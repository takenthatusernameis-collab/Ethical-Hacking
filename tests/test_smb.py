"""Tests for the ethscan smb module."""

import csv
import io
import json
import struct

import pytest

from ethscan.smb import (
    DEFAULT_DIALECTS,
    DEFAULT_PORT,
    SMB1_MAGIC,
    SMB2_MAGIC,
    SMB_COM_NEGOTIATE,
    _build_smb1_negotiate_request,
    _normalize_target,
    _parse_smb_response,
    _send_recv,
    format_smb_report_csv,
    format_smb_report_json,
    format_smb_report_markdown,
    run_smb,
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
