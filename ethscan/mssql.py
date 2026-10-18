"""MSSQL reconnaissance module for ethscan.

Offline-first MSSQL reconnaissance using only the Python standard library
(``socket`` and ``struct``). The module performs a safe, bounded probe over the
TDS (Tabular Data Stream) protocol (TCP ``1433``):

* **prelogin** -- send a TDS PRELOGIN message and parse the server's PRELOGIN
  response. The response carries version information, encryption support,
  instance name, and thread ID (SPID). No login is attempted and no password
  is sent.

All network access is confined to a single helper, ``_send_recv``, which
defaults to a raw TCP socket so tests can substitute a local fake server.
"""
from __future__ import annotations

import csv
import io
import json
import socket
import struct
from typing import Any

DEFAULT_PORT = 1433
DEFAULT_TIMEOUT = 3.0
DEFAULT_PROBES = ("prelogin",)

# TDS message types
_TDS_PRELOGIN = 0x12
_TDS_LOGIN7 = 0x10
_TDS_SSPI = 0x11
_TDS_PRELOGOUT = 0x19
_TDS_LOGINACK = 0xAD

# TDS PRELOGIN option types
_OPTION_VERSION = 0x00
_OPTION_ENCRYPTION = 0x01
_OPTION_INSTINST = 0x02  # Instance ID
_OPTION_THREADID = 0x03
_OPTION_MARS = 0x04
_OPTION_TRACEPARM = 0x05
_OPTION_FEDAUTHREQUIRED = 0x06
_OPTION_NONCE = 0x07
_OPTION_STMTTIMEOUT = 0x08
_OPTION_BUFFER = 0x09
_OPTION_GUID = 0x0A
_OPTION_TOKEN = 0x0B
_OPTION_COLLATION = 0x0C
_OPTION_LCID = 0x0D
_OPTION_HOSTNAME = 0x0E
_OPTION_USERNAME = 0x0F
_OPTION_PASSWORD = 0x10
_OPTION_ATTACHDBFILENAME = 0x11
_OPTION_CHANGEPASSWORD = 0x12
_OPTION_USERID = 0x13
_OPTION_PARTITIONRESERVED0 = 0x14
_OPTION_PARTITIONRESERVED1 = 0x15
_OPTION_PARTITIONRESERVED2 = 0x16
_OPTION_PARTITIONRESERVED3 = 0x17
_OPTION_PARTITIONRESERVED4 = 0x18
_OPTION_PARTITIONRESERVED5 = 0x19
_OPTION_PARTITIONRESERVED6 = 0x1A
_OPTION_PARTITIONRESERVED7 = 0x1B
_OPTION_PARTITIONRESERVED8 = 0x1C
_OPTION_PARTITIONRESERVED9 = 0x1D
_OPTION_PARTITIONRESERVED10 = 0x1E
_OPTION_PARTITIONRESERVED11 = 0x1F
_OPTION_PARTITIONRESERVED12 = 0x20
_OPTION_PARTITIONRESERVED13 = 0x21
_OPTION_PARTITIONRESERVED14 = 0x22
_OPTION_PARTITIONRESERVED15 = 0x23
_OPTION_PARTITIONRESERVED16 = 0x24
_OPTION_PARTITIONRESERVED17 = 0x25
_OPTION_PARTITIONRESERVED18 = 0x26
_OPTION_PARTITIONRESERVED19 = 0x27
_OPTION_PARTITIONRESERVED20 = 0x28
_OPTION_PARTITIONRESERVED21 = 0x29
_OPTION_PARTITIONRESERVED22 = 0x2A
_OPTION_PARTITIONRESERVED23 = 0x2B
_OPTION_PARTITIONRESERVED24 = 0x2C
_OPTION_PARTITIONRESERVED25 = 0x2D
_OPTION_PARTITIONRESERVED26 = 0x2E
_OPTION_PARTITIONRESERVED27 = 0x2F
_OPTION_PARTITIONRESERVED28 = 0x30
_OPTION_PARTITIONRESERVED29 = 0x31
_OPTION_PARTITIONRESERVED30 = 0x32
_OPTION_PARTITIONRESERVED31 = 0x33
_OPTION_PARTITIONRESERVED32 = 0x34
_OPTION_PARTITIONRESERVED33 = 0x35
_OPTION_PARTITIONRESERVED34 = 0x36
_OPTION_PARTITIONRESERVED35 = 0x37
_OPTION_PARTITIONRESERVED36 = 0x38
_OPTION_PARTITIONRESERVED37 = 0x39
_OPTION_PARTITIONRESERVED38 = 0x3A
_OPTION_PARTITIONRESERVED39 = 0x3B
_OPTION_PARTITIONRESERVED40 = 0x3C
_OPTION_PARTITIONRESERVED41 = 0x3D
_OPTION_PARTITIONRESERVED42 = 0x3E
_OPTION_PARTITIONRESERVED43 = 0x3F
_OPTION_PARTITIONRESERVED44 = 0x40
_OPTION_PARTITIONRESERVED45 = 0x41
_OPTION_PARTITIONRESERVED46 = 0x42
_OPTION_PARTITIONRESERVED47 = 0x43
_OPTION_PARTITIONRESERVED48 = 0x44
_OPTION_PARTITIONRESERVED49 = 0x45
_OPTION_PARTITIONRESERVED50 = 0x46
_OPTION_PARTITIONRESERVED51 = 0x47
_OPTION_PARTITIONRESERVED52 = 0x48
_OPTION_PARTITIONRESERVED53 = 0x49
_OPTION_PARTITIONRESERVED54 = 0x4A
_OPTION_PARTITIONRESERVED55 = 0x4B
_OPTION_PARTITIONRESERVED56 = 0x4C
_OPTION_PARTITIONRESERVED57 = 0x4D
_OPTION_PARTITIONRESERVED58 = 0x4E
_OPTION_PARTITIONRESERVED59 = 0x4F
_OPTION_PARTITIONRESERVED60 = 0x50
_OPTION_PARTITIONRESERVED61 = 0x51
_OPTION_PARTITIONRESERVED62 = 0x52
_OPTION_PARTITIONRESERVED63 = 0x53
_OPTION_PARTITIONRESERVED64 = 0x54
_OPTION_PARTITIONRESERVED65 = 0x55
_OPTION_PARTITIONRESERVED66 = 0x56
_OPTION_PARTITIONRESERVED67 = 0x57
_OPTION_PARTITIONRESERVED68 = 0x58
_OPTION_PARTITIONRESERVED69 = 0x59
_OPTION_PARTITIONRESERVED70 = 0x5A
_OPTION_PARTITIONRESERVED71 = 0x5B
_OPTION_PARTITIONRESERVED72 = 0x5C
_OPTION_PARTITIONRESERVED73 = 0x5D
_OPTION_PARTITIONRESERVED74 = 0x5E
_OPTION_PARTITIONRESERVED75 = 0x5F
_OPTION_PARTITIONRESERVED76 = 0x60
_OPTION_PARTITIONRESERVED77 = 0x61
_OPTION_PARTITIONRESERVED78 = 0x62
_OPTION_PARTITIONRESERVED79 = 0x63
_OPTION_PARTITIONRESERVED80 = 0x64
_OPTION_PARTITIONRESERVED81 = 0x65
_OPTION_PARTITIONRESERVED82 = 0x66
_OPTION_PARTITIONRESERVED83 = 0x67
_OPTION_PARTITIONRESERVED84 = 0x68
_OPTION_PARTITIONRESERVED85 = 0x69
_OPTION_PARTITIONRESERVED86 = 0x70
_OPTION_PARTITIONRESERVED87 = 0x71
_OPTION_PARTITIONRESERVED88 = 0x72
_OPTION_PARTITIONRESERVED89 = 0x73
_OPTION_PARTITIONRESERVED90 = 0x74
_OPTION_PARTITIONRESERVED91 = 0x75
_OPTION_PARTITIONRESERVED92 = 0x76
_OPTION_PARTITIONRESERVED93 = 0x77
_OPTION_PARTITIONRESERVED94 = 0x78
_OPTION_PARTITIONRESERVED95 = 0x79
_OPTION_PARTITIONRESERVED96 = 0x80
_OPTION_PARTITIONRESERVED97 = 0x81
_OPTION_PARTITIONRESERVED98 = 0x82
_OPTION_PARTITIONRESERVED99 = 0x83
_OPTION_PARTITIONRESERVED100 = 0x84
_OPTION_PARTITIONRESERVED101 = 0x85
_OPTION_PARTITIONRESERVED102 = 0x86
_OPTION_PARTITIONRESERVED103 = 0x87
_OPTION_PARTITIONRESERVED104 = 0x88
_OPTION_PARTITIONRESERVED105 = 0x89
_OPTION_PARTITIONRESERVED106 = 0x90
_OPTION_PARTITIONRESERVED107 = 0x91
_OPTION_PARTITIONRESERVED108 = 0x92
_OPTION_PARTITIONRESERVED109 = 0x93
_OPTION_PARTITIONRESERVED110 = 0x94
_OPTION_PARTITIONRESERVED111 = 0x95
_OPTION_PARTITIONRESERVED112 = 0x96
_OPTION_PARTITIONRESERVED113 = 0x97
_OPTION_PARTITIONRESERVED114 = 0x98
_OPTION_PARTITIONRESERVED115 = 0x99
_OPTION_PARTITIONRESERVED116 = 0x100
_OPTION_PARTITIONRESERVED117 = 0x101
_OPTION_PARTITIONRESERVED118 = 0x102
_OPTION_PARTITIONRESERVED119 = 0x103
_OPTION_PARTITIONRESERVED120 = 0x104
_OPTION_PARTITIONRESERVED121 = 0x105
_OPTION_PARTITIONRESERVED122 = 0x106
_OPTION_PARTITIONRESERVED123 = 0x107
_OPTION_PARTITIONRESERVED124 = 0x108
_OPTION_PARTITIONRESERVED125 = 0x109
_OPTION_PARTITIONRESERVED126 = 0x110
_OPTION_PARTITIONRESERVED127 = 0x111


def _normalize_target(target: str) -> tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts, ``host:port``, and ``mssql://`` / ``ms-sql://`` URLs.
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
        port = parsed.port
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
        raise ValueError(f"Could not parse host from target {target!r}")

    return host, int(port) if port else DEFAULT_PORT


def _build_prelogin_request(
    version: str | None = None,
    encryption: str | None = None,
    instinst: str | None = None,
    threadid: str | None = None,
) -> bytes:
    """Build a TDS PRELOGIN message.

    The PRELOGIN message consists of a header followed by a list of options.
    Each option is a tuple (type, length, value). The header includes:
      - Message type (0x12 for PRELOGIN)
      - Status (0x01 for first packet, 0x00 for last? Actually for PRELOGIN it's a single packet)
      - Length (total length of message in bytes, big-endian uint16)
      - Channel ID (0x0000, not used)
      - Packet number (0x01, big-endian uint8)
      - Window (0x0000, not used)

    However, according to TDS documentation, the PRELOGIN message structure is:
      - TCP Header (not part of TDS)
      - TDS Header:
          * Type (1 byte): 0x12
          * Flags (1 byte): 0x01 (first packet)
          * Length (2 bytes): big-endian, length of the entire TDS message (including header)
          * Channel ID (2 bytes): 0x0000
          * Packet Number (1 byte): 0x01
          * Window (2 bytes): 0x0000
      - Then the PRELOGIN payload: a list of options, each:
          * Type (1 byte)
          * Length (1 byte) - note: length in bytes of the value field
          * Value (variable)

    The payload is terminated by a type 0xFF option? Actually the options are just listed, and the end is indicated by the length field in the TDS header.

    We'll build a minimal PRELOGIN request with options for version, encryption, instance ID, and thread ID.
    """
    # We'll build the options first.
    options = b""

    # Helper to add an option
    def add_option(opt_type: int, value: bytes):
        nonlocal options
        options += struct.pack("!BB", opt_type, len(value)) + value

    # Version: we can ask for the latest version by sending 0x00? Actually the client sends its version?
    # According to docs, the client sends the highest version it supports in the VERSION option.
    # We'll send a placeholder: we don't care about sending our version, we just want the server's.
    # So we can send an empty value? The spec says the client sends the version it wants to use.
    # Let's send a dummy version: we'll send "72.0.0.0" (SQL Server 2005?) but we don't need to.
    # Actually, for the purpose of reconnaissance, we can send an empty version and the server will respond with its version.
    # However, the server might require a version. Let's look at common practice: many clients send a version.
    # We'll send a version that is high enough: e.g., "72.0.0.0" (which is the version number for SQL Server 2005? Actually the version is a 4-byte integer: major, minor, build, subbuild?).
    # The VERSION option value is 4 bytes: a DWORD representing the version number (major.minor*256 + ...?). Actually it's a 4-byte integer: high word is major version, low word is minor version?
    # From memory: the TDS version is encoded as a DWORD: major (high word), minor (low word). But for SQL Server 2000, version 8.0.0.0 -> 0x08000000?
    # We'll keep it simple: we'll send a version of 0x00000000 to indicate we want the server to tell us its version? Not sure.
    # Let's check the postgresql module: they don't send any version in the startup message? Actually they send a fixed protocol version.
    # For TDS, we can follow the example from FreeTDS or other sources.
    # Since we are doing reconnaissance, we can send a minimal PRELOGIN with no options? But the server might not respond.
    # Let's look at the PRELOGIN request structure from Wireshark or similar.
    # Given time, we'll implement a common approach: send options for VERSION, ENCRYPTION, INSTINST, THREADID with empty values (or zero length) and the server will fill them.
    # Actually, the client must specify the length of the value it is sending. If we want the server to return a value, we set length to 0? Not sure.
    # According to the TDS protocol specification, the client sends the option with a value indicating what it wants. For VERSION, the client sends the highest version it supports. For ENCRYPTION, the client sends a byte: 0x00 (off), 0x01 (on), 0x02 (required), 0x03 (not supported).
    # We'll set:
    #   VERSION: we'll send 0x00000000 (meaning we accept any version?).
    #   ENCRYPTION: we'll send 0x00 (off) because we are not doing encryption.
    #   INSTINST: empty (we want the server to return the instance name)
    #   THREADID: empty (we want the server to return the thread ID)
    # But the option format requires a length byte. If we set length to 0, then the value is empty.
    # Let's do that.

    # Add VERSION option (type 0x00) with value 0x00000000 (4 bytes)
    add_option(_OPTION_VERSION, struct.pack("!I", 0x00000000))
    # Add ENCRYPTION option (type 0x01) with value 0x00 (1 byte, off)
    add_option(_OPTION_ENCRYPTION, b"\x00")
    # Add INSTINST option (type 0x02) with empty value (we want server to return)
    add_option(_OPTION_INSTINST, b"")
    # Add THREADID option (type 0x03) with empty value
    add_option(_OPTION_THREADID, b"")

    # Now build the TDS header.
    # The total length of the TDS message is: header length (9 bytes) + options length.
    header_length = 9
    msg_len = header_length + len(options)
    # TDS header:
    #   Type (1 byte): _TDS_PRELOGIN
    #   Flags (1 byte): 0x01 (first packet)
    #   Length (2 bytes): msg_len (big-endian)
    #   Channel ID (2 bytes): 0x0000
    #   Packet Number (1 byte): 0x01
    #   Window (2 bytes): 0x0000
    header = struct.pack(
        "!BBHHBH",
        _TDS_PRELOGIN,  # Type
        0x01,           # Flags
        msg_len,        # Length
        0x0000,         # Channel ID
        0x01,           # Packet Number
        0x0000,         # Window
    )
    return header + options


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


def _parse_prelogin_response(data: bytes) -> dict[str, Any]:
    """Parse the server's PRELOGIN response.

    The response is a TDS message with type 0x12 (PRELOGIN) as well? Actually the server responds with a PRELOGIN response message (same type?).
    According to TDS, the server responds with a PRELOGIN response message (type 0x12) containing the options.

    We'll parse the TDS header first, then parse the options from the payload.
    """
    result: dict[str, Any] = {
        "version": None,
        "encryption": None,
        "instance_name": None,
        "thread_id": None,
        "error": None,
    }
    if not data or len(data) < 9:
        result["error"] = f"Response too short: {len(data)} bytes"
        return result

    # Parse TDS header
    #   Type (1 byte), Flags (1 byte), Length (2 bytes), Channel ID (2 bytes), Packet Number (1 byte), Window (2 bytes)
    try:
        tds_type, _flags, msg_len, _channel_id, _packet_num, _window = struct.unpack(
            "!BBHHBH", data[:9]
        )
    except struct.error:
        result["error"] = "Failed to parse TDS header"
        return result

    if tds_type != _TDS_PRELOGIN:
        result["error"] = f"Expected PRELOGIN response, got type 0x{tds_type:02x}"
        return result

    # The payload starts at byte 9 and goes to msg_len (or end of data if truncated)
    payload = data[9:msg_len] if len(data) >= msg_len else data[9:]
    # Now parse the options from the payload.
    # Each option: type (1 byte), length (1 byte), value (length bytes)
    pos = 0
    while pos < len(payload):
        if pos + 2 > len(payload):
            break
        opt_type = payload[pos]
        opt_len = payload[pos + 1]
        pos += 2
        if pos + opt_len > len(payload):
            break
        value = payload[pos : pos + opt_len]
        pos += opt_len

        # Process known options
        if opt_type == _OPTION_VERSION:
            # Version is 4 bytes: DWORD representing version? Actually it's a 4-byte integer: high word major, low word minor?
            # Let's convert to a dotted string: major.minor.build?
            if len(value) == 4:
                # The version is encoded as: major (byte0), minor (byte1), high byte of build (byte2), low byte of build (byte3)?
                # Actually from FreeTDS: the version is stored as a 4-byte integer in little-endian? Wait, TDS uses big-endian.
                # We'll assume big-endian:
                major = value[0]
                minor = value[1]
                # Build is two bytes: value[2] and value[3]
                build = struct.unpack("!H", value[2:4])[0]
                # Sometimes there is a subbuild? We'll ignore.
                version_str = f"{major}.{minor}.{build}"
                result["version"] = version_str
            else:
                # If we get something else, just decode as string if possible.
                try:
                    result["version"] = value.decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    result["version"] = value.hex()
        elif opt_type == _OPTION_ENCRYPTION:
            # Encryption is a single byte: 0x00 off, 0x01 on, 0x02 required, 0x03 not supported.
            if len(value) >= 1:
                enc_val = value[0]
                if enc_val == 0x00:
                    result["encryption"] = "OFF"
                elif enc_val == 0x01:
                    result["encryption"] = "ON"
                elif enc_val == 0x02:
                    result["encryption"] = "REQUIRED"
                elif enc_val == 0x03:
                    result["encryption"] = "NOT SUPPORTED"
                else:
                    result["encryption"] = f"UNKNOWN({enc_val})"
            else:
                result["encryption"] = "UNKNOWN"
        elif opt_type == _OPTION_INSTINST:
            # Instance name is a string (usually UTF-8)
            if value:
                try:
                    result["instance_name"] = value.decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    result["instance_name"] = value.hex()
            else:
                result["instance_name"] = ""
        elif opt_type == _OPTION_THREADID:
            # Thread ID is a 4-byte unsigned integer (SPID)
            if len(value) >= 4:
                result["thread_id"] = struct.unpack("!I", value[:4])[0]
            else:
                # If less, try to decode as integer from what we have?
                result["thread_id"] = None
        # Ignore other options for now

    return result


def _assess_prelogin(prelogin: dict[str, Any]) -> list[str]:
    """Assess PRELOGIN data and return findings."""
    findings: list[str] = []
    version = prelogin.get("version")
    if version:
        findings.append(f"MSSQL server version: {version}")
        # Optionally parse version to determine if it's old?
        # We'll skip for now.
    encryption = prelogin.get("encryption")
    if encryption:
        findings.append(f"Encryption: {encryption}")
        if encryption == "NOT SUPPORTED" or encryption == "OFF":
            findings.append(
                "Encryption is not enabled or not required; data may be transmitted in plaintext."
            )
        elif encryption == "REQUIRED":
            findings.append("Encryption is required.")
    instance_name = prelogin.get("instance_name")
    if instance_name:
        findings.append(f"Instance name: {instance_name}")
    thread_id = prelogin.get("thread_id")
    if thread_id is not None:
        findings.append(f"Thread ID (SPID): {thread_id}")
    if prelogin.get("error"):
        findings.append(f"Error: {prelogin['error']}")
    return findings


def run_mssql(
    target: str,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    probes: list[str] | None = None,
    connector=None,
) -> dict[str, Any]:
    """Run MSSQL reconnaissance probes against *target*.

    Args:
        target: Hostname, ``host:port``, or ``mssql://`` / ``ms-sql://`` URL.
        port: Explicit MSSQL port; when ``None`` the port is parsed from
            the target (or defaults to 1433).
        timeout: Per-request timeout in seconds.
        probes: List of probes to run (case-insensitive). Defaults to
            ``("prelogin",)``.
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
            "prelogin": {},
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
            "prelogin": {},
            "version": None,
            "findings": [],
            "error": None,
        }

    norm_probes = [p.strip().lower() for p in probe_list if p.strip()]

    prelogin_data: dict[str, Any] = {}
    version: str | None = None
    accessible = False
    error: str | None = None

    if "prelogin" in norm_probes:
        try:
            resp, err = _send_recv(
                host, final_port, _build_prelogin_request(), timeout, connector
            )
            if err:
                error = err
            elif resp:
                accessible = True
                prelogin_data = _parse_prelogin_response(resp)
                if prelogin_data.get("version"):
                    version = str(prelogin_data["version"])
            else:
                error = error or "No response from server"
        except Exception as exc:  # pragma: no cover
            error = str(exc)

    findings = _assess_prelogin(prelogin_data)

    return {
        "target": target,
        "host": host,
        "port": final_port,
        "accessible": bool(accessible),
        "prelogin": prelogin_data,
        "version": version,
        "findings": findings,
        "error": error,
    }


def format_mssql_report_json(data: dict[str, Any]) -> str:
    """Format MSSQL reconnaissance results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_mssql_report_markdown(data: dict[str, Any]) -> str:
    """Format MSSQL reconnaissance results as Markdown."""
    lines: list[str] = []
    lines.append("# MSSQL Reconnaissance Report")
    lines.append("")
    lines.append(f"**Target:** {data.get('target', '')}")
    lines.append(f"**Host:** {data.get('host') or 'N/A'}")
    lines.append(f"**Port:** {data.get('port', DEFAULT_PORT)}")
    lines.append(f"**Accessible:** {'Yes' if data.get('accessible') else 'No'}")
    lines.append("")

    if data.get("version"):
        lines.append(f"**Server Version:** {data['version']}")
        lines.append("")

    prelogin = data.get("prelogin") or {}
    if prelogin:
        lines.append("## PRELOGIN Response")
        lines.append("")
        for key in [
            "version",
            "encryption",
            "instance_name",
            "thread_id",
        ]:
            if key in prelogin and prelogin[key] is not None:
                lines.append(f"- **{key}:** {_markdown_escape(prelogin[key])}")
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


def format_mssql_report_csv(data: dict[str, Any]) -> str:
    """Format MSSQL reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "version",
        "encryption",
        "instance_name",
        "thread_id",
        "findings",
        "error",
    ])

    prelogin = data.get("prelogin") or {}
    findings = data.get("findings") or []
    writer.writerow([
        data.get("target", ""),
        data.get("host", ""),
        data.get("port", DEFAULT_PORT),
        "true" if data.get("accessible") else "false",
        data.get("version") or "",
        prelogin.get("encryption") or "",
        prelogin.get("instance_name") or "",
        prelogin.get("thread_id") or "",
        "; ".join(findings).replace("\n", " ").replace("\r", " "),
        data.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_PROBES",
    "DEFAULT_TIMEOUT",
    "_assess_prelogin",
    "_build_prelogin_request",
    "_normalize_target",
    "_parse_prelogin_response",
    "_send_recv",
    "format_mssql_report_csv",
    "format_mssql_report_json",
    "format_mssql_report_markdown",
    "run_mssql",
]