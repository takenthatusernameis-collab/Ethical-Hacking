"""FTP reconnaissance module for ethscan.

Offline-first FTP reconnaissance using only the Python standard library
(``ftplib`` / ``socket``). The module performs:

* Banner grab (the server's greeting / welcome message).
* Optional anonymous-login probe (``USER anonymous`` / ``PASS anonymous@``).

All network access is confined to a single helper, ``_connect``, which defaults
to ``ftplib.FTP`` so tests can substitute a local fake FTP client.
"""
from __future__ import annotations

import contextlib
import csv
import ftplib
import io
import json
import socket
from typing import Any

from ethscan.target import TargetSpecError, check_port, parse_url, url_port

DEFAULT_PORT = 21
DEFAULT_TIMEOUT = 3.0


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and port.

    Accepts ``host``, ``host:port``, and ``ftp://host:port`` forms.
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
        # Strip an optional ``host:port`` suffix.
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


def _connect(
    host: str,
    port: int,
    timeout: float,
    connector=ftplib.FTP,
) -> Any:
    """Open an FTP session to the server (injectable for tests).

    ``connector`` is expected to be callable with no arguments and return an
    object exposing ``connect(host, port, timeout=...)``, ``getwelcome()``,
    ``login(...)`` and ``close()`` -- mirroring the ``ftplib.FTP`` interface.
    """
    client = connector()
    client.connect(host, port, timeout=timeout)
    return client


def run_ftp(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    check_anonymous: bool = True,
    connector=ftplib.FTP,
) -> dict[str, Any]:
    """Run FTP reconnaissance against *target*.

    Args:
        target: Hostname, ``host:port``, or URL.
        port: Explicit FTP port; when ``None`` the port is parsed from the
            target (or defaults to 21).
        timeout: Per-read timeout in seconds.
        check_anonymous: Whether to attempt an anonymous login probe.
        connector: Callable returning a connected FTP client (for testing).

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
        "welcome_message": None,
        "anonymous_login": None,
        "anonymous_message": None,
        "check_anonymous": check_anonymous,
        "error": None,
    }

    client: Any | None = None
    try:
        try:
            client = _connect(host, server_port, timeout, connector=connector)
            results["connected"] = True
            try:
                welcome = client.getwelcome()
                results["banner"] = welcome
                results["welcome_message"] = welcome
            except ftplib.Error as exc:
                results["error"] = f"banner read failed: {exc}"
                return results
        # A host that is not a valid host name ("....") raises a UnicodeError,
        # which is a ValueError, when the resolver encodes it.
        except (socket.timeout, OSError, ftplib.Error, ValueError) as exc:
            results["error"] = f"connection failed: {exc}"
            return results

        # Optional anonymous-login probe.
        if check_anonymous:
            try:
                client.login(user="anonymous", passwd="anonymous@")
                results["anonymous_login"] = True
                results["anonymous_message"] = "anonymous login successful"
            except ftplib.Error as exc:
                results["anonymous_login"] = False
                results["anonymous_message"] = str(exc)
    finally:
        if client is not None:
            with contextlib.suppress(ftplib.Error, OSError):
                client.close()

    return results


def format_ftp_report_json(data: dict[str, Any]) -> str:
    """Format FTP reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_ftp_report_markdown(data: dict[str, Any]) -> str:
    """Format FTP reconnaissance results as Markdown."""
    lines = ["# ethscan FTP Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Host:** {data.get('host', '')}")
    lines.append(f"- **Port:** {data.get('port', '')}")
    lines.append(f"- **Connected:** {data.get('connected', False)}")
    if data.get("banner"):
        lines.append(f"- **Banner:** {data['banner']}")
    if data.get("welcome_message"):
        lines.append(f"- **Welcome Message:** {data['welcome_message']}")
    anon = data.get("anonymous_login")
    if anon is True:
        lines.append("- **Anonymous Login:** allowed")
    elif anon is False:
        lines.append("- **Anonymous Login:** disallowed")
    else:
        lines.append("- **Anonymous Login:** not checked")
    if data.get("anonymous_message"):
        lines.append(f"- **Anonymous Message:** {data['anonymous_message']}")
    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {data['error']}")
    lines.append("")
    return "\n".join(lines)


def format_ftp_report_csv(data: dict[str, Any]) -> str:
    """Format FTP reconnaissance results as CSV.

    Emits a single summary row per target with the header
    ``target,host,port,banner,anonymous_login,anonymous_message,error``.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "host", "port", "banner", "anonymous_login", "anonymous_message", "error"])
    anon = data.get("anonymous_login")
    if anon is True:
        anon_str = "true"
    elif anon is False:
        anon_str = "false"
    else:
        anon_str = ""
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", ""),
        data.get("banner") or "",
        anon_str,
        data.get("anonymous_message") or "",
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")
