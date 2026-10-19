"""Oracle reconnaissance module for ethscan.

Offline-first Oracle reconnaissance using only the Python standard library
(``socket`` and ``struct``). The module performs a safe, bounded probe over the
TNS (Transparent Network Substrate) protocol (TCP ``1521``):

* **version** -- send a TNS Connect request and parse the server's Accept
  response to extract the protocol version. No login is attempted.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
import struct
from typing import Any

from ethscan.target import TargetSpecError, url_port

DEFAULT_PORT = 1521
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("version",)


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts, ``host:port``, and ``oracle://`` / ``tns://`` URLs.
    Defaults to port ``DEFAULT_PORT`` when none is supplied. IPv6
    literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: str | None = None
    port: int | None = None

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        # urlparse already unwraps bracketed IPv6 and splits the port.
        host = (parsed.hostname or "").strip()
        port = url_port(parsed)
    else:
        host = normalized
        # Only interpret host[:port] / bracketed IPv6 when no scheme was given.
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
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _build_connect_request(
    desired_version: int = 0x03FF,
    min_version: int = 0x0000,
    connect_data: str = "",
) -> bytes:
    """Build a TNS Connect packet.

    We follow the structure from the Ruby example in the Oracle TNS Enumeration
    article, which is known to work with many listeners.

    The packet structure is:

      0-1: Packet Length (big endian, includes these two bytes)
      2-3: Packet Checksum (0)
      4:   Packet Type (0x01 for Connect)
      5:   Reserved (0)
      6-7: Header Checksum (0)
      8-9:  Version (desired)
      10-11: Version (minimum compatible)
      12-13: Service Options
      14-15: SDU (Session Data Unit Size)
      16-17: TDU (Transport Data Unit Size)
      18-19: NT Protocol Characteristics
      20-21: Line Turnaround Value
      22-23: Value of 1 in Hardware (0x0001)
      24-25: Length of Connect Data (in bytes)
      26-27: Offset to Connect Data (from start of packet)
      28-31: Maximum Receivable Connect Data
      32:    Connect Flags 0
      33:    Connect Flags 1
      34-37: Trace Cross Facility Item 1
      38-41: Trace Cross Facility Item 2
      42-49: Unique Connection ID (8 bytes)
      50-57: Reserved (8 bytes) - set to zero
      58-...: Connect Data (string)

    We set the Unique Connection ID to zero for simplicity.
    """
    # Build the connect data bytes
    connect_data_bytes = connect_data.encode("utf-8")
    connect_data_len = len(connect_data_bytes)

    # The offset to connect data is fixed at 58 (as in the Ruby example)
    offset_to_connect_data = 58

    # Calculate the total packet length:
    #   Header up to connect data: 58 bytes
    #   Connect data: connect_data_len bytes
    total_length = offset_to_connect_data + connect_data_len

    # Build the packet
    pkt = bytearray()

    # Packet Length (big endian)
    pkt.extend(struct.pack("!H", total_length))
    # Packet Checksum (0)
    pkt.extend(struct.pack("!H", 0x0000))
    # Packet Type (0x01 for Connect)
    pkt.append(0x01)
    # Reserved
    pkt.append(0x00)
    # Header Checksum (0)
    pkt.extend(struct.pack("!H", 0x0000))

    # Connect packet fields
    pkt.extend(struct.pack("!H", desired_version))        # Version (desired)
    pkt.extend(struct.pack("!H", min_version))            # Version (minimum compatible)
    pkt.extend(struct.pack("!H", 0x0000))                 # Service Options
    pkt.extend(struct.pack("!H", 0x0800))                 # SDU (2048)
    pkt.extend(struct.pack("!H", 0xFFFF))                 # TDU (65535)
    pkt.extend(struct.pack("!H", 0x7F08))                 # NT Protocol Characteristics
    pkt.extend(struct.pack("!H", 0x0000))                 # Line Turnaround Value
    pkt.extend(struct.pack("!H", 0x0001))                 # Value of 1 in Hardware
    pkt.extend(struct.pack("!H", connect_data_len))       # Length of Connect Data
    pkt.extend(struct.pack("!H", offset_to_connect_data)) # Offset to Connect Data
    pkt.extend(struct.pack("!I", 0x00000000))             # Maximum Receivable Connect Data
    pkt.append(0x00)                                      # Connect Flags 0
    pkt.append(0x00)                                      # Connect Flags 1
    pkt.extend(struct.pack("!I", 0x00000000))             # Trace Cross Facility Item 1
    pkt.extend(struct.pack("!I", 0x00000000))             # Trace Cross Facility Item 2
    pkt.extend(struct.pack("!Q", 0x0000000000000000))     # Unique Connection ID (8 bytes)
    # Reserved 8 bytes (to reach offset 58)
    pkt.extend(b"\x00" * 8)

    # Connect Data
    pkt.extend(connect_data_bytes)

    return bytes(pkt)


def _send_recv(
    host: str,
    port: int,
    request: bytes,
    timeout: float,
    connector=None,
) -> tuple[bytes | None, str | None]:
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
            chunks: list[bytes] = []
            try:
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except socket.timeout:
                pass
            return b"".join(chunks) if chunks else None, None
    except socket.timeout:
        return None, "Timeout"
    except ConnectionRefusedError:
        return None, "Connection refused"
    except OSError as exc:
        return None, str(exc)


def _parse_accept_response(data: bytes) -> dict[str, Any]:
    """Parse the server's Accept response.

    The Accept packet has the same TNS header as the Connect packet.
    After the 8-byte TNS header, the Accept payload starts.

    According to the oracle-rs source, the Accept payload begins with:
        - protocol version (2 bytes) that the server has agreed to.

    We'll extract that version and return it.
    """
    result: dict[str, Any] = {
        "version": None,
        "error": None,
    }
    if not data or len(data) < 8:
        result["error"] = f"Response too short: {len(data)} bytes"
        return result

    # Parse TNS header
    try:
        _pkt_len, _chk_sum, pkt_type, _reserved, _hdr_chk_sum = struct.unpack(
            "!HHBBH", data[:8]
        )
    except struct.error:
        result["error"] = "Failed to parse TNS header"
        return result

    if pkt_type != 0x02:  # Accept packet type
        result["error"] = f"Expected Accept response (type 0x02), got type 0x{pkt_type:02x}"
        return result

    # The payload starts at byte 8
    payload = data[8:]

    # We expect at least 2 bytes for the version
    if len(payload) < 2:
        result["error"] = "Accept payload too short to contain version"
        return result

    # The first two bytes of the payload are the protocol version (agreed)
    version_bytes = payload[:2]
    try:
        version = struct.unpack("!H", version_bytes)[0]
        result["version"] = f"{version}"  # We'll return as string for now
    except struct.error:
        result["error"] = "Failed to parse version from Accept payload"
        return result

    return result


def _parse_refuse_response(data: bytes) -> dict[str, Any]:
    """Parse the server's Refuse response.

    The Refuse packet has the same TNS header.
    After the 8-byte TNS header, the Refuse payload starts.

    According to the oracle-rs source and the pythian blog, the Refuse payload is:
        - Reason (2 bytes) - unused
        - Data length (2 bytes)
        - Data (n bytes) - error message

    We'll extract the error message and try to get an error code if present.
    """
    result: dict[str, Any] = {
        "error": None,
        "error_code": None,
    }
    if not data or len(data) < 8:
        result["error"] = f"Response too short: {len(data)} bytes"
        return result

    # Parse TNS header
    try:
        _pkt_len, _chk_sum, pkt_type, _reserved, _hdr_chk_sum = struct.unpack(
            "!HHBBH", data[:8]
        )
    except struct.error:
        result["error"] = "Failed to parse TNS header"
        return result

    if pkt_type != 0x04:  # Refuse packet type
        result["error"] = f"Expected Refuse response (type 0x04), got type 0x{pkt_type:02x}"
        return result

    # The payload starts at byte 8
    payload = data[8:]

    # We need at least 4 bytes for reason and data length
    if len(payload) < 4:
        result["error"] = "Refuse payload too short"
        return result

    # Skip reason (2 bytes)
    # Data length (2 bytes)
    try:
        data_length = struct.unpack("!H", payload[2:4])[0]
    except struct.error:
        result["error"] = "Failed to parse data length in Refuse payload"
        return result

    if len(payload) < 4 + data_length:
        result["error"] = "Refuse payload length does not match indicated data length"
        return result

    # Extract data
    error_data = payload[4:4 + data_length]
    try:
        error_str = error_data.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        error_str = error_data.hex()

    result["error"] = error_str

    # Try to extract error code from the error string (e.g., (ERR=12514))
    import re
    match = re.search(r'\(ERR=(\d+)\)', error_str)
    if match:
        with contextlib.suppress(ValueError):
            result["error_code"] = int(match.group(1))

    return result


def _assess_version(accept_resp: dict[str, Any]) -> list[str]:
    """Assess Accept response and return findings."""
    findings: list[str] = []
    version = accept_resp.get("version")
    if version:
        findings.append(f"Oracle TNS server version: {version}")
        # Optionally, we could parse the version to determine if it's old?
        # We'll skip for now.
    if accept_resp.get("error"):
        findings.append(f"Error: {accept_resp['error']}")
    return findings


def run_oracle(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run Oracle reconnaissance probes against *target*.

    Args:
        target: Hostname, ``host:port``, or ``oracle://`` / ``tns://`` URL.
        port: Explicit Oracle port; when ``None`` the port is parsed from
            the target (or defaults to 1521).
        timeout: Per-request timeout in seconds.
        probes: List of probes to run (case-insensitive). Defaults to
            ``("version",)``.
        connector: Callable for sending/receiving TCP data (for testing).

    Returns:
        Structured result dict consumed by the formatters below.
    """
    try:
        host, parsed_port = _normalize_target(target)
    except ValueError as exc:
        return {
            "target": target,
            "host": None,
            "port": port or DEFAULT_PORT,
            "accessible": False,
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
            "version": None,
            "findings": [],
            "error": None,
        }

    norm_probes = [p.strip().lower() for p in probe_list if p.strip()]

    version_data: dict[str, Any] = {}
    version: str | None = None
    accessible = False
    error: str | None = None

    if "version" in norm_probes:
        # Build a minimal connect data string.
        # We'll use a dummy service name. The listener might refuse if the service name is invalid,
        # but we hope to still get an Accept packet with the version before checking the service name?
        # Alternatively, we can try to send an empty service name.
        connect_data = f"(DESCRIPTION=(CONNECT_DATA=(SERVICE_NAME=)))(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={final_port}))"
        try:
            request = _build_connect_request(
                desired_version=0x03FF,
                min_version=0x0000,
                connect_data=connect_data,
            )
            resp, err = _send_recv(
                host, final_port, request, timeout, connector
            )
            if err:
                error = err
            elif resp:
                accessible = True
                # Check if it's an Accept or Refuse
                # We'll parse the TNS header to get the packet type
                if len(resp) >= 8:
                    try:
                        pkt_type = struct.unpack("!B", resp[4:5])[0]
                    except struct.error:
                        pkt_type = None
                    if pkt_type == 0x02:  # Accept
                        version_data = _parse_accept_response(resp)
                        if version_data.get("version"):
                            version = str(version_data["version"])
                    elif pkt_type == 0x04:  # Refuse
                        # Even in a refuse, we might get some version info? Not usually.
                        # But we'll parse the refuse to get the error.
                        refuse_data = _parse_refuse_response(resp)
                        error = refuse_data.get("error")
                        version_data = refuse_data
                        # We don't set version from refuse
                    else:
                        error = f"Unexpected packet type 0x{pkt_type:02x}"
                else:
                    error = "Response too short to determine packet type"
            else:
                error = error or "No response from server"
        except Exception as exc:  # pragma: no cover
            error = str(exc)

    findings = _assess_version(version_data)

    return {
        "target": target,
        "host": host,
        "port": final_port,
        "accessible": bool(accessible),
        "version": version,
        "findings": findings,
        "error": error,
    }


def format_oracle_report_json(data: dict[str, Any]) -> str:
    """Format Oracle reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_oracle_report_markdown(data: dict[str, Any]) -> str:
    """Format Oracle reconnaissance results as Markdown."""
    lines: list[str] = []
    lines.append("# Oracle Reconnaissance Report")
    lines.append("")
    lines.append(f"**Target:** {data.get('target', '')}")
    lines.append(f"**Host:** {data.get('host') or 'N/A'}")
    lines.append(f"**Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"**Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    lines.append("")

    if data.get("version"):
        lines.append(f"**Server Version:** {data['version']}")
        lines.append("")

    findings = data.get("findings") or []
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines.append("## Findings\n- No notable findings\n")

    if data.get("error"):
        lines.append("## Error")
        lines.append("")
        lines.append(f"**Error:** {data['error']}")
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def format_oracle_report_csv(data: dict[str, Any]) -> str:
    """Format Oracle reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "version",
        "error",
    ])
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("version") or "",
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_PROBES",
    "DEFAULT_TIMEOUT",
    "_assess_version",
    "_build_connect_request",
    "_normalize_target",
    "_parse_accept_response",
    "_parse_refuse_response",
    "_send_recv",
    "format_oracle_report_csv",
    "format_oracle_report_json",
    "format_oracle_report_markdown",
    "run_oracle",
]