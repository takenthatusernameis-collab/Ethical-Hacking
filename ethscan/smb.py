"""SMB/CIFS reconnaissance module for ethscan.

Offline-forward SMB reconnaissance using only the Python standard library
(``socket`` and ``struct``).

The module performs a single, safe, bounded probe: an SMB1 ``SMB_COM_NEGOTIATE``
dialect negotiation request. This is the traditional SMB "banner/dialect"
probe -- it elicits no authentication exchange and reveals the negotiated
dialect, the server's security mode, message-signing policy, and the NTLM
server challenge.

The SMB1 SecurityMode bit decode mirrors nmap's ``smb-security-mode`` script:

    0x01  user-level authentication supported (else share-level)
    0x02  challenge/response (NTLM) authentication supported
    0x04  message signing enabled (supported)
    0x08  message signing required

All network access is confined to a single helper, ``_send_recv``, so tests
can inject a fake connector and exercise request building and response parsing
without touching the network.

Note: SMB1 is disabled by default on modern Windows hosts and many modern Samba
installations. In that case the server refuses/resets the connection and the
probe reports ``accessible=False`` with a descriptive error. Use ``--port 445``
(the default) for direct SMB over TCP.
"""

import csv
import io
import json
import socket
import struct
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PORT = 445
DEFAULT_TIMEOUT = 3.0

# SMB protocol magic signatures (the first four bytes of every SMB frame).
SMB1_MAGIC = b"\xffSMB"
SMB2_MAGIC = b"\xfeSMB"

# SMB command codes.
SMB_COM_NEGOTIATE = 0x72  # request and response

# SMB1 SecurityMode bit fields from the SMB_COM_NEGOTIATE response. These mirror
# the bits decoded by nmap's smb-security-mode script (and MS-SMB 2.2.4.2).
SMB1_SECURITY_USER = 0x01               # user-level auth supported (else share-level)
SMB1_SECURITY_CHALLENGE_RESPONSE = 0x02  # challenge/response (NTLM) auth supported
SMB1_SECURITY_SIGNING_ENABLED = 0x04   # message signing enabled (supported)
SMB1_SECURITY_SIGNING_REQUIRED = 0x08  # message signing required

# Default SMB1 dialects offered to the server, in preference order. The
# negotiated DialectIndex is a 0-based index into this list; 0xFFFF means no
# common dialect was agreed.
DEFAULT_DIALECTS: Tuple[str, ...] = ("NT LM 0.12", "Samba", "Core", "CorePlus")

# Length of the SMB1 header (signature + command + status + flags + ids).
_SMB1_HEADER_LEN = 32


def _normalize_target(target: str) -> Tuple[str, int]:
    """Parse a target into a bare host and integer port.

    Accepts bare hosts (``192.168.1.5``), ``host:port``, and
    ``smb://host:port`` style URLs. IPv6 literals may be bracketed. When no
    port is supplied, ``DEFAULT_PORT`` (445) is used.
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
        port = None

    # IPv6 literal in brackets, optionally followed by :port.
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
    """Send ``request`` to ``host:port`` and return ``(data, error)``.

    When ``connector`` is provided it is called as
    ``connector(host, port, request, timeout)`` and must return a
    ``(data, error)`` tuple, bypassing the network. This is what tests use.
    """
    if connector is not None:
        return connector(host, port, request, timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.sendall(request)
        data = sock.recv(65536)
        return data, None
    except socket.timeout:
        return None, "timeout"
    except OSError as exc:
        return None, str(exc)
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _build_smb1_negotiate_request(
    dialects: Tuple[str, ...] = DEFAULT_DIALECTS,
) -> bytes:
    """Build a raw SMB1 ``SMB_COM_NEGOTIATE`` request.

    Layout:
      * 32-byte SMB header (little-endian): signature ``\\xffSMB``, command
        ``0x72`` (``SMB_COM_NEGOTIATE``), zero status/flags/ids.
      * WordCount (1 byte) = 0 (negotiate request carries no fixed parameters).
      * ByteCount (2 bytes, little-endian) = length of the dialect blob.
      * Dialect blob: for each dialect, ``\\x02`` + ASCII name + ``\\x00``.
    """
    buf = bytearray()
    # --- SMB header (32 bytes, little-endian) ---
    buf += SMB1_MAGIC                                   # Protocol[4]
    buf += struct.pack("<B", SMB_COM_NEGOTIATE)        # Command
    buf += struct.pack("<I", 0)                        # Status (ErrorClass/reserved/ErrorCode)
    buf += struct.pack("<B", 0)                        # Flags1
    buf += struct.pack("<H", 0x0001)                   # Flags2 (long file names supported)
    buf += struct.pack("<H", 0)                         # PIDHigh
    buf += b"\x00" * 8                                  # Reserved / Signature
    buf += struct.pack("<H", 0)                         # Reserved
    buf += struct.pack("<H", 0)                         # Tid
    buf += struct.pack("<H", 0)                         # Pid
    buf += struct.pack("<H", 0)                         # Uid
    buf += struct.pack("<H", 0)                         # Mid
    # --- Parameters: WordCount + ByteCount + dialect blob ---
    buf += struct.pack("<B", 0)                         # WordCount = 0
    dialect_blob = b"".join(
        b"\x02" + d.encode("ascii", "replace") + b"\x00" for d in dialects
    )
    buf += struct.pack("<H", len(dialect_blob))         # ByteCount (little-endian)
    buf += dialect_blob
    return bytes(buf)


def _parse_smb_response(
    data: Optional[bytes],
    dialects: Tuple[str, ...] = DEFAULT_DIALECTS,
) -> Dict[str, Any]:
    """Parse an SMB response, returning negotiated dialect/security info.

    Handles a well-formed SMB1 ``SMB_COM_NEGOTIATE`` response. A non-SMB or
    truncated response is reported via the ``error`` field instead of raising.
    """
    result: Dict[str, Any] = {
        "protocol": None,
        "command": None,
        "status": None,
        "dialect": None,
        "dialect_index": None,
        "security_mode": 0,
        "security_flags": [],
        "user_security": False,
        "challenge_response": False,
        "signing_enabled": False,
        "signing_required": False,
        "challenge": None,
        "raw_preview": "",
        "error": None,
    }

    if not data:
        result["error"] = "no response received"
        return result

    result["raw_preview"] = data[:48].hex()

    if len(data) < _SMB1_HEADER_LEN + 1:
        result["error"] = "response too short to be an SMB1 message"
        return result

    signature = data[0:4]
    if signature == SMB2_MAGIC:
        result["protocol"] = "SMB2"
        result["error"] = "SMB2 response received for an SMB1 negotiate (not decoded)"
        return result
    if signature != SMB1_MAGIC:
        result["error"] = "response is not an SMB message"
        return result

    result["protocol"] = "SMB1"
    result["command"] = data[4]
    result["status"] = struct.unpack("<I", data[5:9])[0]

    word_count = data[_SMB1_HEADER_LEN]
    params_len = word_count * 2
    if word_count < 1 or _SMB1_HEADER_LEN + 1 + params_len + 2 > len(data):
        result["error"] = "truncated negotiate response parameters"
        return result

    # DialectIndex is the first parameter word (offset 33, little-endian).
    dialect_index = struct.unpack("<H", data[33:35])[0]
    result["dialect_index"] = dialect_index
    if dialect_index == 0xFFFF:
        result["dialect"] = "(no common dialect)"
    elif dialect_index < len(dialects):
        result["dialect"] = dialects[dialect_index]
    else:
        result["dialect"] = f"unknown (index {dialect_index})"

    # SecurityMode is a single byte immediately after DialectIndex (offset 35).
    security_mode = data[35]
    result["security_mode"] = security_mode
    flags: List[str] = []
    if security_mode & SMB1_SECURITY_USER:
        result["user_security"] = True
        flags.append("user_security")
    if security_mode & SMB1_SECURITY_CHALLENGE_RESPONSE:
        result["challenge_response"] = True
        flags.append("challenge_response")
    if security_mode & SMB1_SECURITY_SIGNING_ENABLED:
        result["signing_enabled"] = True
        flags.append("signing_enabled")
    if security_mode & SMB1_SECURITY_SIGNING_REQUIRED:
        result["signing_required"] = True
        flags.append("signing_required")
    result["security_flags"] = flags

    # Data section: ByteCount (2 bytes) follows the parameter words. The first
    # 8 bytes of the data section are the server challenge (ChallengeString).
    bytecount_off = _SMB1_HEADER_LEN + 1 + params_len
    bytecount = struct.unpack("<H", data[bytecount_off:bytecount_off + 2])[0]
    data_start = bytecount_off + 2
    blob = data[data_start:data_start + bytecount]
    if len(blob) >= 8:
        result["challenge"] = blob[:8].hex()

    return result


def _build_banner(parsed: Dict[str, Any]) -> Optional[str]:
    """Build a short human-readable banner from a parsed SMB response."""
    if parsed.get("protocol") != "SMB1":
        return None
    dialect = parsed.get("dialect")
    if dialect == "(no common dialect)":
        return "SMB1 endpoint responded; no common dialect agreed"

    if parsed.get("signing_required"):
        signing = "required"
    elif parsed.get("signing_enabled"):
        signing = "enabled"
    else:
        signing = "disabled"
    auth = "challenge-response" if parsed.get("challenge_response") else "plaintext"

    parts = [
        f"dialect={dialect}",
        f"signing={signing}",
        f"auth={auth}",
    ]
    if parsed.get("challenge"):
        parts.append("challenge present")
    return "SMB1 negotiate OK; " + ", ".join(parts)


def run_smb(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    dialects: Optional[Tuple[str, ...]] = None,
    connector=None,
) -> Dict[str, Any]:
    """Run an SMB1 negotiate probe against ``target``.

    Parameters mirror the CLI: ``target`` is a host, ``host:port``, or
    ``smb://host:port``; ``port`` overrides the parsed/default port (445);
    ``timeout`` bounds the TCP exchange; ``connector`` injects a fake transport
    for testing.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port
    dial = tuple(dialects) if dialects else DEFAULT_DIALECTS

    results: Dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "accessible": False,
        "protocol": None,
        "dialect": None,
        "dialect_index": None,
        "security_mode": 0,
        "security_flags": [],
        "user_security": False,
        "challenge_response": False,
        "signing_enabled": False,
        "signing_required": False,
        "challenge": None,
        "banner": None,
        "raw_preview": "",
        "error": None,
    }

    request = _build_smb1_negotiate_request(dial)
    data, err = _send_recv(host, server_port, request, timeout, connector=connector)

    if err:
        results["error"] = f"negotiate request failed: {err}"
        return results
    if not data:
        results["error"] = "negotiate request failed: no response"
        return results

    parsed = _parse_smb_response(data, dial)
    results.update({k: parsed[k] for k in parsed})
    if parsed.get("error"):
        results["error"] = parsed["error"]
        return results

    results["accessible"] = True
    results["banner"] = _build_banner(parsed)
    return results


def format_smb_report_json(results: Dict[str, Any]) -> str:
    """Format SMB reconnaissance results as JSON."""
    return json.dumps(results, indent=2, default=str)


def format_smb_report_markdown(results: Dict[str, Any]) -> str:
    """Format SMB reconnaissance results as Markdown."""
    lines = ["# ethscan SMB Reconnaissance Report", ""]
    lines.append(f"- **Target:** {results.get('target', '')}")
    lines.append(f"- **Host:** {results.get('host', '')}")
    lines.append(f"- **Port:** {results.get('port', DEFAULT_PORT)}")
    lines.append(f"- **Accessible:** {'Yes' if results.get('accessible') else 'No'}")
    if results.get("error"):
        lines.append(f"- **Error:** {results.get('error')}")
    lines.append("")

    if results.get("accessible"):
        lines.append("## Negotiation")
        lines.append(f"- **Protocol:** {results.get('protocol') or 'unknown'}")
        lines.append(f"- **Dialect:** {results.get('dialect') or 'n/a'}")
        lines.append(f"- **Dialect Index:** {results.get('dialect_index')}")
        lines.append(f"- **Security Mode:** 0x{results.get('security_mode', 0):02x}")
        flags = results.get("security_flags") or []
        lines.append(f"- **Security Flags:** {', '.join(flags) if flags else 'none'}")
        lines.append(f"- **User Security:** {'Yes' if results.get('user_security') else 'No'}")
        lines.append(f"- **Challenge/Response:** {'Yes' if results.get('challenge_response') else 'No'}")
        lines.append(f"- **Signing Required:** {'Yes' if results.get('signing_required') else 'No'}")
        lines.append(f"- **Signing Enabled:** {'Yes' if results.get('signing_enabled') else 'No'}")
        if results.get("challenge"):
            lines.append(f"- **Server Challenge:** {results.get('challenge')}")
        if results.get("banner"):
            lines.append(f"- **Banner:** {results.get('banner')}")
        lines.append("")

    raw = results.get("raw_preview")
    if raw:
        lines.append("## Response Preview")
        lines.append("```")
        lines.append(raw)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def format_smb_report_csv(results: Dict[str, Any]) -> str:
    """Format SMB reconnaissance results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target",
        "host",
        "port",
        "accessible",
        "protocol",
        "dialect",
        "dialect_index",
        "security_mode",
        "security_flags",
        "user_security",
        "challenge_response",
        "requires_signing",
        "signing_enabled",
        "challenge",
        "banner",
        "error",
    ])
    writer.writerow([
        results.get("target", ""),
        results.get("host", ""),
        results.get("port", DEFAULT_PORT),
        "true" if results.get("accessible") else "false",
        results.get("protocol") or "",
        results.get("dialect") or "",
        results.get("dialect_index"),
        f"0x{results.get('security_mode', 0):02x}",
        "|".join(results.get("security_flags", [])),
        "true" if results.get("user_security") else "false",
        "true" if results.get("challenge_response") else "false",
        "true" if results.get("signing_required") else "false",
        "true" if results.get("signing_enabled") else "false",
        results.get("challenge") or "",
        results.get("banner") or "",
        results.get("error") or "",
    ])
    return output.getvalue().rstrip("\r\n")


__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_DIALECTS",
    "SMB_COM_NEGOTIATE",
    "SMB1_MAGIC",
    "SMB2_MAGIC",
    "_build_smb1_negotiate_request",
    "_normalize_target",
    "_parse_smb_response",
    "_send_recv",
    "run_smb",
    "format_smb_report_csv",
    "format_smb_report_json",
    "format_smb_report_markdown",
]
