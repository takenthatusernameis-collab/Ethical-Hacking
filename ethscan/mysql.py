"""MySQL reconnaissance module for ethscan.

Offline-first MySQL reconnaissance using only the Python standard library
(``socket``). The module performs a safe, bounded probe over the MySQL
client/server protocol (TCP 3306):

* **handshake** -- read the server's initial handshake packet and parse
  server version, protocol version, capabilities, charset, and status.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""
import csv
import io
import json
import socket
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PORT = 3306
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("handshake",)


def _normalize_target(target: str) -> Tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts, ``host:port``, and ``mysql://host:port`` URLs.
    Defaults to port ``DEFAULT_PORT`` when none is supplied. IPv6
    literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: Optional[str] = None
    port: Optional[int] = None

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = (parsed.hostname or "").strip()
        port = parsed.port
    else:
        host = normalized
        if host and host.startswith("["):
            close = host.find("]")
            if close > 0:
                maybe_port = host[close + 1:]
                if maybe_port.startswith(":") and maybe_port[1:].isdigit():
                    port = port or int(maybe_port[1:])
                host = host[1:close]
        elif host and ":" in host and "]" not in host:
            base, _, rest = host.rpartition(":")
            if rest.isdigit():
                host = base
                port = port or int(rest)

    if not host:
        raise ValueError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """Send bytes over TCP and return received bytes.

    Tests may provide a ``connector`` callable to inject a fake transport.
    """
    if connector is not None:
        try:
            return connector(host, port, request, timeout)
        except Exception as exc:  # pragma: no cover
            return None, f"connector error: {exc}"

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            if request:
                sock.sendall(request)
            return sock.recv(4096), None
    except socket.timeout:
        return None, "Timeout"
    except ConnectionRefusedError:
        return None, "Connection refused"
    except OSError as exc:
        return None, str(exc)


def _parse_handshake(data: bytes) -> Dict[str, Any]:
    """Parse MySQL initial handshake packet (Protocol::HandshakeV10).

    Returns a dict with version/protocol/capabilities/charset/status if
    parsable, otherwise empty dict. This is a best-effort parser that
    handles common fields.
    """
    if not data or len(data) < 5:
        return {}

    # Packet header: 3 bytes length + 1 byte sequence number
    # We don't need to validate header strictly for parsing the payload
    payload = data[4:] if len(data) > 4 else b""

    if not payload:
        return {}

    pos = 0
    if pos >= len(payload):
        return {}

    protocol_version = payload[pos]
    pos += 1

    # Null-terminated server version string
    server_version_bytes: List[bytearray] = []
    while pos < len(payload):
        b = payload[pos]
        pos += 1
        if b == 0:
            break
        server_version_bytes.append(b)
    server_version = bytes(server_version_bytes).decode("utf-8", errors="replace") if server_version_bytes else ""

    if pos + 4 > len(payload):
        # Not enough for thread id; still try to extract what we have
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
        }

    # Thread ID (4 bytes, little-endian in practice; we just note presence)
    thread_id = int.from_bytes(payload[pos:pos + 4], byteorder="little", signed=False)
    pos += 4

    # Auth plugin data part 1 (8 bytes + 1 null)
    if pos >= len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
        }

    salt1_start = pos
    # Find next null
    null1 = payload.find(b"\x00", salt1_start)
    salt1_len = (null1 - salt1_start) if null1 != -1 else 8
    if salt1_len < 0:
        salt1_len = 8
    if salt1_len > 12:  # reasonable bound
        salt1_len = 8
    salt1 = payload[salt1_start:salt1_start + salt1_len].decode("utf-8", errors="replace") if salt1_len > 0 else ""
    if null1 != -1:
        pos = null1 + 1
    else:
        pos = salt1_start + salt1_len

    if pos + 2 > len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
        }

    # Capabilities (lower 2 bytes)
    capabilities_lower = int.from_bytes(payload[pos:pos + 2], byteorder="little", signed=False)
    pos += 2

    if pos >= len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
            "capabilities": capabilities_lower,
        }

    charset = payload[pos]
    pos += 1

    if pos + 2 > len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
            "capabilities": capabilities_lower,
            "charset": charset,
        }

    status = int.from_bytes(payload[pos:pos + 2], byteorder="little", signed=False)
    pos += 2

    if pos + 2 > len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
            "capabilities": capabilities_lower,
            "charset": charset,
            "status": status,
        }

    capabilities_upper = int.from_bytes(payload[pos:pos + 2], byteorder="little", signed=False)
    pos += 2
    capabilities = (capabilities_upper << 16) | capabilities_lower

    # Auth plugin data length
    if pos >= len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
            "capabilities": capabilities,
            "charset": charset,
            "status": status,
        }

    auth_plug_len = payload[pos]
    pos += 1

    # Skip reserved 10 bytes
    pos += 10
    if pos >= len(payload):
        return {
            "protocol_version": protocol_version,
            "server_version": server_version,
            "thread_id": thread_id,
            "salt1": salt1,
            "capabilities": capabilities,
            "charset": charset,
            "status": status,
            "auth_plugin_data_length": auth_plug_len,
        }

    # Auth plugin data part 2 (max 13 bytes)
    salt2_max = max(0, auth_plug_len - 8) if auth_plug_len > 8 else 12
    salt2_max = min(salt2_max, 13)
    salt2 = payload[pos:pos + salt2_max].split(b"\x00", 1)[0].decode("utf-8", errors="replace") if salt2_max > 0 else ""
    salt_full = (salt1 + salt2) if salt1 or salt2 else ""

    # Auth plugin name (null-terminated) - optional
    auth_plugin_name = ""
    # Try to read remaining as plugin name
    # If salt2 was terminated by null inside the slice, the plugin name starts at pos + (index of null + 1)
    # But we need to be precise relative to pos
    salt2_full_slice = payload[pos:pos + salt2_max] if salt2_max > 0 else b""
    null_in_slice = salt2_full_slice.find(b"\x00")
    if null_in_slice != -1:
        plugin_start = pos + null_in_slice + 1
    else:
        plugin_start = pos + salt2_max
    remaining = payload[plugin_start:] if plugin_start < len(payload) else b""
    if remaining:
        start_ap = 0
        if remaining.startswith(b"\x00"):
            start_ap = 1
        end_ap = remaining.find(b"\x00", start_ap)
        auth_plugin_name = (
            remaining[start_ap:end_ap].decode("utf-8", errors="replace")
            if end_ap != -1
            else remaining[start_ap:].decode("utf-8", errors="replace")
        )

    return {
        "protocol_version": protocol_version,
        "server_version": server_version,
        "thread_id": thread_id,
        "salt1": salt1,
        "salt2": salt2,
        "salt": salt_full,
        "capabilities": capabilities,
        "charset": charset,
        "status": status,
        "auth_plugin_data_length": auth_plug_len,
        "auth_plugin_name": auth_plugin_name,
    }


def _assess_handshake(handshake: Dict[str, Any]) -> List[str]:
    """Assess handshake data and return findings."""
    findings: List[str] = []
    version = handshake.get("server_version", "")
    if version:
        findings.append(f"MySQL/MariaDB server version: {version}")
        # Check for very old versions as a simple heuristic
        v_lower = version.lower()
        if any(x in v_lower for x in ("5.0.", "5.1.", "4.")):
            findings.append("Old MySQL version detected (potentially unsupported)")
        if "mariadb" in v_lower:
            findings.append("MariaDB server detected")

    capabilities = handshake.get("capabilities")
    if capabilities is not None:
        try:
            # Common capability flags (simplified)
            if capabilities & (1 << 11):  # CLIENT_SECURE_CONNECTION
                findings.append("Secure connection capability advertised")
            if capabilities & (1 << 9):  # CLIENT_SSL
                findings.append("SSL/TLS capability advertised")
        except Exception:
            pass

    return findings


def run_mysql(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: Optional[List[str]] = None,
    connector=None,
) -> Dict[str, Any]:
    """Run MySQL reconnaissance probes against a target.

    Args:
        target: Hostname, ``host:port``, or ``mysql://host:port``.
        port: Optional override for the TCP port.
        timeout: Connection timeout in seconds.
        probes: List of probe names (case-insensitive). Defaults to
            ``("handshake",)``.
        connector: Optional transport injector for testing.

    Returns:
        A structured dict with target/host/port, accessibility,
        handshake data, findings, and any error.
    """
    try:
        host, parsed_port = _normalize_target(target)
    except ValueError as exc:
        return {
            "target": target,
            "host": None,
            "port": port or DEFAULT_PORT,
            "accessible": False,
            "handshake": {},
            "version": None,
            "findings": [],
            "error": str(exc),
        }

    final_port = int(port) if port is not None else parsed_port
    probe_list = probes if probes is not None else list(DEFAULT_PROBES)
    if not probe_list:
        return {
            "target": target,
            "host": host,
            "port": final_port,
            "accessible": False,
            "handshake": {},
            "version": None,
            "findings": [],
            "error": None,
        }

    # Normalize probe names
    norm_probes = [p.strip().lower() for p in probe_list if p.strip()]

    handshake_data: Dict[str, Any] = {}
    accessible = False
    error: Optional[str] = None
    version: Optional[str] = None

    # For MySQL, the server sends handshake on connect; we don't need to send anything
    # So for handshake probe, just receive
    try:
        resp, err = _send_recv(host, final_port, b"", timeout, connector)
        if err:
            error = err
        else:
            if resp:
                accessible = True
                handshake_data = _parse_handshake(resp)
                if handshake_data.get("server_version"):
                    version = str(handshake_data["server_version"])
            else:
                accessible = False
                error = error or "No response from server"
    except Exception as exc:  # pragma: no cover
        accessible = False
        error = str(exc)

    findings = _assess_handshake(handshake_data)

    return {
        "target": target,
        "host": host,
        "port": final_port,
        "accessible": bool(accessible),
        "handshake": handshake_data,
        "version": version,
        "findings": findings,
        "error": error,
    }


def format_mysql_report_json(data: Dict[str, Any]) -> str:
    """Format MySQL reconnaissance results as JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_mysql_report_markdown(data: Dict[str, Any]) -> str:
    """Format MySQL reconnaissance results as Markdown."""
    lines: List[str] = []
    lines.append("# MySQL Reconnaissance Report")
    lines.append("")
    lines.append(f"**Target:** {data.get('target', '')}")
    lines.append(f"**Host:** {data.get('host') or 'N/A'}")
    lines.append(f"**Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"**Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    lines.append("")

    if data.get("version"):
        lines.append(f"**Server Version:** {data['version']}")
        lines.append("")

    handshake = data.get("handshake") or {}
    if handshake:
        lines.append("## Handshake")
        lines.append("")
        for key in ["protocol_version", "thread_id", "capabilities", "charset", "status", "auth_plugin_name"]:
            if key in handshake and handshake[key] is not None:
                lines.append(f"- **{key}:** {handshake[key]}")
        if handshake.get("salt"):
            # Don't expose full salt in verbose form? Just indicate presence
            lines.append("- **auth_salt_present:** true")
        lines.append("")

    findings = data.get("findings") or []
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("- No notable findings")
        lines.append("")

    if data.get("error"):
        lines.append("## Error")
        lines.append("")
        lines.append(f"**Error:** {data['error']}")
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def format_mysql_report_csv(data: Dict[str, Any]) -> str:
    """Format MySQL reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "version",
        "protocol_version",
        "thread_id",
        "capabilities",
        "charset",
        "status",
        "auth_plugin_name",
        "findings",
        "error",
    ])

    handshake = data.get("handshake") or {}
    findings = data.get("findings") or []
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("version") or "",
        handshake.get("protocol_version") or "",
        handshake.get("thread_id") or "",
        handshake.get("capabilities") or "",
        handshake.get("charset") or "",
        handshake.get("status") or "",
        handshake.get("auth_plugin_name") or "",
        "; ".join(findings).replace("\n", " ").replace("\r", " "),
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_PROBES",
    "DEFAULT_TIMEOUT",
    "_assess_handshake",
    "_normalize_target",
    "_parse_handshake",
    "_send_recv",
    "format_mysql_report_csv",
    "format_mysql_report_json",
    "format_mysql_report_markdown",
    "run_mysql",
]
