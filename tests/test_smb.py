"""Tests for the ethscan smb module."""

import csv
import io
import json
import socket
import struct
from unittest.mock import patch

import pytest

from ethscan.smb import (
    DEFAULT_DIALECTS,
    DEFAULT_PORT,
    DEFAULT_SMB2_DIALECTS,
    SMB1_MAGIC,
    SMB2_CIPHER_AES128_CCM,
    SMB2_CIPHER_AES128_GCM,
    SMB2_DIALECT_002,
    SMB2_DIALECT_21,
    SMB2_DIALECT_30,
    SMB2_DIALECT_302,
    SMB2_DIALECT_311,
    SMB2_ENCRYPTION_CAP,
    SMB2_HASH_SHA512,
    SMB2_MAGIC,
    SMB2_PREAUTH_INTEGRITY,
    SMB2_SIGNING_ENABLED,
    SMB2_SIGNING_REQUIRED,
    SMB_COM_NEGOTIATE,
    _build_banner,
    _build_smb1_negotiate_request,
    _build_smb2_banner,
    _build_smb2_negotiate_request,
    _build_smb2_preauth_integrity_context,
    _decode_smb2_capabilities,
    _normalize_target,
    _parse_encryption_capabilities,
    _parse_preauth_integrity_context,
    _parse_smb2_negotiate_contexts,
    _parse_smb2_response,
    _parse_smb_response,
    _send_recv,
    format_smb_report_csv,
    format_smb_report_json,
    format_smb_report_markdown,
    run_smb,
    run_smb2,
)

# ---------------------------------------------------------------------------
# Helpers to build well-formed SMB1 negotiate responses
# ---------------------------------------------------------------------------


def _build_smb1_response(
    dialect_index: int = 0,
    security_mode: int = 0x01,
    data: bytes = b"",
) -> bytes:
    """Build a raw SMB1 SMB_COM_NEGOTIATE response message."""
    header = SMB1_MAGIC + bytes([SMB_COM_NEGOTIATE]) + b"\x00" * 27  # 32 bytes
    # Parameter words: DialectIndex(2) + SecurityMode(1) + 31 bytes of zeros
    # => 34 bytes = 17 words (WordCount == 0x11).
    params = struct.pack("<H", dialect_index) + bytes([security_mode]) + b"\x00" * 31
    return header + bytes([0x11]) + params + struct.pack("<H", len(data)) + data


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT == 445


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("192.168.1.100:139")
    assert host == "192.168.1.100"
    assert port == 139


def test_normalize_target_smb_url_default_port() -> None:
    host, port = _normalize_target("smb://192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT


def test_normalize_target_smb_url_with_port() -> None:
    host, port = _normalize_target("smb://192.168.1.100:139")
    assert host == "192.168.1.100"
    assert port == 139


def test_normalize_target_ipv6_with_port() -> None:
    host, port = _normalize_target("[fd00::1]:445")
    assert host == "fd00::1"
    assert port == 445


def test_normalize_target_ipv6_no_port() -> None:
    host, port = _normalize_target("[fd00::1]")
    assert host == "fd00::1"
    assert port == DEFAULT_PORT


def test_normalize_target_ipv6_url_with_port() -> None:
    host, port = _normalize_target("smb://[fd00::1]:445")
    assert host == "fd00::1"
    assert port == 445


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


# ---------------------------------------------------------------------------
# _build_smb1_negotiate_request
# ---------------------------------------------------------------------------


def test_build_request_structure() -> None:
    request = _build_smb1_negotiate_request()
    assert request[:4] == SMB1_MAGIC
    assert request[4] == SMB_COM_NEGOTIATE  # command
    assert request[32] == 0  # WordCount is 0 for a negotiate request

    # ByteCount (2 bytes, little-endian) starts at offset 33.
    bytecount = struct.unpack("<H", request[33:35])[0]
    assert bytecount == len(request) - 35
    assert request[35:35 + bytecount] == request[35:]


def test_build_request_contains_dialects() -> None:
    request = _build_smb1_negotiate_request(DEFAULT_DIALECTS)
    blob = request[35:]
    # Each dialect is prefixed with 0x02 and null-terminated.
    assert blob.startswith(b"\x02NT LM 0.12\x00")
    assert b"\x02Samba\x00" in blob
    assert b"\x02Core\x00" in blob
    assert b"\x02CorePlus\x00" in blob


def test_build_request_custom_dialects() -> None:
    request = _build_smb1_negotiate_request(("NT LM 0.12", "Samba"))
    blob = request[35:]
    assert blob == b"\x02NT LM 0.12\x00\x02Samba\x00"
    assert struct.unpack("<H", request[33:35])[0] == len(blob)


# ---------------------------------------------------------------------------
# _parse_smb_response
# ---------------------------------------------------------------------------


def test_parse_smb_response_full() -> None:
    parsed = _parse_smb_response(_build_smb1_response(0, 0x05, b"\x00" * 8))
    assert parsed["protocol"] == "SMB1"
    assert parsed["command"] == SMB_COM_NEGOTIATE
    assert parsed["dialect_index"] == 0
    assert parsed["dialect"] == "NT LM 0.12"
    assert parsed["security_mode"] == 0x05
    assert parsed["user_security"] is True
    assert parsed["signing_enabled"] is True
    assert parsed["signing_required"] is False
    assert parsed["challenge_response"] is False
    assert parsed["security_flags"] == ["user_security", "signing_enabled"]
    assert parsed["challenge"] == "0000000000000000"
    assert parsed["error"] is None


def test_parse_smb_response_all_security_flags() -> None:
    # 0x0f = user(0x01) + challenge-response(0x02) + signing-enabled(0x04) + signing-required(0x08)
    parsed = _parse_smb_response(_build_smb1_response(0, 0x0F, b"\x00" * 8))
    assert parsed["user_security"] is True
    assert parsed["challenge_response"] is True
    assert parsed["signing_enabled"] is True
    assert parsed["signing_required"] is True
    assert parsed["security_flags"] == [
        "user_security",
        "challenge_response",
        "signing_enabled",
        "signing_required",
    ]


def test_parse_smb_response_dialect_mapping() -> None:
    parsed = _parse_smb_response(_build_smb1_response(1, 0x01, b"\x00" * 8))
    assert parsed["dialect"] == "Samba"
    parsed = _parse_smb_response(_build_smb1_response(2, 0x01, b"\x00" * 8))
    assert parsed["dialect"] == "Core"


def test_parse_smb_response_no_common_dialect() -> None:
    parsed = _parse_smb_response(_build_smb1_response(0xFFFF, 0x01, b"\x00" * 8))
    assert parsed["dialect"] == "(no common dialect)"
    assert parsed["dialect_index"] == 0xFFFF
    assert parsed["error"] is None


def test_parse_smb_response_unknown_dialect_index() -> None:
    parsed = _parse_smb_response(_build_smb1_response(9, 0x01, b"\x00" * 8))
    assert parsed["dialect_index"] == 9
    assert parsed["dialect"] == "unknown (index 9)"


def test_parse_smb_response_extracts_challenge() -> None:
    parsed = _parse_smb_response(_build_smb1_response(0, 0x01, b"\xaa" * 8))
    assert parsed["challenge"] == "aa" * 8


def test_parse_smb_response_challenge_after_ntlm_token() -> None:
    # Realistic extended-security layout: ChallengeString (8 bytes) first, then
    # the NTLMSSP negotiate token. The challenge must be the ChallengeString.
    data_section = b"\x11" * 8 + b"NTLMSSP\x00" + b"\x00" * 16
    parsed = _parse_smb_response(_build_smb1_response(0, 0x03, data_section))
    assert parsed["challenge"] == "11" * 8


def test_parse_smb_response_smb2_magic_is_tolerated() -> None:
    parsed = _parse_smb_response(SMB2_MAGIC + b"\x00" * 40)
    assert parsed["protocol"] == "SMB2"
    assert parsed["error"] is not None


def test_parse_smb_response_non_smb_magic() -> None:
    parsed = _parse_smb_response(b"HTTP/1.1 200 OK\r\n" + b"x" * 40)
    assert parsed["protocol"] is None
    assert parsed["error"] == "response is not an SMB message"


def test_parse_smb_response_empty() -> None:
    parsed = _parse_smb_response(b"")
    assert parsed["error"] == "no response received"
    assert parsed["protocol"] is None


def test_parse_smb_response_too_short() -> None:
    parsed = _parse_smb_response(b"\xffSMB\x72\x00\x00")
    assert parsed["error"] == "response too short to be an SMB1 message"


def test_parse_smb_response_truncated_parameters() -> None:
    # Header + WordCount says 17 words but fewer bytes follow.
    payload = SMB1_MAGIC + bytes([SMB_COM_NEGOTIATE]) + b"\x00" * 27
    payload += bytes([0x11]) + b"\x00" * 4  # not enough parameter words
    parsed = _parse_smb_response(payload)
    assert parsed["error"] == "truncated negotiate response parameters"


# ---------------------------------------------------------------------------
# _send_recv
# ---------------------------------------------------------------------------


def test_send_recv_with_connector_returns_data() -> None:
    def connector(host, port, request, timeout):
        return b"response", None

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0, connector=connector)
    assert data == b"response"
    assert err is None


def test_send_recv_with_connector_returns_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0, connector=connector)
    assert data is None
    assert err == "timeout"


def test_send_recv_connector_receives_arguments() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured.update(host=host, port=port, request=request, timeout=timeout)
        return None, "timeout"

    _send_recv("192.168.1.1", 445, b"req-bytes", 2.5, connector=connector)
    assert captured == {
        "host": "192.168.1.1",
        "port": 445,
        "request": b"req-bytes",
        "timeout": 2.5,
    }


def test_send_recv_real_socket_success() -> None:
    """The non-connector path: socket.socket, settimeout, connect, sendall, recv."""

    class FakeSocket:
        def __init__(self, *args, **kwargs):
            self.args = args

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect(self, addr):
            self.addr = addr

        def sendall(self, data):
            self.sent = data

        def recv(self, n):
            return b"pong"

        def close(self):
            self.closed = True

    with patch("ethscan.smb.socket.socket", FakeSocket):
        data, err = _send_recv("10.0.0.1", 445, b"ping", 1.0)
    assert data == b"pong"
    assert err is None


def test_send_recv_real_socket_timeout() -> None:
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, addr):
            pass

        def sendall(self, data):
            pass

        def recv(self, n):
            raise socket.timeout()

        def close(self):
            pass

    with patch("ethscan.smb.socket.socket", FakeSocket):
        data, err = _send_recv("10.0.0.1", 445, b"ping", 0.5)
    assert data is None
    assert err == "timeout"


def test_send_recv_real_socket_oserror() -> None:
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, addr):
            raise ConnectionRefusedError("[Errno 111] Connection refused")

        def sendall(self, data):
            pass

        def recv(self, n):
            return b""

        def close(self):
            pass

    with patch("ethscan.smb.socket.socket", FakeSocket):
        data, err = _send_recv("10.0.0.1", 445, b"ping", 1.0)
    assert data is None
    assert "Connection refused" in err


def test_send_recv_real_socket_close_error_swallowed() -> None:
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, addr):
            pass

        def sendall(self, data):
            pass

        def recv(self, n):
            return b"data"

        def close(self):
            raise OSError("close failed")

    with patch("ethscan.smb.socket.socket", FakeSocket):
        data, err = _send_recv("10.0.0.1", 445, b"ping", 1.0)
    assert data == b"data"
    assert err is None


# ---------------------------------------------------------------------------
# _build_banner
# ---------------------------------------------------------------------------


def test_build_banner_non_smb1_returns_none() -> None:
    assert _build_banner({"protocol": "SMB2"}) is None


def test_build_banner_signing_enabled() -> None:
    parsed = {
        "protocol": "SMB1",
        "dialect": "NT LM 0.12",
        "security_mode": 0x05,
        "signing_required": False,
        "signing_enabled": True,
        "challenge_response": True,
        "challenge": "0102030405060708",
    }
    banner = _build_banner(parsed)
    assert banner is not None
    assert "signing=enabled" in banner
    assert "auth=challenge-response" in banner
    assert "challenge present" in banner


# ---------------------------------------------------------------------------
# run_smb
# ---------------------------------------------------------------------------


def test_run_smb_accessible_via_connector() -> None:
    def connector(host, port, request, timeout):
        assert request[4] == SMB_COM_NEGOTIATE
        assert request[:4] == SMB1_MAGIC
        # 0x09 = user(0x01) + signing-required(0x08) -> hardened host.
        return _build_smb1_response(0, 0x09, b"\x11" * 8), None

    results = run_smb("smb://192.168.1.100:445", connector=connector)
    assert results["target"] == "smb://192.168.1.100:445"
    assert results["host"] == "192.168.1.100"
    assert results["port"] == 445
    assert results["accessible"] is True
    assert results["protocol"] == "SMB1"
    assert results["dialect"] == "NT LM 0.12"
    assert results["dialect_index"] == 0
    assert results["user_security"] is True
    assert results["signing_required"] is True
    assert results["signing_enabled"] is False
    assert results["challenge"] == "11" * 8
    assert results["error"] is None
    assert results["banner"] is not None
    assert "signing=required" in results["banner"]


def test_run_smb_no_common_dialect_is_accessible() -> None:
    def connector(host, port, request, timeout):
        return _build_smb1_response(0xFFFF, 0x01, b"\x00" * 8), None

    results = run_smb("192.168.1.100", connector=connector)
    assert results["accessible"] is True
    assert results["dialect"] == "(no common dialect)"
    assert results["error"] is None
    assert "no common dialect" in results["banner"]


def test_run_smb_timeout_sets_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_smb("192.168.1.100", timeout=1.0, connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "negotiate request failed: timeout"


def test_run_smb_connection_refused() -> None:
    def connector(host, port, request, timeout):
        return None, "[Errno 111] Connection refused"

    results = run_smb("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "negotiate request failed: [Errno 111] Connection refused"


def test_run_smb_no_response() -> None:
    def connector(host, port, request, timeout):
        return b"", None

    results = run_smb("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "negotiate request failed: no response"


def test_run_smb_non_smb_response() -> None:
    def connector(host, port, request, timeout):
        return b"HTTP/1.1 200 OK\r\n" + b"x" * 40, None

    results = run_smb("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "response is not an SMB message"


def test_run_smb_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["port"] = port
        captured["host"] = host
        return _build_smb1_response(0, 0x01, b"\x00" * 8), None

    results = run_smb("192.0.2.9:445", port=139, connector=connector)
    assert captured["port"] == 139
    assert results["port"] == 139


def test_run_smb_passes_timeout_to_connector() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["timeout"] = timeout
        return _build_smb1_response(0, 0x01, b"\x00" * 8), None

    run_smb("192.168.1.100", timeout=5.0, connector=connector)
    assert captured["timeout"] == 5.0


def test_run_smb_default_dialects_used() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["request"] = request
        return _build_smb1_response(0, 0x01, b"\x00" * 8), None

    run_smb("192.168.1.100", connector=connector)
    request = captured["request"]
    bytecount = struct.unpack("<H", request[33:35])[0]
    assert request[35:35 + bytecount] == (
        b"\x02NT LM 0.12\x00\x02Samba\x00\x02Core\x00\x02CorePlus\x00"
    )


def test_run_smb_custom_dialects() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["request"] = request
        return _build_smb1_response(0, 0x01, b"\x00" * 8), None

    run_smb("192.168.1.100", dialects=("NT LM 0.12", "Samba"), connector=connector)
    bytecount = struct.unpack("<H", captured["request"][33:35])[0]
    assert captured["request"][35:35 + bytecount] == b"\x02NT LM 0.12\x00\x02Samba\x00"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _accessible_results() -> dict:
    # 0x07 = user + challenge-response + signing enabled.
    return {
        "target": "smb://192.168.1.100:445",
        "host": "192.168.1.100",
        "port": 445,
        "accessible": True,
        "protocol": "SMB1",
        "dialect": "NT LM 0.12",
        "dialect_index": 0,
        "security_mode": 0x07,
        "security_flags": ["user_security", "challenge_response", "signing_enabled"],
        "user_security": True,
        "challenge_response": True,
        "signing_enabled": True,
        "signing_required": False,
        "challenge": "aabbccddeeff0011",
        "banner": "SMB1 negotiate OK; dialect=NT LM 0.12, signing=enabled, auth=challenge-response, challenge present",
        "raw_preview": "ff534d42",
        "error": None,
    }


def _inaccessible_results() -> dict:
    return {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 445,
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
        "error": "negotiate request failed: timeout",
    }


def test_format_smb_report_json() -> None:
    parsed = json.loads(format_smb_report_json(_accessible_results()))
    assert parsed["host"] == "192.168.1.100"
    assert parsed["accessible"] is True
    assert parsed["dialect"] == "NT LM 0.12"
    assert parsed["dialect_index"] == 0
    assert parsed["user_security"] is True
    assert parsed["challenge_response"] is True
    assert parsed["signing_enabled"] is True
    assert parsed["signing_required"] is False
    assert parsed["challenge"] == "aabbccddeeff0011"


def test_format_smb_report_json_inaccessible() -> None:
    parsed = json.loads(format_smb_report_json(_inaccessible_results()))
    assert parsed["accessible"] is False
    assert parsed["error"] == "negotiate request failed: timeout"


def test_format_smb_report_markdown_full() -> None:
    output = format_smb_report_markdown(_accessible_results())
    assert "# ethscan SMB Reconnaissance Report" in output
    assert "- **Target:** smb://192.168.1.100:445" in output
    assert "- **Port:** 445" in output
    assert "- **Accessible:** Yes" in output
    assert "## Negotiation" in output
    assert "- **Dialect:** NT LM 0.12" in output
    assert "- **User Security:** Yes" in output
    assert "- **Challenge/Response:** Yes" in output
    assert "- **Signing Required:** No" in output
    assert "- **Signing Enabled:** Yes" in output
    assert "- **Server Challenge:** aabbccddeeff0011" in output
    assert "- **Banner:**" in output


def test_format_smb_report_markdown_inaccessible() -> None:
    output = format_smb_report_markdown(_inaccessible_results())
    assert "- **Accessible:** No" in output
    assert "- **Error:** negotiate request failed: timeout" in output


def test_format_smb_report_csv() -> None:
    output = format_smb_report_csv(_accessible_results())
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == [
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
    ]
    assert rows[1][0] == "smb://192.168.1.100:445"
    assert rows[1][3] == "true"
    assert rows[1][4] == "SMB1"
    assert rows[1][5] == "NT LM 0.12"
    assert rows[1][7] == "0x07"
    assert rows[1][8] == "user_security|challenge_response|signing_enabled"
    assert rows[1][9] == "true"
    assert rows[1][10] == "true"
    assert rows[1][11] == "false"
    assert rows[1][12] == "true"
    assert rows[1][13] == "aabbccddeeff0011"


def test_format_smb_report_csv_inaccessible() -> None:
    output = format_smb_report_csv(_inaccessible_results())
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][3] == "false"
    assert rows[1][-1] == "negotiate request failed: timeout"


# ---------------------------------------------------------------------------
# SMB2/SMB3 negotiate probe helpers
# ---------------------------------------------------------------------------


def _build_smb2_header(command: int = 0) -> bytes:
    """Build a 64-byte SMB2 header (all control fields zeroed)."""
    header = bytearray()
    header += SMB2_MAGIC
    header += struct.pack("<H", 64)      # StructureSize
    header += struct.pack("<H", 0)       # CreditCharge
    header += b"\x00" * 4                # Status
    header += struct.pack("<H", command)  # Command (0 = SMB2_NEGOTIATE)
    header += struct.pack("<H", 0)       # CreditRequest
    header += struct.pack("<I", 0)       # Flags
    header += struct.pack("<I", 0)       # NextCommand
    header += struct.pack("<Q", 0)       # MessageId
    header += b"\x00" * 4                # ProcessId
    header += b"\x00" * 4                # TreeId
    header += b"\x00" * 8                # SessionId
    header += b"\x00" * 16               # Signature
    assert len(header) == 64
    return bytes(header)


def _build_smb2_negotiate_response(
    dialect_revision: int = SMB2_DIALECT_311,
    security_mode: int = SMB2_SIGNING_ENABLED,
    capabilities: int = 0,
    server_guid: bytes = b"\x11" * 16,
    negotiate_context_count: int = 0,
    negotiate_context_offset: int = 0,
) -> bytes:
    """Build a well-formed SMB2 NEGOTIATE response (MS-SMB2 2.2.5)."""
    body = bytearray()
    body += struct.pack("<H", 65)                        # StructureSize
    body += struct.pack("<H", security_mode)             # SecurityMode
    body += struct.pack("<H", dialect_revision)          # DialectRevision
    body += struct.pack("<H", negotiate_context_count)   # NegotiateContextCount
    body += server_guid                                  # ServerGUID (16)
    body += struct.pack("<I", capabilities)              # Capabilities
    body += struct.pack("<I", 1048576)                   # MaxTransactSize
    body += struct.pack("<I", 1048576)                   # MaxReadSize
    body += struct.pack("<I", 1048576)                   # MaxWriteSize
    body += b"\x00" * 8                                  # SystemTime
    body += b"\x00" * 8                                  # ServerStartTime
    body += b"\x00" * 4                                  # Buffer
    body += struct.pack("<I", negotiate_context_offset)  # NegotiateContextOffset
    assert len(body) == 64
    return _build_smb2_header() + bytes(body)


def _build_smb2_preauth_context(salt: bytes = b"\xab" * 32) -> bytes:
    """Build a preauth-integrity negotiate context (8-byte aligned)."""
    data = struct.pack("<H", 1) + struct.pack("<H", len(salt))
    data += struct.pack("<H", SMB2_HASH_SHA512) + salt
    context = struct.pack("<H", SMB2_PREAUTH_INTEGRITY)
    context += struct.pack("<H", len(data)) + b"\x00" * 4 + data
    return context + b"\x00" * ((8 - (len(context) % 8)) % 8)


def _build_smb2_encryption_context() -> bytes:
    """Build an encryption-capabilities negotiate context (8-byte aligned)."""
    data = struct.pack("<H", 2)
    data += struct.pack("<H", SMB2_CIPHER_AES128_CCM)
    data += struct.pack("<H", SMB2_CIPHER_AES128_GCM)
    context = struct.pack("<H", SMB2_ENCRYPTION_CAP)
    context += struct.pack("<H", len(data)) + b"\x00" * 4 + data
    return context + b"\x00" * ((8 - (len(context) % 8)) % 8)


# ---------------------------------------------------------------------------
# _build_smb2_negotiate_request
# ---------------------------------------------------------------------------


def test_build_smb2_request_header_structure() -> None:
    request = _build_smb2_negotiate_request()
    assert request[:4] == SMB2_MAGIC
    assert struct.unpack("<H", request[4:6])[0] == 64   # header StructureSize
    assert struct.unpack("<H", request[12:14])[0] == 0  # SMB2_NEGOTIATE
    assert len(request) >= 100


def test_build_smb2_request_body_defaults() -> None:
    request = _build_smb2_negotiate_request()
    assert struct.unpack("<H", request[64:66])[0] == 36  # body StructureSize
    assert struct.unpack("<H", request[66:68])[0] == len(DEFAULT_SMB2_DIALECTS)
    assert struct.unpack("<H", request[68:70])[0] == SMB2_SIGNING_ENABLED
    assert struct.unpack("<I", request[72:76])[0] == 0
    assert request[76:92] == b"\x00" * 16  # ClientGuid


def test_build_smb2_request_default_dialect_list() -> None:
    request = _build_smb2_negotiate_request()
    dialect_count = struct.unpack("<H", request[66:68])[0]
    assert dialect_count == 5
    dialects = struct.unpack("<5H", request[100:110])
    assert dialects == DEFAULT_SMB2_DIALECTS


def test_build_smb2_request_custom_dialects() -> None:
    request = _build_smb2_negotiate_request(dialects=(SMB2_DIALECT_21,))
    assert struct.unpack("<H", request[66:68])[0] == 1
    assert struct.unpack("<H", request[100:102])[0] == SMB2_DIALECT_21


def test_build_smb2_request_no_preauth_context_without_311() -> None:
    request = _build_smb2_negotiate_request(dialects=(SMB2_DIALECT_21,))
    # No 0x0311 offered -> no negotiate context required.
    assert struct.unpack("<H", request[96:98])[0] == 0  # NegotiateContextCount
    assert struct.unpack("<I", request[92:96])[0] == 0  # NegotiateContextOffset


def test_build_smb2_request_preauth_context_with_311() -> None:
    request = _build_smb2_negotiate_request()
    assert struct.unpack("<H", request[96:98])[0] == 1  # one context
    ctx_offset = struct.unpack("<I", request[92:96])[0]
    assert ctx_offset > 0
    assert ctx_offset % 8 == 0  # contexts are 8-byte aligned
    ctx_type = struct.unpack("<H", request[ctx_offset:ctx_offset + 2])[0]
    assert ctx_type == SMB2_PREAUTH_INTEGRITY
    data_len = struct.unpack("<H", request[ctx_offset + 2:ctx_offset + 4])[0]
    ctx_data = request[ctx_offset + 8:ctx_offset + 8 + data_len]
    assert struct.unpack("<H", ctx_data[0:2])[0] == 1       # HashAlgorithmCount
    assert struct.unpack("<H", ctx_data[2:4])[0] == 32      # SaltLength
    assert struct.unpack("<H", ctx_data[4:6])[0] == SMB2_HASH_SHA512
    assert len(ctx_data) == 6 + 32


def test_build_smb2_request_security_mode_and_capabilities() -> None:
    request = _build_smb2_negotiate_request(
        dialects=(SMB2_DIALECT_21,),
        security_mode=SMB2_SIGNING_ENABLED | SMB2_SIGNING_REQUIRED,
        capabilities=0x00000007,
    )
    assert struct.unpack("<H", request[68:70])[0] == 0x0003
    assert struct.unpack("<I", request[72:76])[0] == 0x00000007


def test_build_smb2_request_custom_client_guid() -> None:
    guid = bytes(range(16))
    request = _build_smb2_negotiate_request(dialects=(SMB2_DIALECT_21,), client_guid=guid)
    assert request[76:92] == guid


def test_build_smb2_request_explicit_preauth_salt() -> None:
    salt = b"\x01" * 16
    request = _build_smb2_negotiate_request(preauth_salt=salt)
    ctx_offset = struct.unpack("<I", request[92:96])[0]
    data_len = struct.unpack("<H", request[ctx_offset + 2:ctx_offset + 4])[0]
    ctx_data = request[ctx_offset + 8:ctx_offset + 8 + data_len]
    assert struct.unpack("<H", ctx_data[2:4])[0] == 16
    assert ctx_data[4 + 2:4 + 2 + 16] == salt


# ---------------------------------------------------------------------------
# _build_smb2_preauth_integrity_context
# ---------------------------------------------------------------------------


def test_build_smb2_preauth_integrity_context_layout() -> None:
    salt = b"\xcd" * 8
    context = _build_smb2_preauth_integrity_context(salt)
    assert struct.unpack("<H", context[0:2])[0] == SMB2_PREAUTH_INTEGRITY
    assert struct.unpack("<H", context[2:4])[0] == 6 + len(salt)
    assert context[4:8] == b"\x00" * 4  # Reserved
    data = context[8:]
    assert struct.unpack("<H", data[0:2])[0] == 1            # HashAlgorithmCount
    assert struct.unpack("<H", data[2:4])[0] == len(salt)    # SaltLength
    assert struct.unpack("<H", data[4:6])[0] == SMB2_HASH_SHA512
    assert data[6:] == salt


# ---------------------------------------------------------------------------
# Context sub-structure parsers
# ---------------------------------------------------------------------------


def test_parse_preauth_integrity_context() -> None:
    salt = b"\x00" * 32
    data = struct.pack("<H", 1) + struct.pack("<H", len(salt))
    data += struct.pack("<H", SMB2_HASH_SHA512) + salt
    parsed = _parse_preauth_integrity_context(data)
    assert parsed == {"hash_algorithms": ["SHA-512"], "salt_length": 32}


def test_parse_preauth_integrity_context_multiple_algorithms() -> None:
    data = struct.pack("<H", 2) + struct.pack("<H", 0)
    data += struct.pack("<H", SMB2_HASH_SHA512)
    data += struct.pack("<H", 0x0002)
    parsed = _parse_preauth_integrity_context(data)
    assert parsed["hash_algorithms"] == ["SHA-512", "SHA-256"]


def test_parse_preauth_integrity_context_short() -> None:
    assert _parse_preauth_integrity_context(b"\x00\x00") == {}


def test_parse_encryption_capabilities() -> None:
    data = struct.pack("<H", 2)
    data += struct.pack("<H", SMB2_CIPHER_AES128_CCM)
    data += struct.pack("<H", SMB2_CIPHER_AES128_GCM)
    parsed = _parse_encryption_capabilities(data)
    assert parsed == {"ciphers": ["AES-128-CCM", "AES-128-GCM"]}


def test_parse_encryption_capabilities_short() -> None:
    assert _parse_encryption_capabilities(b"\x00") == {}


def test_parse_smb2_negotiate_contexts() -> None:
    preauth = _build_smb2_preauth_context()
    encryption = _build_smb2_encryption_context()
    blob = preauth + encryption
    contexts = _parse_smb2_negotiate_contexts(blob, 0)
    assert len(contexts) == 2
    assert contexts[0]["type"] == SMB2_PREAUTH_INTEGRITY
    assert contexts[0]["type_name"] == "preauth_integrity"
    assert contexts[0]["detail"]["hash_algorithms"] == ["SHA-512"]
    assert contexts[1]["type"] == SMB2_ENCRYPTION_CAP
    assert contexts[1]["type_name"] == "encryption"
    assert contexts[1]["detail"]["ciphers"] == ["AES-128-CCM", "AES-128-GCM"]


def test_parse_smb2_negotiate_contexts_unknown_type() -> None:
    context = struct.pack("<H", 0x7777) + struct.pack("<H", 2) + b"\x00" * 4 + b"\x01\x02"
    context += b"\x00" * ((8 - (len(context) % 8)) % 8)
    contexts = _parse_smb2_negotiate_contexts(context, 0)
    assert len(contexts) == 1
    assert contexts[0]["type"] == 0x7777
    assert contexts[0]["type_name"] is None
    assert contexts[0]["detail"] is None


def test_parse_smb2_negotiate_contexts_empty() -> None:
    assert _parse_smb2_negotiate_contexts(b"", 0) == []


# ---------------------------------------------------------------------------
# _decode_smb2_capabilities
# ---------------------------------------------------------------------------


def test_decode_smb2_capabilities_none() -> None:
    assert _decode_smb2_capabilities(0) == []


def test_decode_smb2_capabilities_all() -> None:
    all_bits = 0x7F
    assert _decode_smb2_capabilities(all_bits) == [
        "dfs",
        "leasing",
        "large_mtu",
        "multi_channel",
        "persistent_handles",
        "directory_leasing",
        "encryption",
    ]


# ---------------------------------------------------------------------------
# _parse_smb2_response
# ---------------------------------------------------------------------------


def test_parse_smb2_response_full() -> None:
    guid = bytes(range(16))
    data = _build_smb2_negotiate_response(
        dialect_revision=SMB2_DIALECT_311,
        security_mode=SMB2_SIGNING_ENABLED | SMB2_SIGNING_REQUIRED,
        capabilities=0x00000047,
        server_guid=guid,
    )
    parsed = _parse_smb2_response(data)
    assert parsed["protocol"] == "SMB2"
    assert parsed["command"] == 0
    assert parsed["status"] == 0
    assert parsed["structure_size"] == 65
    assert parsed["security_mode"] == 0x0003
    assert parsed["signing_enabled"] is True
    assert parsed["signing_required"] is True
    assert parsed["dialect_revision"] == SMB2_DIALECT_311
    assert parsed["dialect"] == "SMB 3.1.1"
    assert parsed["server_guid"] == guid.hex()
    assert parsed["capabilities"] == 0x00000047
    assert parsed["capability_flags"] == ["dfs", "leasing", "large_mtu", "encryption"]
    assert parsed["max_transact_size"] == 1048576
    assert parsed["max_read_size"] == 1048576
    assert parsed["max_write_size"] == 1048576
    assert parsed["negotiate_context_count"] == 0
    assert parsed["negotiate_contexts"] == []
    assert parsed["error"] is None


def test_parse_smb2_response_dialect_names() -> None:
    for revision, name in (
        (SMB2_DIALECT_002, "SMB 2.0.2"),
        (SMB2_DIALECT_21, "SMB 2.1"),
        (SMB2_DIALECT_30, "SMB 3.0"),
        (SMB2_DIALECT_302, "SMB 3.0.2"),
        (SMB2_DIALECT_311, "SMB 3.1.1"),
        (0x02FF, "SMB 2.x (wildcard)"),
    ):
        parsed = _parse_smb2_response(_build_smb2_negotiate_response(dialect_revision=revision))
        assert parsed["dialect"] == name, revision


def test_parse_smb2_response_unknown_dialect() -> None:
    parsed = _parse_smb2_response(_build_smb2_negotiate_response(dialect_revision=0x0222))
    assert parsed["dialect"] == "unknown (0x0222)"


def test_parse_smb2_response_signing_disabled() -> None:
    parsed = _parse_smb2_response(_build_smb2_negotiate_response(security_mode=0))
    assert parsed["signing_enabled"] is False
    assert parsed["signing_required"] is False


def test_parse_smb2_response_with_negotiate_contexts() -> None:
    preauth = _build_smb2_preauth_context()
    encryption = _build_smb2_encryption_context()
    blob = preauth + encryption
    data = _build_smb2_negotiate_response(
        negotiate_context_count=2,
        negotiate_context_offset=128,
    ) + blob
    parsed = _parse_smb2_response(data)
    assert parsed["negotiate_context_count"] == 2
    assert len(parsed["negotiate_contexts"]) == 2
    assert parsed["negotiate_contexts"][0]["type_name"] == "preauth_integrity"
    assert parsed["negotiate_contexts"][1]["type_name"] == "encryption"


def test_parse_smb2_response_wrong_structure_size() -> None:
    data = _build_smb2_negotiate_response()
    data = data[:64] + struct.pack("<H", 66) + data[66:]
    parsed = _parse_smb2_response(data)
    assert parsed["error"] == "unexpected SMB2 negotiate structure size 66"


def test_parse_smb2_response_too_short() -> None:
    parsed = _parse_smb2_response(SMB2_MAGIC + b"\x00" * 40)
    assert parsed["error"] == "response too short to be an SMB2 message"


def test_parse_smb2_response_smb1_magic() -> None:
    parsed = _parse_smb2_response(SMB1_MAGIC + b"\x00" * 128)
    assert parsed["error"] == "SMB1 response received for an SMB2 negotiate (not decoded)"


def test_parse_smb2_response_non_smb() -> None:
    parsed = _parse_smb2_response(b"HTTP/1.1 200 OK\r\n" + b"x" * 200)
    assert parsed["error"] == "response is not an SMB2 message"


def test_parse_smb2_response_empty() -> None:
    parsed = _parse_smb2_response(b"")
    assert parsed["error"] == "no response received"


# ---------------------------------------------------------------------------
# _build_smb2_banner
# ---------------------------------------------------------------------------


def test_build_smb2_banner_full() -> None:
    parsed = _parse_smb2_response(
        _build_smb2_negotiate_response(
            security_mode=SMB2_SIGNING_REQUIRED,
            capabilities=0x00000040,
        ),
    )
    banner = _build_smb2_banner(parsed)
    assert banner is not None
    assert "SMB2 negotiate OK" in banner
    assert "dialect=SMB 3.1.1" in banner
    assert "signing=required" in banner
    assert "encryption" in banner
    assert "guid present" in banner


def test_build_smb2_banner_non_smb2() -> None:
    assert _build_smb2_banner({"protocol": "SMB1"}) is None


def test_build_smb2_banner_signing_disabled() -> None:
    parsed = {
        "protocol": "SMB2",
        "dialect": "SMB 3.1.1",
        "security_mode": 0,
        "signing_enabled": False,
        "signing_required": False,
        "server_guid": None,
        "capability_flags": [],
    }
    banner = _build_smb2_banner(parsed)
    assert banner is not None
    assert "signing=disabled" in banner


# ---------------------------------------------------------------------------
# run_smb2
# ---------------------------------------------------------------------------


def test_run_smb2_accessible_via_connector() -> None:
    def connector(host, port, request, timeout):
        assert request[:4] == SMB2_MAGIC
        return _build_smb2_negotiate_response(), None

    results = run_smb2("smb://192.168.1.100:445", connector=connector)
    assert results["target"] == "smb://192.168.1.100:445"
    assert results["host"] == "192.168.1.100"
    assert results["port"] == 445
    assert results["accessible"] is True
    assert results["protocol"] == "SMB2"
    assert results["dialect"] == "SMB 3.1.1"
    assert results["dialect_revision"] == SMB2_DIALECT_311
    assert results["signing_enabled"] is True
    assert results["error"] is None
    assert results["banner"] is not None
    assert "dialect=SMB 3.1.1" in results["banner"]
    assert "message signing is supported but not enforced" in results["notes"]


def test_run_smb2_signing_required_note() -> None:
    def connector(host, port, request, timeout):
        return _build_smb2_negotiate_response(
            security_mode=SMB2_SIGNING_ENABLED | SMB2_SIGNING_REQUIRED,
        ), None

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["signing_required"] is True
    assert "message signing is required by the server" in results["notes"]


def test_run_smb2_smb202_note() -> None:
    def connector(host, port, request, timeout):
        return _build_smb2_negotiate_response(dialect_revision=SMB2_DIALECT_002), None

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["dialect"] == "SMB 2.0.2"
    assert any("original SMB2 specification" in note for note in results["notes"])


def test_run_smb2_timeout_sets_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_smb2("192.168.1.100", timeout=1.0, connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "SMB2 negotiate request failed: timeout"


def test_run_smb2_connection_refused() -> None:
    def connector(host, port, request, timeout):
        return None, "[Errno 111] Connection refused"

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "SMB2 negotiate request failed: [Errno 111] Connection refused"


def test_run_smb2_no_response() -> None:
    def connector(host, port, request, timeout):
        return b"", None

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "SMB2 negotiate request failed: no response"


def test_run_smb2_malformed_response() -> None:
    def connector(host, port, request, timeout):
        return b"HTTP/1.1 200 OK\r\n" + b"x" * 200, None

    results = run_smb2("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "response is not an SMB2 message"


def test_run_smb2_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["host"] = host
        captured["port"] = port
        return _build_smb2_negotiate_response(), None

    results = run_smb2("192.0.2.9:445", port=139, connector=connector)
    assert captured["host"] == "192.0.2.9"
    assert captured["port"] == 139
    assert results["port"] == 139


def test_run_smb2_passes_timeout_to_connector() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["timeout"] = timeout
        return _build_smb2_negotiate_response(), None

    run_smb2("192.168.1.100", timeout=5.0, connector=connector)
    assert captured["timeout"] == 5.0


def test_run_smb2_custom_dialects() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["request"] = request
        return _build_smb2_negotiate_response(dialect_revision=SMB2_DIALECT_21), None

    run_smb2("192.168.1.100", dialects=(SMB2_DIALECT_21,), connector=connector)
    request = captured["request"]
    assert struct.unpack("<H", request[66:68])[0] == 1
    assert struct.unpack("<H", request[100:102])[0] == SMB2_DIALECT_21


# ---------------------------------------------------------------------------
# run_smb with the smb2 follow-up probe
# ---------------------------------------------------------------------------


def _smb1_then_smb2_connector(smb1_response, smb2_response):
    """Build a connector that answers SMB1 and SMB2 probes separately."""
    requests = []

    def connector(host, port, request, timeout):
        requests.append(request)
        if request[:4] == SMB1_MAGIC:
            return smb1_response, None
        return smb2_response, None

    return connector, requests


def test_run_smb_smb2_flag_runs_both_probes() -> None:
    connector, requests = _smb1_then_smb2_connector(
        _build_smb1_response(0, 0x01, b"\x00" * 8),
        _build_smb2_negotiate_response(),
    )
    results = run_smb("192.168.1.100", smb2=True, connector=connector)
    assert len(requests) == 2
    assert requests[0][:4] == SMB1_MAGIC
    assert requests[1][:4] == SMB2_MAGIC
    assert results["accessible"] is True
    assert results["protocol"] == "SMB1"
    assert results["smb2"]["accessible"] is True
    assert results["smb2"]["dialect"] == "SMB 3.1.1"


def test_run_smb_smb2_disabled_by_default() -> None:
    connector, requests = _smb1_then_smb2_connector(
        _build_smb1_response(0, 0x01, b"\x00" * 8),
        _build_smb2_negotiate_response(),
    )
    results = run_smb("192.168.1.100", connector=connector)
    assert len(requests) == 1
    assert "smb2" not in results


def test_run_smb_smb2_failure_does_not_mask_smb1_success() -> None:
    def connector(host, port, request, timeout):
        if request[:4] == SMB1_MAGIC:
            return _build_smb1_response(0, 0x01, b"\x00" * 8), None
        return None, "timeout"

    results = run_smb("192.168.1.100", smb2=True, connector=connector)
    assert results["accessible"] is True
    assert results["error"] is None
    assert results["smb2"]["accessible"] is False
    assert results["smb2"]["error"] == "SMB2 negotiate request failed: timeout"


def test_run_smb_smb2_reports_modern_dialect_when_smb1_disabled() -> None:
    # Modern host: SMB1 negotiate is refused, SMB2 negotiate succeeds.
    def connector(host, port, request, timeout):
        if request[:4] == SMB1_MAGIC:
            return None, "[Errno 111] Connection refused"
        return _build_smb2_negotiate_response(dialect_revision=SMB2_DIALECT_302), None

    results = run_smb("192.168.1.100", smb2=True, connector=connector)
    assert results["accessible"] is False
    assert "Connection refused" in results["error"]
    assert results["smb2"]["accessible"] is True
    assert results["smb2"]["dialect"] == "SMB 3.0.2"


def test_run_smb_smb2_custom_dialects_passthrough() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        if request[:4] == SMB1_MAGIC:
            return _build_smb1_response(0, 0x01, b"\x00" * 8), None
        captured["smb2_request"] = request
        return _build_smb2_negotiate_response(), None

    run_smb(
        "192.168.1.100",
        smb2=True,
        smb2_dialects=(SMB2_DIALECT_311,),
        connector=connector,
    )
    request = captured["smb2_request"]
    assert struct.unpack("<H", request[66:68])[0] == 1
    assert struct.unpack("<H", request[100:102])[0] == SMB2_DIALECT_311


# ---------------------------------------------------------------------------
# Formatters with SMB2 results
# ---------------------------------------------------------------------------


def _smb2_results() -> dict:
    return {
        "target": "smb://192.168.1.100:445",
        "host": "192.168.1.100",
        "port": 445,
        "accessible": True,
        "protocol": "SMB2",
        "dialect_revision": SMB2_DIALECT_311,
        "dialect": "SMB 3.1.1",
        "security_mode": 0x0003,
        "signing_enabled": True,
        "signing_required": True,
        "server_guid": "11" * 16,
        "capabilities": 0x00000040,
        "capability_flags": ["encryption"],
        "max_transact_size": 1048576,
        "max_read_size": 1048576,
        "max_write_size": 1048576,
        "negotiate_context_count": 0,
        "negotiate_contexts": [],
        "banner": "SMB2 negotiate OK; dialect=SMB 3.1.1, signing=required, caps=encryption, guid present",
        "raw_preview": "fe534d42",
        "notes": ["message signing is required by the server"],
        "error": None,
    }


def test_format_smb_report_markdown_with_smb2_section() -> None:
    results = _accessible_results()
    results["smb2"] = _smb2_results()
    output = format_smb_report_markdown(results)
    assert "## SMB2 Negotiation" in output
    assert "- **Dialect:** SMB 3.1.1" in output
    assert "- **Dialect Revision:** 785" in output
    assert "- **Security Mode:** 0x03" in output
    assert "- **Server GUID:** 11" * 1 in output
    assert "- **Capabilities:** encryption" in output
    assert "- **Banner:** SMB2 negotiate OK" in output
    assert "**Note:** message signing is required by the server" in output


def test_format_smb_report_markdown_smb2_inaccessible() -> None:
    results = _inaccessible_results()
    smb2 = _smb2_results()
    smb2["accessible"] = False
    smb2["error"] = "SMB2 negotiate request failed: timeout"
    results["smb2"] = smb2
    output = format_smb_report_markdown(results)
    assert "## SMB2 Negotiation" in output
    assert "- **Accessible:** No" in output
    assert "- **Error:** SMB2 negotiate request failed: timeout" in output


def test_format_smb_report_markdown_smb2_contexts() -> None:
    results = _accessible_results()
    smb2 = _smb2_results()
    smb2["negotiate_context_count"] = 2
    smb2["negotiate_contexts"] = [
        {
            "type": SMB2_PREAUTH_INTEGRITY,
            "type_name": "preauth_integrity",
            "detail": {"hash_algorithms": ["SHA-512"], "salt_length": 32},
        },
        {
            "type": SMB2_ENCRYPTION_CAP,
            "type_name": "encryption",
            "detail": {"ciphers": ["AES-128-GCM"]},
        },
    ]
    results["smb2"] = smb2
    output = format_smb_report_markdown(results)
    assert "- **Negotiate Contexts:** 2" in output
    assert "**preauth_integrity:**" in output
    assert "**encryption:**" in output


def test_format_smb_report_markdown_smb2_context_without_detail() -> None:
    results = _accessible_results()
    smb2 = _smb2_results()
    smb2["negotiate_context_count"] = 1
    smb2["negotiate_contexts"] = [
        {
            "type": SMB2_ENCRYPTION_CAP,
            "type_name": "encryption",
            "detail": None,
        },
    ]
    results["smb2"] = smb2
    output = format_smb_report_markdown(results)
    assert "- **Negotiate Contexts:** 1" in output
    assert "**encryption**" in output


def test_format_smb_report_json_with_smb2() -> None:
    results = _accessible_results()
    results["smb2"] = _smb2_results()
    parsed = json.loads(format_smb_report_json(results))
    assert parsed["smb2"]["dialect"] == "SMB 3.1.1"
    assert parsed["smb2"]["dialect_revision"] == SMB2_DIALECT_311
    assert parsed["smb2"]["server_guid"] == "11" * 16
    assert parsed["smb2"]["capability_flags"] == ["encryption"]


def test_format_smb_report_csv_unchanged_without_smb2() -> None:
    results = _accessible_results()
    results["smb2"] = _smb2_results()
    output = format_smb_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    # The CSV schema is unchanged: the SMB2 probe stays a JSON/Markdown detail.
    assert rows[0] == [
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
    ]


def test_format_smb_report_csv_escapes_special_characters() -> None:
    # Test that CSV formatter properly escapes special characters in banner and challenge
    results = _accessible_results()
    # Set banner to contain a comma and a double quote
    banner_value = 'Server says "Hello, World!"'
    results["banner"] = banner_value
    # Set challenge to contain a comma (though challenge is hex, we test anyway)
    challenge_value = "01,02"
    results["challenge"] = challenge_value
    output = format_smb_report_csv(results)
    # Parse the CSV output
    rows = list(csv.reader(io.StringIO(output)))
    # Check that the row has the correct number of columns
    assert len(rows[1]) == 16
    # Check that the banner value is correctly preserved after CSV parsing
    assert rows[1][14] == banner_value  # banner is at index 14
    # Check that the challenge value is correctly preserved after CSV parsing
    assert rows[1][13] == challenge_value  # challenge is at index 13
