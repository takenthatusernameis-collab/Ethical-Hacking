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

When invoked with the ``smb2`` option the module additionally performs an
SMB2/SMB3 ``SMB2_NEGOTIATE`` request (``\\xfeSMB``) and decodes the negotiated
dialect (SMB 2.0.2 / 2.1 / 3.0 / 3.0.2 / 3.1.1), the server's security-mode
signing bits, ServerGuid, capabilities, and -- for SMB 3.1.1 -- the negotiate
context list (preauth integrity hash algorithm and encryption ciphers). This is
what reveals the dialect on modern hosts with SMB1 disabled. No authentication
exchange is performed; every network access flows through ``_send_recv``.
"""
from __future__ import annotations

import csv
import io
import json
import os
import socket
import struct
from typing import Any, Optional

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
DEFAULT_DIALECTS: tuple[str, ...] = ("NT LM 0.12", "Samba", "Core", "CorePlus")

# Length of the SMB1 header (signature + command + status + flags + ids).
_SMB1_HEADER_LEN = 32

# ---------------------------------------------------------------------------
# SMB2/SMB3 protocol constants
# ---------------------------------------------------------------------------
#
# The SMB2 dialect identifiers, security-mode bits, capability flags, and
# negotiate-context types are defined by [MS-SMB2]. The values below mirror
# impacket's smb3structs so the byte layout matches real client traffic.

# SMB2 dialects offered to the server (preference order). ``DialectRevision``
# in a NEGOTIATE response is one of these.
SMB2_DIALECT_002 = 0x0202   # SMB 2.0.2
SMB2_DIALECT_21 = 0x0210    # SMB 2.1
SMB2_DIALECT_30 = 0x0300    # SMB 3.0
SMB2_DIALECT_302 = 0x0302   # SMB 3.0.2
SMB2_DIALECT_311 = 0x0311   # SMB 3.1.1
SMB2_DIALECT_WILDCARD = 0x02FF

DEFAULT_SMB2_DIALECTS: tuple[int, ...] = (
    SMB2_DIALECT_002,
    SMB2_DIALECT_21,
    SMB2_DIALECT_30,
    SMB2_DIALECT_302,
    SMB2_DIALECT_311,
)

# SMB2_NEGOTIATE request message's SecurityMode bit fields (MS-SMB2 2.2.3).
SMB2_SIGNING_ENABLED = 0x0001
SMB2_SIGNING_REQUIRED = 0x0002

# Client/server capabilities advertised in an SMB2 NEGOTIATE
# (MS-SMB2 2.2.3 / 2.2.5).
SMB2_CAP_DFS = 0x00000001
SMB2_CAP_LEASING = 0x00000002
SMB2_CAP_LARGE_MTU = 0x00000004
SMB2_CAP_MULTI_CHANNEL = 0x00000008
SMB2_CAP_PERSISTENT_HANDLES = 0x00000010
SMB2_CAP_DIRECTORY_LEASING = 0x00000020
SMB2_CAP_ENCRYPTION = 0x00000040

# SMB2 negotiate-context types (MS-SMB2 2.2.3.1).
SMB2_PREAUTH_INTEGRITY = 0x0001
SMB2_ENCRYPTION_CAP = 0x0002

# Preauth integrity hash algorithms (MS-SMB2 2.2.3.3.1).
SMB2_HASH_SHA512 = 0x0001
SMB2_HASH_SHA256 = 0x0002  # reserved, included for completeness

# Encryption ciphers (MS-SMB2 2.2.3.2.2).
SMB2_CIPHER_AES128_CCM = 0x0001
SMB2_CIPHER_AES128_GCM = 0x0002

# Length of the SMB2 header (the fixed 64-byte envelope).
_SMB2_HEADER_LEN = 64

_SMB2_DIALECT_NAMES: dict[int, str] = {
    SMB2_DIALECT_002: "SMB 2.0.2",
    SMB2_DIALECT_21: "SMB 2.1",
    SMB2_DIALECT_30: "SMB 3.0",
    SMB2_DIALECT_302: "SMB 3.0.2",
    SMB2_DIALECT_311: "SMB 3.1.1",
    SMB2_DIALECT_WILDCARD: "SMB 2.x (wildcard)",
}

_SMB2_CAPABILITY_FLAGS: list[tuple[int, str]] = [
    (SMB2_CAP_DFS, "dfs"),
    (SMB2_CAP_LEASING, "leasing"),
    (SMB2_CAP_LARGE_MTU, "large_mtu"),
    (SMB2_CAP_MULTI_CHANNEL, "multi_channel"),
    (SMB2_CAP_PERSISTENT_HANDLES, "persistent_handles"),
    (SMB2_CAP_DIRECTORY_LEASING, "directory_leasing"),
    (SMB2_CAP_ENCRYPTION, "encryption"),
]

_SMB2_NEGOTIATE_CONTEXT_NAMES: dict[int, str] = {
    SMB2_PREAUTH_INTEGRITY: "preauth_integrity",
    SMB2_ENCRYPTION_CAP: "encryption",
}

_SMB2_HASH_ALGORITHM_NAMES: dict[int, str] = {
    SMB2_HASH_SHA512: "SHA-512",
    SMB2_HASH_SHA256: "SHA-256",
}

_SMB2_CIPHER_NAMES: dict[int, str] = {
    SMB2_CIPHER_AES128_CCM: "AES-128-CCM",
    SMB2_CIPHER_AES128_GCM: "AES-128-GCM",
}


def _normalize_target(target: str) -> tuple[str, int]:
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
) -> tuple[Optional[bytes], Optional[str]]:
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
    dialects: tuple[str, ...] = DEFAULT_DIALECTS,
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
    dialects: tuple[str, ...] = DEFAULT_DIALECTS,
) -> dict[str, Any]:
    """Parse an SMB response, returning negotiated dialect/security info.

    Handles a well-formed SMB1 ``SMB_COM_NEGOTIATE`` response. A non-SMB or
    truncated response is reported via the ``error`` field instead of raising.
    """
    result: dict[str, Any] = {
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
    flags: list[str] = []
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


def _build_banner(parsed: dict[str, Any]) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# SMB2/SMB3 negotiate probe (MS-SMB2 2.2.3 / 2.2.5)
# ---------------------------------------------------------------------------


def _build_smb2_preauth_integrity_context(salt: bytes) -> bytes:
    """Build an SMB2_PREAUTH_INTEGRITY_CAPABILITIES negotiate context.

    Required by [MS-SMB2] whenever the client offers dialect 0x0311 in its
    dialect list. The context advertises the hash algorithm(s) and salt the
    client will use for the preauthentication integrity hash; for a stateless
    recon probe the salt is never consumed, so any non-empty value is fine.
    """
    data = bytearray()
    data += struct.pack("<H", 1)                       # HashAlgorithmCount
    data += struct.pack("<H", len(salt))               # SaltLength
    data += struct.pack("<H", SMB2_HASH_SHA512)        # HashAlgorithms[0]
    data += salt
    body = bytearray()
    body += struct.pack("<H", SMB2_PREAUTH_INTEGRITY)   # ContextType
    body += struct.pack("<H", len(data))               # DataLength
    body += b"\x00" * 4                                 # Reserved
    body += data
    return bytes(body)


def _build_smb2_negotiate_request(
    dialects: tuple[int, ...] = DEFAULT_SMB2_DIALECTS,
    security_mode: int = SMB2_SIGNING_ENABLED,
    capabilities: int = 0,
    client_guid: bytes = b"\x00" * 16,
    preauth_salt: Optional[bytes] = None,
) -> bytes:
    """Build a raw SMB2 ``SMB2_NEGOTIATE`` request.

    Layout (all little-endian):
      * 64-byte SMB2 header: protocol id ``\\xfeSMB``, StructureSize 64,
        Command ``SMB2_NEGOTIATE`` (0), zeroed control fields.
      * 36-byte ``SMB2_NEGOTIATE_REQUEST`` fixed body: StructureSize (36),
        DialectCount, SecurityMode, Reserved, Capabilities, ClientGuid, and
        the NegotiateContextOffset/Count/Reserved2 triple (8 bytes).
      * Dialect list (``DialectCount * 2`` bytes).
      * For SMB 3.1.1, an 8-byte aligned ``SMB2_PREAUTH_INTEGRITY``
        negotiate context.
    """
    dialect_list = list(dialects)
    dialect_count = len(dialect_list)
    needs_preauth = SMB2_DIALECT_311 in dialect_list

    buf = bytearray()
    # --- SMB2 header (64 bytes) ---
    buf += SMB2_MAGIC
    buf += struct.pack("<H", 64)                       # StructureSize
    buf += struct.pack("<H", 0)                        # CreditCharge (negotiate: 0)
    buf += b"\x00\x00\x00\x00"                         # Status / ChannelSequence
    buf += struct.pack("<H", 0)                        # Command (SMB2_NEGOTIATE)
    buf += struct.pack("<H", 0)                        # CreditRequest
    buf += struct.pack("<I", 0)                        # Flags
    buf += struct.pack("<I", 0)                        # NextCommand
    buf += struct.pack("<Q", 0)                        # MessageId
    buf += b"\x00" * 4                                 # ProcessId / Reserved
    buf += b"\x00" * 4                                 # TreeId
    buf += b"\x00" * 8                                 # SessionId
    buf += b"\x00" * 16                                # Signature
    assert len(buf) == _SMB2_HEADER_LEN

    # --- SMB2_NEGOTIATE_REQUEST body ---
    body = bytearray()
    body += struct.pack("<H", 36)                     # StructureSize
    body += struct.pack("<H", dialect_count)          # DialectCount
    body += struct.pack("<H", security_mode)          # SecurityMode
    body += b"\x00\x00"                               # Reserved
    body += struct.pack("<I", capabilities)           # Capabilities
    body += client_guid                               # ClientGuid (16)
    ctx_field_off = len(body)                          # body offset 28
    body += b"\x00" * 8                                # NegotiateContextOffset/Count/Reserved2
    body += b"".join(struct.pack("<H", d) for d in dialect_list)

    dialects_end = len(buf) + len(body)
    pad = (8 - (dialects_end % 8)) % 8
    body += b"\x00" * pad

    if needs_preauth:
        salt = preauth_salt if preauth_salt is not None else os.urandom(32)
        context_data = _build_smb2_preauth_integrity_context(salt)
        context_offset = dialects_end + pad            # from SMB2 header start
        body[ctx_field_off:ctx_field_off + 4] = struct.pack("<I", context_offset)
        body[ctx_field_off + 4:ctx_field_off + 6] = struct.pack("<H", 1)
        body[ctx_field_off + 6:ctx_field_off + 8] = b"\x00\x00"
        body += context_data
        body += b"\x00" * ((8 - (len(context_data) % 8)) % 8)

    buf += body
    return bytes(buf)


def _parse_smb2_negotiate_contexts(data: bytes, ctx_offset: int) -> list[dict[str, Any]]:
    """Parse the SMB2 negotiate-context list referenced by ``ctx_offset``.

    ``ctx_offset`` is measured from the start of the SMB2 header (i.e. byte 0
    of ``data``). Each context is 8-byte aligned. Unknown context types are
    preserved with their raw hex so nothing is silently dropped.
    """
    contexts: list[dict[str, Any]] = []
    pos = ctx_offset
    while pos + 8 <= len(data):
        ctx_type = struct.unpack("<H", data[pos:pos + 2])[0]
        data_len = struct.unpack("<H", data[pos + 2:pos + 4])[0]
        ctx_data = data[pos + 8:pos + 8 + data_len]
        entry: dict[str, Any] = {
            "type": ctx_type,
            "type_name": _SMB2_NEGOTIATE_CONTEXT_NAMES.get(ctx_type),
            "detail": None,
        }
        if ctx_type == SMB2_PREAUTH_INTEGRITY:
            entry["detail"] = _parse_preauth_integrity_context(ctx_data)
        elif ctx_type == SMB2_ENCRYPTION_CAP:
            entry["detail"] = _parse_encryption_capabilities(ctx_data)
        contexts.append(entry)
        pos += 8 + data_len
        pos += (8 - (data_len % 8)) % 8
    return contexts


def _parse_preauth_integrity_context(ctx_data: bytes) -> dict[str, Any]:
    """Decode an SMB2_PREAUTH_INTEGRITY_CAPABILITIES sub-structure."""
    if len(ctx_data) < 4:
        return {}
    hash_count = struct.unpack("<H", ctx_data[0:2])[0]
    salt_length = struct.unpack("<H", ctx_data[2:4])[0]
    algos: list[Any] = []
    off = 4
    available = (len(ctx_data) - 4) // 2
    for _ in range(min(hash_count, available)):
        algos.append(_SMB2_HASH_ALGORITHM_NAMES.get(struct.unpack("<H", ctx_data[off:off + 2])[0]))
        off += 2
    return {"hash_algorithms": algos, "salt_length": salt_length}


def _parse_encryption_capabilities(ctx_data: bytes) -> dict[str, Any]:
    """Decode an SMB2_ENCRYPTION_CAPABILITIES sub-structure."""
    if len(ctx_data) < 2:
        return {}
    cipher_count = struct.unpack("<H", ctx_data[0:2])[0]
    ciphers: list[Any] = []
    off = 2
    available = (len(ctx_data) - 2) // 2
    for _ in range(min(cipher_count, available)):
        ciphers.append(_SMB2_CIPHER_NAMES.get(struct.unpack("<H", ctx_data[off:off + 2])[0]))
        off += 2
    return {"ciphers": ciphers}


def _decode_smb2_capabilities(capabilities: int) -> list[str]:
    return [name for bit, name in _SMB2_CAPABILITY_FLAGS if capabilities & bit]


def _parse_smb2_response(
    data: Optional[bytes],
    dialects: tuple[int, ...] = DEFAULT_SMB2_DIALECTS,
) -> dict[str, Any]:
    """Parse an SMB2 ``SMB2_NEGOTIATE`` response.

    Returns negotiated dialect/security info. A non-SMB2 or truncated response
    is reported via the ``error`` field instead of raising.
    """
    result: dict[str, Any] = {
        "protocol": None,
        "command": None,
        "status": None,
        "structure_size": None,
        "security_mode": 0,
        "signing_enabled": False,
        "signing_required": False,
        "dialect_revision": None,
        "dialect": None,
        "server_guid": None,
        "capabilities": 0,
        "capability_flags": [],
        "max_transact_size": None,
        "max_read_size": None,
        "max_write_size": None,
        "negotiate_context_count": 0,
        "negotiate_contexts": [],
        "raw_preview": "",
        "error": None,
    }

    if not data:
        result["error"] = "no response received"
        return result

    result["raw_preview"] = data[:48].hex()

    if len(data) < _SMB2_HEADER_LEN + 64:
        result["error"] = "response too short to be an SMB2 message"
        return result

    signature = data[0:4]
    if signature == SMB1_MAGIC:
        result["error"] = "SMB1 response received for an SMB2 negotiate (not decoded)"
        return result
    if signature != SMB2_MAGIC:
        result["error"] = "response is not an SMB2 message"
        return result

    result["protocol"] = "SMB2"
    result["command"] = struct.unpack("<H", data[12:14])[0]
    result["status"] = struct.unpack("<I", data[8:12])[0]

    body = data[_SMB2_HEADER_LEN:]
    structure_size = struct.unpack("<H", body[0:2])[0]
    result["structure_size"] = structure_size
    if structure_size != 65:
        result["error"] = f"unexpected SMB2 negotiate structure size {structure_size}"
        return result

    security_mode = struct.unpack("<H", body[2:4])[0]
    result["security_mode"] = security_mode
    result["signing_enabled"] = bool(security_mode & SMB2_SIGNING_ENABLED)
    result["signing_required"] = bool(security_mode & SMB2_SIGNING_REQUIRED)

    dialect_revision = struct.unpack("<H", body[4:6])[0]
    result["dialect_revision"] = dialect_revision
    result["dialect"] = _SMB2_DIALECT_NAMES.get(dialect_revision, f"unknown (0x{dialect_revision:04x})")

    result["server_guid"] = body[8:24].hex()

    capabilities = struct.unpack("<I", body[24:28])[0]
    result["capabilities"] = capabilities
    result["capability_flags"] = _decode_smb2_capabilities(capabilities)

    result["max_transact_size"] = struct.unpack("<I", body[28:32])[0]
    result["max_read_size"] = struct.unpack("<I", body[32:36])[0]
    result["max_write_size"] = struct.unpack("<I", body[36:40])[0]

    neg_ctx_count = struct.unpack("<H", body[6:8])[0]
    result["negotiate_context_count"] = neg_ctx_count
    neg_ctx_off = struct.unpack("<I", body[60:64])[0]
    if neg_ctx_off and neg_ctx_count and neg_ctx_off + 8 <= len(data):
        result["negotiate_contexts"] = _parse_smb2_negotiate_contexts(data, neg_ctx_off)

    return result


def _build_smb2_banner(parsed: dict[str, Any]) -> Optional[str]:
    """Build a short human-readable banner from a parsed SMB2 response."""
    if parsed.get("protocol") != "SMB2":
        return None
    dialect = parsed.get("dialect") or "unknown"
    parts = [f"dialect={dialect}"]
    if parsed.get("signing_required"):
        signing = "required"
    elif parsed.get("signing_enabled"):
        signing = "enabled"
    else:
        signing = "disabled"
    parts.append(f"signing={signing}")
    caps = parsed.get("capability_flags") or []
    if caps:
        parts.append("caps=" + ",".join(caps))
    if parsed.get("server_guid"):
        parts.append("guid present")
    return "SMB2 negotiate OK; " + ", ".join(parts)


def run_smb2(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    dialects: tuple[int, ...] = DEFAULT_SMB2_DIALECTS,
    connector=None,
) -> dict[str, Any]:
    """Run an SMB2/SMB3 ``SMB2_NEGOTIATE`` probe against ``target``.

    Performs a single dialect-negotiation round and decodes the negotiated
    SMB dialect/version plus security capabilities. ``target`` is a host,
    ``host:port``, or ``smb://host:port``; ``port`` overrides the parsed port
    (default 445); ``connector`` injects a fake transport for testing.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port

    results: dict[str, Any] = {
        "target": target,
        "host": host,
        "port": server_port,
        "accessible": False,
        "protocol": "SMB2",
        "dialect_revision": None,
        "dialect": None,
        "security_mode": 0,
        "signing_enabled": False,
        "signing_required": False,
        "server_guid": None,
        "capabilities": 0,
        "capability_flags": [],
        "max_transact_size": None,
        "max_read_size": None,
        "max_write_size": None,
        "negotiate_context_count": 0,
        "negotiate_contexts": [],
        "banner": None,
        "raw_preview": "",
        "notes": [],
        "error": None,
    }

    request = _build_smb2_negotiate_request(dialects=tuple(dialects))
    data, err = _send_recv(host, server_port, request, timeout, connector=connector)

    if err:
        results["error"] = f"SMB2 negotiate request failed: {err}"
        return results
    if not data:
        results["error"] = "SMB2 negotiate request failed: no response"
        return results

    parsed = _parse_smb2_response(data, dialects=tuple(dialects))
    results.update({k: parsed[k] for k in parsed})
    if parsed.get("error"):
        results["error"] = parsed["error"]
        return results

    results["accessible"] = True
    results["banner"] = _build_smb2_banner(parsed)

    revision = parsed.get("dialect_revision")
    if revision == SMB2_DIALECT_002:
        results["notes"].append("dialect SMB 2.0.2 is the original SMB2 specification")
    if parsed.get("signing_required"):
        results["notes"].append("message signing is required by the server")
    elif parsed.get("signing_enabled"):
        results["notes"].append("message signing is supported but not enforced")
    return results


def run_smb(
    target: str,
    port: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    dialects: Optional[tuple[str, ...]] = None,
    smb2: bool = False,
    smb2_dialects: Optional[tuple[int, ...]] = None,
    connector=None,
) -> dict[str, Any]:
    """Run SMB reconnaissance probes against ``target``.

    Always performs the SMB1 ``SMB_COM_NEGOTIATE`` probe described above. When
    ``smb2`` is true an additional SMB2/SMB3 ``SMB2_NEGOTIATE`` probe is run and
    its results are attached under the ``smb2`` key (this is what reaches modern
    hosts with SMB1 disabled). ``target`` is a host, ``host:port``, or
    ``smb://host:port``; ``port`` overrides the parsed port (445); ``timeout``
    bounds each TCP exchange; ``connector`` injects a fake transport for
    testing.
    """
    host, parsed_port = _normalize_target(target)
    server_port = port if port is not None else parsed_port
    dial = tuple(dialects) if dialects else DEFAULT_DIALECTS

    results: dict[str, Any] = {
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
    elif not data:
        results["error"] = "negotiate request failed: no response"
    else:
        parsed = _parse_smb_response(data, dial)
        results.update({k: parsed[k] for k in parsed})
        if parsed.get("error"):
            results["error"] = parsed["error"]
        else:
            results["accessible"] = True
            results["banner"] = _build_banner(parsed)

    if smb2:
        smb2_dial = tuple(smb2_dialects) if smb2_dialects else DEFAULT_SMB2_DIALECTS
        results["smb2"] = run_smb2(
            target,
            port=server_port,
            timeout=timeout,
            dialects=smb2_dial,
            connector=connector,
        )

    return results


def format_smb_report_json(results: dict[str, Any]) -> str:
    """Format SMB reconnaissance results as JSON."""
    return json.dumps(results, indent=2, default=str)


def format_smb_report_markdown(results: dict[str, Any]) -> str:
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

    smb2_results = results.get("smb2")
    if smb2_results:
        lines.append("## SMB2 Negotiation")
        lines.append(f"- **Accessible:** {'Yes' if smb2_results.get('accessible') else 'No'}")
        if smb2_results.get("error"):
            lines.append(f"- **Error:** {smb2_results.get('error')}")
        if smb2_results.get("accessible"):
            lines.append(f"- **Dialect:** {smb2_results.get('dialect') or 'n/a'}")
            lines.append(f"- **Dialect Revision:** {smb2_results.get('dialect_revision')}")
            lines.append(f"- **Security Mode:** 0x{smb2_results.get('security_mode', 0):02x}")
            lines.append(f"- **Signing Required:** {'Yes' if smb2_results.get('signing_required') else 'No'}")
            lines.append(f"- **Signing Enabled:** {'Yes' if smb2_results.get('signing_enabled') else 'No'}")
            if smb2_results.get("server_guid"):
                lines.append(f"- **Server GUID:** {smb2_results.get('server_guid')}")
            caps = smb2_results.get("capability_flags") or []
            lines.append(f"- **Capabilities:** {', '.join(caps) if caps else 'none'}")
            if smb2_results.get("negotiate_context_count"):
                lines.append(f"- **Negotiate Contexts:** {smb2_results.get('negotiate_context_count')}")
                for ctx in smb2_results.get("negotiate_contexts") or []:
                    name = ctx.get("type_name") or f"0x{ctx.get('type', 0):04x}"
                    detail = ctx.get("detail")
                    if detail:
                        lines.append(f"  - **{name}:** {detail}")
                    else:
                        lines.append(f"  - **{name}**")
            if smb2_results.get("banner"):
                lines.append(f"- **Banner:** {smb2_results.get('banner')}")
            for note in smb2_results.get("notes") or []:
                lines.append(f"- **Note:** {note}")
        lines.append("")

    raw = results.get("raw_preview")
    if raw:
        lines.append("## Response Preview")
        lines.append("```")
        lines.append(raw)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def format_smb_report_csv(results: dict[str, Any]) -> str:
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
    "DEFAULT_DIALECTS",
    "DEFAULT_PORT",
    "DEFAULT_SMB2_DIALECTS",
    "DEFAULT_TIMEOUT",
    "SMB1_MAGIC",
    "SMB2_CIPHER_AES128_CCM",
    "SMB2_CIPHER_AES128_GCM",
    "SMB2_DIALECT_002",
    "SMB2_DIALECT_21",
    "SMB2_DIALECT_30",
    "SMB2_DIALECT_302",
    "SMB2_DIALECT_311",
    "SMB2_ENCRYPTION_CAP",
    "SMB2_HASH_SHA512",
    "SMB2_MAGIC",
    "SMB2_PREAUTH_INTEGRITY",
    "SMB2_SIGNING_ENABLED",
    "SMB2_SIGNING_REQUIRED",
    "SMB_COM_NEGOTIATE",
    "_build_smb1_negotiate_request",
    "_build_smb2_banner",
    "_build_smb2_negotiate_request",
    "_build_smb2_preauth_integrity_context",
    "_normalize_target",
    "_parse_smb2_negotiate_contexts",
    "_parse_smb2_response",
    "_parse_smb_response",
    "_send_recv",
    "format_smb_report_csv",
    "format_smb_report_json",
    "format_smb_report_markdown",
    "run_smb",
    "run_smb2",
]
