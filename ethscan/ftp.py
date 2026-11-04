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
import re
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
    try:
        client.connect(host, port, timeout=timeout)
    except BaseException:
        with contextlib.suppress(Exception):
            client.close()
        raise
    return client


def _assess_ftp_version(banner: str | None) -> list[str]:
    """Assess the FTP banner and return version-related findings.

    FTP greetings commonly embed the server version (for example
    ``220 (vsFTPd 3.0.3)`` or ``220 ProFTPD 1.3.5 Server``). Only version
    tokens attached to a known FTP server name are assessed, so IPv4
    addresses and other dotted numbers in the banner are never mistaken for
    a version. Versions with a major component below 3 are treated as out of
    support.
    """
    findings: list[str] = []
    if not banner:
        return findings
    match = re.search(
        r"\b(?:vsFTPd|ProFTPD|FileZilla|Pure-FTPd|Microsoft FTP)\b[^\d]{0,30}(\d+(?:\.\d+){1,2})",
        banner,
        re.IGNORECASE,
    )
    if not match:
        return findings
    version = match.group(1)
    major = int(version.split(".")[0])
    findings.append(f"FTP server version: {version}")
    if major < 3:
        findings.append(
            f"Old FTP server version detected (version {version}; "
            "out of support, may lack security updates)"
        )
    return findings


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

        ``anonymous_login`` is ``True`` when the login succeeded, ``False``
        when the server refused it, and ``None`` when the login could not be
        completed (the server dropped the connection or answered with a
        malformed reply); the reason is reported in ``error``.
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
        "findings": [],
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
                results["findings"].extend(_assess_ftp_version(welcome))
            except EOFError:
                results["error"] = "banner read failed: server closed the connection"
                return results
            except (ftplib.Error, OSError, ValueError, RuntimeError) as exc:
                results["error"] = f"banner read failed: {exc}"
                return results
        # A host that is not a valid host name ("....") raises a UnicodeError,
        # which is a ValueError, when the resolver encodes it. A server that
        # closes the connection before sending its greeting makes ftplib
        # raise EOFError, and a server that answers with bytes that are not
        # text raises a UnicodeDecodeError, which is a ValueError. A transport
        # failure of an unnamed type must not escape the command.
        except EOFError:
            results["error"] = "connection failed: server closed the connection"
            return results
        except (socket.timeout, OSError, ftplib.Error, ValueError, RuntimeError) as exc:
            results["error"] = f"connection failed: {exc}"
            return results
        except Exception as exc:  # noqa: BLE001 - transport can raise any type
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
            # A server that drops the connection, resets it, or answers with
            # bytes that are not text must not crash the command: the outcome
            # of the login stays unknown and the failure is reported.
            except EOFError:
                results["anonymous_login"] = None
                results["anonymous_message"] = "login failed: server closed the connection"
                results["error"] = "login failed: server closed the connection"
            except (OSError, ValueError) as exc:
                results["anonymous_login"] = None
                results["anonymous_message"] = f"login failed: {exc}"
                results["error"] = f"login failed: {exc}"
            except Exception as exc:  # noqa: BLE001 - transport can raise any type
                results["anonymous_login"] = None
                results["anonymous_message"] = f"login failed: {exc}"
                results["error"] = f"login failed: {exc}"
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
    findings = data.get("findings") or []
    if findings:
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.append(f"- {f}")
        lines.append("")
    if data.get("error"):
        lines.append("")
        lines.append(f"- **Error:** {data['error']}")
    lines.append("")
    return "\n".join(lines)


def format_ftp_report_csv(data: dict[str, Any]) -> str:
    """Format FTP reconnaissance results as CSV.

    Emits a single summary row per target with the header
    ``target,host,port,banner,anonymous_login,anonymous_message,error``.
    A top-level probe error is surfaced as a dedicated error row (mirroring
    the Markdown ``- **Error:**`` rendering and the ssh/smtp CSV pattern)
    instead of being buried as the last field of a summary row.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "host", "port", "banner", "anonymous_login", "anonymous_message", "error"])

    error = data.get("error")
    if error:
        writer.writerow([
            data.get("target", ""),
            data.get("host", ""),
            data.get("port", ""),
            "",  # banner
            "",  # anonymous_login
            "",  # anonymous_message
            str(error),
        ])
        findings = data.get("findings")
        if isinstance(findings, list) and findings:
            writer.writerow([])
            writer.writerow(["finding"])
            for finding in findings:
                writer.writerow([finding])
        return output.getvalue().rstrip("\r\n")

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

    findings = data.get("findings")
    if isinstance(findings, list) and findings:
        writer.writerow([])
        writer.writerow(["finding"])
        for finding in findings:
            writer.writerow([finding])

    return output.getvalue().rstrip("\r\n")
