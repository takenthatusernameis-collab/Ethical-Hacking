"""SMTP reconnaissance module for ethscan.

Offline-first SMTP reconnaissance using only the Python standard library
(``smtplib`` / ``socket``). The module performs:

* Banner grab (the server's greeting line).
* Capability discovery via ``EHLO`` (reports whether ``STARTTLS`` is advertised).
* Optional ``VRFY`` user enumeration when a username list is supplied.
* Optional open-relay probing (``MAIL FROM`` / ``RCPT TO`` to an external domain).

All network access is confined to a single helper, ``_connect``, which defaults
to ``socket.create_connection`` so tests can substitute a local fake SMTP server.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
import time
from typing import Any

from ethscan.target import TargetSpecError, check_port, parse_url, url_port

DEFAULT_PORT = 25
DEFAULT_TIMEOUT = 2.0
DEFAULT_EHLO_NAME = "ethscan"
RELAY_PROBE_DOMAIN = "ethscan.invalid"

# VRFY response classification. A 3-digit SMTP code is mapped to a human label
# and a boolean ``found`` flag (True when the server confirms knowledge of the
# user). ``None`` means the response was inconclusive.
_VRFY_LABELS: dict[str, tuple[bool | None, str]] = {
    "250": (None, "user known"),
    "251": (True, "user not local but will forward"),
    "252": (None, "user enumeration not allowed / will accept"),
    "550": (False, "no such user"),
    "551": (False, "not local"),
}


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, ``smtp://host:port`` and ``host:25`` forms.
    Defaults to port ``DEFAULT_PORT`` when none is supplied.
    """
    normalized = target.strip()
    if "://" in normalized:
        parsed = parse_url(normalized)
        host = parsed.hostname or ""
        port = url_port(parsed)
    else:
        host = normalized
        port = None
        # Strip an optional ``host:port`` suffix (bare host:port or bracketed form).
        if host and host.startswith("[") and "]:" in host:
            bracket_end = host.find("]:")
            if bracket_end > 0:
                port_part = host[bracket_end + 2:]
                if port_part.isdigit():
                    host = host[1:bracket_end]
                    port = port or check_port(port_part)
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or check_port(rest)
        elif host and host.startswith("[") and host.endswith("]"):
            host = host[1:-1]

    if not host:
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _reply_code(line: str) -> int:
    """Return the three-digit reply code of an SMTP status line.

    A reply code is three ASCII digits (RFC 5321). ``str.isdigit`` also
    accepts the Unicode superscript digits, which ``int`` refuses, so the
    code is only read when the text is ASCII. A status line that is not a
    valid reply code is reported as ``0``, like any other non-numeric line.
    """
    prefix = line[:3]
    if not prefix.isascii() or not prefix.isdigit():
        return 0
    return int(prefix)


def _parse_smtp_response(lines: list[str]) -> tuple[int, str, bool]:
    """Parse the first line of an SMTP response list.

    Returns ``(code, message, complete)`` where ``complete`` is False when the
    response is a multi-line continuation (a line whose separator was ``-``).
    """
    if not lines:
        return 0, "", False
    first = lines[0]
    code = _reply_code(first)
    sep = first[3:4] if len(first) > 3 else ""
    message = first[4:] if len(first) > 4 else ""
    complete = sep == " "
    return code, message, complete


def _read_response(sock: socket.socket, timeout: float, max_lines: int = 100) -> list[str]:
    """Read a complete SMTP response (all continuation lines) from *sock*.

    A response is complete once a line whose fourth character is a space
    (separator `` ` `) is received. Lines using ``-`` as the separator are
    continuations.
    """
    sock.settimeout(timeout)
    lines: list[str] = []
    buf = b""
    start = time.monotonic()
    while True:
        if lines and lines[-1][3:4] == " ":
            break
        if len(lines) >= max_lines:
            break
        try:
            chunk = sock.recv(4096)
        except (socket.timeout, OSError):
            if not lines:
                raise
            break
        except Exception:
            if not lines:
                raise
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.rstrip(b"\r").decode("utf-8", errors="replace")
            if text:
                lines.append(text)
                if text[3:4] == " ":
                    break
        # Bound total wait time to avoid hanging on a stalled socket.
        if time.monotonic() - start > timeout * max_lines:
            break
    return lines


def _send_command(sock: socket.socket, command: str, timeout: float) -> list[str]:
    """Send *command* over *sock* and return the parsed response lines."""
    sock.settimeout(timeout)
    data = (command + "\r\n").encode("utf-8")
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise OSError("connection closed while sending command")
        total_sent += sent
    return _read_response(sock, timeout)


def _connect(
    host: str,
    port: int,
    timeout: float,
    connector=socket.create_connection,
) -> socket.socket:
    """Open a TCP connection to the SMTP server (injectable for tests)."""
    return connector((host, port), timeout)


def _classify_vrfy(code: int) -> tuple[bool | None, str]:
    """Map an SMTP ``VRFY`` response code to ``(found, description)``."""
    key = str(code)
    if key in _VRFY_LABELS:
        return _VRFY_LABELS[key]
    if 200 <= code < 300:
        return (None, "accepted")
    if 500 <= code < 600:
        return (None, "rejected")
    return (None, f"code {code}")


def run_smtp(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    users: list[str] | None = None,
    check_starttls: bool = True,
    check_relay: bool = True,
    ehlo_name: str = DEFAULT_EHLO_NAME,
    connector=socket.create_connection,
) -> dict[str, Any]:
    """Run SMTP reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit SMTP port; when ``None`` the port is parsed from the
            target (or defaults to 25).
        timeout: Per-read timeout in seconds.
        users: Optional list of usernames to probe with ``VRFY``.
        check_starttls: Whether to advertise/require ``EHLO`` and look for STARTTLS.
        check_relay: Whether to probe for open relays.
        ehlo_name: Hostname string sent in the ``EHLO`` command.
        connector: Callable returning a connected socket (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port
    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "connected": False,
        "banner": None,
        "ehlo_success": False,
        "starttls_advertised": False,
        "starttls_checked": check_starttls,
        "capabilities": [],
        "users": [],
        "open_relay": None,
        "error": None,
    }

    sock: socket.socket | None = None
    try:
        sock = _connect(host, server_port, timeout, connector=connector)
        results["connected"] = True
        try:
            banner_lines = _read_response(sock, timeout)
            results["banner"] = banner_lines[0] if banner_lines else None
        except (socket.timeout, OSError) as exc:
            results["error"] = f"banner read failed: {exc}"
            return results
        except Exception as exc:  # noqa: BLE001 - transport can raise any type
            results["error"] = f"banner read failed: {exc}"
            return results
    # A host that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it.
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        results["error"] = f"connection failed: {exc}"
        if sock is not None:
            sock.close()
        return results

    try:
        # EHLO to discover capabilities (and to check STARTTLS support).
        if check_starttls:
            try:
                resp = _send_command(sock, f"EHLO {ehlo_name}", timeout)
                results["ehlo_success"] = True
                caps: list[str] = []
                # In an EHLO multi-line response the first line carries the
                # server greeting (a domain) and the final line is a bare
                # acknowledgement ("250 OK"); neither is an extension keyword.
                for idx, line in enumerate(resp):
                    if len(line) <= 4:
                        continue
                    # A line that holds no word after the separator ("250-   ")
                    # carries no keyword, so it is skipped instead of being
                    # read at a fixed index into an empty list.
                    words = line[4:].split()
                    if not words:
                        continue
                    kw = words[0]
                    if kw.upper() == "OK" or idx == 0:
                        continue
                    if kw:
                        caps.append(kw.upper())
                results["capabilities"] = caps
                results["starttls_advertised"] = "STARTTLS" in caps
            except (socket.timeout, OSError) as exc:
                results["error"] = f"ehlo failed: {exc}"
                results["ehlo_success"] = False
            except Exception as exc:  # noqa: BLE001 - transport can raise any type
                results["error"] = f"ehlo failed: {exc}"
                results["ehlo_success"] = False

        # Optional VRFY user enumeration.
        if users:
            for user in users:
                if not user:
                    continue
                entry: dict[str, Any] = {
                    "user": user,
                    "found": None,
                    "description": None,
                    "code": None,
                    "error": None,
                }
                try:
                    resp = _send_command(sock, f"VRFY {user}", timeout)
                    code, _msg, _complete = _parse_smtp_response(resp)
                    entry["code"] = code
                    found, desc = _classify_vrfy(code)
                    entry["found"] = found
                    entry["description"] = desc
                except (socket.timeout, OSError) as exc:
                    entry["error"] = str(exc)
                except Exception as exc:  # noqa: BLE001 - transport can raise any type
                    entry["error"] = str(exc)
                results["users"].append(entry)

        # Optional open-relay probe.
        if check_relay and results["ehlo_success"]:
            open_relay = False
            try:
                mail = _send_command(sock, f"MAIL FROM:<probe@{RELAY_PROBE_DOMAIN}>", timeout)
                mail_code, _, _ = _parse_smtp_response(mail)
                if 250 <= mail_code < 300:
                    rcpt = _send_command(sock, f"RCPT TO:<relay@{RELAY_PROBE_DOMAIN}>", timeout)
                    rcpt_code, _, _ = _parse_smtp_response(rcpt)
                    if 250 <= rcpt_code < 300:
                        open_relay = True
                results["open_relay"] = open_relay
            except (socket.timeout, OSError) as exc:
                results["open_relay"] = None
                if not results["error"]:
                    results["error"] = f"relay check failed: {exc}"
            except Exception as exc:  # noqa: BLE001 - transport can raise any type
                results["open_relay"] = None
                if not results["error"]:
                    results["error"] = f"relay check failed: {exc}"

        # Politely close.
        with contextlib.suppress(socket.timeout, OSError):
            _send_command(sock, "QUIT", timeout)
    # A hostile server must never crash the command: whatever it sends is
    # reported through the "error" field, like the other protocol modules.
    except Exception as exc:  # noqa: BLE001 - a remote answer must not raise
        results["error"] = f"smtp probe failed: {exc}"
    finally:
        if sock is not None:
            sock.close()

    return results


def format_smtp_report_json(data: dict[str, Any]) -> str:
    """Format SMTP reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_smtp_report_markdown(data: dict[str, Any]) -> str:
    """Format SMTP reconnaissance results as Markdown."""
    lines = ["# ethscan SMTP Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    lines.append(f"- **Connected:** {data.get('connected', False)}")
    if data.get("banner"):
        lines.append(f"- **Banner:** {data['banner']}")
    lines.append(f"- **EHLO Success:** {data.get('ehlo_success', False)}")
    lines.append(f"- **STARTTLS Advertised:** {data.get('starttls_advertised', False)}")
    caps = data.get("capabilities") or []
    if caps:
        lines.append(f"- **Capabilities:** {', '.join(caps)}")
    if data.get("users"):
        lines.append("")
        lines.append("## VRFY User Enumeration")
        lines.append("| User | Found | Code | Description |")
        lines.append("|------|-------|------|-------------|")
        for u in data["users"]:
            found = u.get("found")
            found_str = "Yes" if found is True else ("No" if found is False else "Unknown")
            lines.append(
                f"| {u.get('user', '')} | {found_str} | {u.get('code') or ''} | "
                f"{u.get('description', '')} |"
            )
    if data.get("open_relay") is not None:
        relay_str = "VULNERABLE" if data["open_relay"] else "not vulnerable"
        lines.append("")
        lines.append(f"- **Open Relay:** {relay_str}")
    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {data['error']}")
    lines.append("")
    return "\n".join(lines)


def format_smtp_report_csv(data: dict[str, Any]) -> str:
    """Format SMTP reconnaissance results as CSV.

    Emits one row per VRFY-checked user (``target,host,port,user,found,code,description``)
    when a user list was supplied; otherwise a single summary row.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "host", "port", "user", "found", "code", "description"])
    users = data.get("users") or []
    if not users:
        relay = data.get("open_relay")
        if relay is True:
            found_str, desc = "true", "open relay"
        elif relay is False:
            found_str, desc = "false", "closed relay"
        else:
            found_str, desc = "", ""
        writer.writerow([
            data.get("target", ""),
            data.get("host", ""),
            data.get("port", ""),
            "",
            found_str,
            "",
            desc,
        ])
    else:
        for u in users:
            found = u.get("found")
            found_str = "true" if found is True else ("false" if found is False else "")
            writer.writerow([
                data.get("target", ""),
                data.get("host", ""),
                data.get("port", ""),
                u.get("user", ""),
                found_str,
                u.get("code") or "",
                u.get("description", "") or "",
            ])
    return output.getvalue().rstrip("\r\n")
