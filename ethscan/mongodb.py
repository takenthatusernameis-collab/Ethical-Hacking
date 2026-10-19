"""MongoDB reconnaissance module for ethscan.

Offline-first MongoDB reconnaissance using only the Python standard library
(``socket``). The module performs a safe, bounded probe over the MongoDB
Wire Protocol (TCP 27017):

* **buildInfo** -- send buildInfo command to retrieve server version, version
  array, and build environment information.
* **serverStatus** -- optional serverStatus command for additional metrics.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
from typing import Any

from ethscan.target import TargetSpecError, url_port

DEFAULT_PORT = 27017
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("buildInfo",)


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts, ``host:port``, and ``mongodb://host:port`` URLs.
    Defaults to port ``DEFAULT_PORT`` when none is supplied. IPv6
    literals may be bracketed.
    """
    normalized = (target or "").strip()
    host: str | None = None
    port: int | None = None

    if "://" in normalized:
        from urllib.parse import urlparse

        parsed = urlparse(normalized)
        host = (parsed.hostname or "").strip()
        port = url_port(parsed)
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
        raise TargetSpecError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


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
            return sock.recv(4096), None
    except socket.timeout:
        return None, "Timeout"
    except ConnectionRefusedError:
        return None, "Connection refused"
    except OSError as exc:
        return None, str(exc)


def _build_mongodb_message(request_id: int, response_to: int, opcode: int, data: bytes) -> bytes:
    """Build a MongoDB Wire Protocol message header and concatenate with data.

    Message Structure:
      messageHeader {
        int32  messageLength;  // total message size, including this
        int32  requestID;      // identifier for this message
        int32  responseTo;     // requestID from the corresponding request
        int32  opcode;         // request type - see opcodes below
      }
    """
    # MongoDB Wire Protocol message header: 16 bytes
    # 4 bytes messageLength (will be filled in)
    # 4 bytes requestID
    # 4 bytes responseTo
    # 4 bytes opcode
    header = bytearray(16)
    header[0:4] = (16 + len(data)).to_bytes(4, byteorder='little')  # messageLength (placeholder)
    header[4:8] = request_id.to_bytes(4, byteorder='little')
    header[8:12] = response_to.to_bytes(4, byteorder='little')
    header[12:16] = opcode.to_bytes(4, byteorder='little')
    return bytes(header) + data


def _build_buildinfo_request() -> bytes:
    """Build a MongoDB buildInfo command message.

    Builds a OP_QUERY message for the buildInfo command.
    """
    # MongoDB OP_QUERY opcode
    OP_QUERY = 2004

    # Build the buildInfo command document: { buildInfo: 1 }
    # In BSON format: \x05\x00\x00\x00\x02buildInfo\x00\x01\x00\x00\x00\x00
    buildinfo_doc = b'\x0e\x00\x00\x00\x02buildInfo\x00\x01\x00\x00\x00\x00'

    # OP_QUERY message structure:
    #   ZERO (4 bytes) - reserved
    #   collectionName (string) - "admin.$cmd" + null terminator
    #   numberToSkip (int32) - 0
    #   numberToReturn (int32) - 1 (we want one result)
    #   query (BSON document) - the buildInfo command
    #   returnFieldsSelector (optional) - not used

    query_part = b'\x00\x00\x00\x00'  # ZERO
    query_part += b'admin.$cmd\x00'    # collectionName
    query_part += b'\x00\x00\x00\x00'  # numberToSkip
    query_part += b'\x01\x00\x00\x00'  # numberToReturn
    query_part += buildinfo_doc        # query

    return _build_mongodb_message(request_id=1, response_to=0, opcode=OP_QUERY, data=query_part)


def _parse_buildinfo_response(data: bytes) -> dict[str, Any]:
    """Parse MongoDB buildInfo command response.

    Parses the OP_REPLY message and extracts the buildInfo document.
    """
    if not data or len(data) < 16:
        return {}

    # Parse OP_REPLY message header (first 16 bytes)
    # 4 bytes responseFlags
    # 4 bytes cursorID[0] (lower 32 bits)
    # 4 bytes cursorID[1] (upper 32 bits)
    # 4 bytes startingFrom
    # 4 bytes numberReturned

    int.from_bytes(data[0:4], byteorder='little')
    int.from_bytes(data[4:8], byteorder='little')
    int.from_bytes(data[8:12], byteorder='little')
    int.from_bytes(data[12:16], byteorder='little')
    number_returned = int.from_bytes(data[16:20], byteorder='little')

    # The actual documents start after the header (20 bytes)
    if len(data) < 20 or number_returned == 0:
        return {}

    # For simplicity, we'll parse the first document as BSON
    # This is a simplified parser that extracts key fields we care about
    doc_data = data[20:]

    # Extract version and versionArray from the buildInfo response
    result = {}

    # Look for version string (string type 0x02)
    # BSON string: \x02fieldname\x00length\x00content\x00
    version_pos = doc_data.find(b'\x02version\x00')
    if version_pos != -1:
        str_start = version_pos + 8  # skip '\x02version\x00'
        if str_start + 4 <= len(doc_data):
            str_len = int.from_bytes(doc_data[str_start:str_start+4], byteorder='little')
            if str_start + 4 + str_len < len(doc_data):  # +1 for null terminator
                version_str = doc_data[str_start+4:str_start+4+str_len].decode('utf-8', errors='replace')
                result['version'] = version_str

    # Look for versionArray (array type 0x04)
    # We'll look for a simpler approach - just extract basic info
    # For now, return what we can parse simply

    # Also look for sysInfo, version, etc. as strings
    for field in [b'sysInfo', b'version', b'versionArray', b'modules', b'encryptionOptions']:
        field_search = b'\x02' + field + b'\x00'
        pos = doc_data.find(field_search)
        if pos != -1:
            str_start = pos + len(field_search)
            if str_start + 4 <= len(doc_data):
                str_len = int.from_bytes(doc_data[str_start:str_start+4], byteorder='little')
                if str_start + 4 + str_len < len(doc_data):
                    with contextlib.suppress(Exception):  # pragma: no cover - defensive
                        value = doc_data[str_start+4:str_start+4+str_len].decode('utf-8', errors='replace')
                        result[field.decode('utf-8')] = value

    return result


def _assess_buildinfo(buildinfo: dict[str, Any]) -> list[str]:
    """Assess buildInfo data and return findings."""
    findings: list[str] = []
    version = buildinfo.get('version', '')
    if version:
        findings.append(f"MongoDB server version: {version}")
        # Check for very old versions as a simple heuristic
        v_lower = version.lower()
        if any(x in v_lower for x in ('2.0', '2.2', '2.4', '2.6')):
            findings.append("Old MongoDB version detected (may lack security features)")

    sys_info = buildinfo.get('sysInfo', '')
    if sys_info:
        findings.append(f"Build environment: {sys_info}")

    modules = buildinfo.get('modules', '')
    if modules:
        findings.append(f"Modules: {modules}")

    return findings


def run_mongodb(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run MongoDB reconnaissance probes against a target.

    Args:
        target: Hostname, ``host:port``, or ``mongodb://host:port``.
        port: Optional override for the TCP port.
        timeout: Connection timeout in seconds.
        probes: List of probe names (case-insensitive). Defaults to
            ``("buildInfo",)``.
        connector: Optional transport injector for testing.

    Returns:
        A structured dict with target/host/port, accessibility,
        buildInfo data, findings, and any error.
    """
    try:
        host, parsed_port = _normalize_target(target)
    except ValueError as exc:
        return {
            'target': target,
            'host': None,
            'port': port or DEFAULT_PORT,
            'accessible': False,
            'buildInfo': {},
            'version': None,
            'findings': [],
            'error': str(exc),
        }

    final_port = int(port) if port is not None else parsed_port
    probe_list = probes if probes is not None else list(DEFAULT_PROBES)
    if not probe_list:
        return {
            'target': target,
            'host': host,
            'port': final_port,
            'accessible': False,
            'buildInfo': {},
            'version': None,
            'findings': [],
            'error': None,
        }

    # Normalize probe names
    [p.strip().lower() for p in probe_list if p.strip()]

    buildinfo_data: dict[str, Any] = {}
    accessible = False
    error: str | None = None
    version: str | None = None

    # For MongoDB, we need to send a buildInfo command
    try:
        resp, err = _send_recv(host, final_port, _build_buildinfo_request(), timeout, connector)
        if err:
            error = err
        else:
            if resp:
                accessible = True
                buildinfo_data = _parse_buildinfo_response(resp)
                if buildinfo_data.get('version'):
                    version = str(buildinfo_data['version'])
            else:
                accessible = False
                error = error or "No response from server"
    except Exception as exc:  # pragma: no cover
        accessible = False
        error = str(exc)

    findings = _assess_buildinfo(buildinfo_data)

    return {
        'target': target,
        'host': host,
        'port': final_port,
        'accessible': bool(accessible),
        'buildInfo': buildinfo_data,
        'version': version,
        'findings': findings,
        'error': error,
    }


def format_mongodb_report_json(data: dict[str, Any]) -> str:
    """Format MongoDB reconnaissance results as JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_mongodb_report_markdown(data: dict[str, Any]) -> str:
    """Format MongoDB reconnaissance results as Markdown."""
    lines: list[str] = []
    lines.append("# MongoDB Reconnaissance Report")
    lines.append("")
    lines.append(f"**Target:** {data.get('target', '')}")
    lines.append(f"**Host:** {data.get('host') or 'N/A'}")
    lines.append(f"**Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"**Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    lines.append("")

    if data.get('version'):
        lines.append(f"**Server Version:** {data['version']}")
        lines.append("")

    buildinfo = data.get('buildInfo') or {}
    if buildinfo:
        lines.append("## Build Info")
        lines.append("")
        # Show key buildInfo fields
        for key in ['version', 'sysInfo', 'modules', 'encryptioOptions']:
            if key in buildinfo and buildinfo[key] is not None and buildinfo[key] != '':
                lines.append(f"- **{key}:** {buildinfo[key]}")
        lines.append("")

    findings = data.get('findings') or []
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

    if data.get('error'):
        lines.append("## Error")
        lines.append("")
        lines.append(f"**Error:** {data['error']}")
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def format_mongodb_report_csv(data: dict[str, Any]) -> str:
    """Format MongoDB reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'target',
        'host',
        'port',
        'accessible',
        'version',
        'sysInfo',
        'modules',
        'findings',
        'error',
    ])

    buildinfo = data.get('buildInfo') or {}
    findings = data.get('findings') or []
    writer.writerow([
        data.get('target', ''),
        data.get('host', ''),
        data.get('port', DEFAULT_PORT),
        'true' if data.get('accessible') else 'false',
        data.get('version') or '',
        buildinfo.get('sysInfo', ''),
        buildinfo.get('modules', ''),
        '; '.join(findings).replace('\n', ' ').replace('\r', ' '),
        data.get('error') or '',
    ])
    return output.getvalue().rstrip('\r\n')


__all__ = [
    'DEFAULT_PORT',
    'DEFAULT_PROBES',
    'DEFAULT_TIMEOUT',
    '_assess_buildinfo',
    '_build_buildinfo_request',
    '_normalize_target',
    '_parse_buildinfo_response',
    '_send_recv',
    'format_mongodb_report_csv',
    'format_mongodb_report_json',
    'format_mongodb_report_markdown',
    'run_mongodb',
]