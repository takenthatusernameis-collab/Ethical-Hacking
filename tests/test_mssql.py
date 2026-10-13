"""Tests for the ethscan mssql module."""

import json
import struct

from ethscan.mssql import (
    DEFAULT_PORT,
    _normalize_target,
    _build_prelogin_request,
    _parse_prelogin_response,
    _assess_prelogin,
    run_mssql,
    format_mssql_report_csv,
    format_mssql_report_json,
    format_mssql_report_markdown,
    _OPTION_VERSION,
    _OPTION_ENCRYPTION,
    _OPTION_INSTINST,
    _OPTION_THREADID,
)


def _tds_prelogin_resp(options_payload: bytes) -> bytes:
    """Build a TDS PRELOGIN response message.

    Args:
        options_payload: The PRELOGIN options payload (type-length-value tuples).

    Returns:
        A complete TDS message with header and options payload.
    """
    # TDS header: type, flags, length, channel ID, packet number, window
    msg_type = 0x12  # PRELOGIN
    flags = 0x01  # first packet
    channel_id = 0x0000
    packet_num = 0x01
    window = 0x0000
    header_length = 9
    msg_len = header_length + len(options_payload)
    header = struct.pack(
        "!BBHHBH",
        msg_type,
        flags,
        msg_len,
        channel_id,
        packet_num,
        window,
    )
    return header + options_payload


def _add_option(opt_type: int, value: bytes) -> bytes:
    """Helper to build a single PRELOGIN option."""
    return struct.pack("!BB", opt_type, len(value)) + value


def test_normalize_target():
    """Test target normalization."""
    # Bare host
    assert _normalize_target("localhost") == ("localhost", DEFAULT_PORT)
    # Host with port
    assert _normalize_target("localhost:1434") == ("localhost", 1434)
    # IPv6
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)
    assert _normalize_target("[::1]:1434") == ("::1", 1434)
    # URL
    assert _normalize_target("mssql://example.com") == ("example.com", DEFAULT_PORT)
    assert _normalize_target("mssql://example.com:1434") == ("example.com", 1434)
    assert _normalize_target("ms-sql://example.com") == ("example.com", DEFAULT_PORT)
    # IPv6 URL (note: urlparse handles brackets)
    assert _normalize_target("mssql://[::1]:1434") == ("::1", 1434)
    # Invalid
    try:
        _normalize_target("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_build_prelogin_request():
    """Test building a PRELOGIN request."""
    req = _build_prelogin_request()
    # Check that we get bytes
    assert isinstance(req, bytes)
    # Check header: first byte should be 0x12 (PRELOGIN)
    assert req[0] == 0x12
    # We could parse further but for now just ensure it's not empty
    assert len(req) > 9  # header + at least some options


def test_parse_prelogin_response():
    """Test parsing a PRELOGIN response."""
    # Build a response with version, encryption, instance name, thread ID
    version_val = struct.pack("!I", 0x0A000000)  # major=10, minor=0, build=0? Actually 0x0A000000 -> major=10, minor=0, build=0?
    encryption_val = b"\x02"  # REQUIRED
    instance_val = b"MSSQLSERVER"
    threadid_val = struct.pack("!I", 54)  # SPID 54

    payload = (
        _add_option(_OPTION_VERSION, version_val) +
        _add_option(_OPTION_ENCRYPTION, encryption_val) +
        _add_option(_OPTION_INSTINST, instance_val) +
        _add_option(_OPTION_THREADID, threadid_val)
    )
    resp = _tds_prelogin_resp(payload)

    parsed = _parse_prelogin_response(resp)
    assert parsed["version"] == "10.0.0"  # major.minor.build
    assert parsed["encryption"] == "REQUIRED"
    assert parsed["instance_name"] == "MSSQLSERVER"
    assert parsed["thread_id"] == 54
    assert parsed["error"] is None

    # Test with truncated response
    parsed2 = _parse_prelogin_response(b"")
    assert parsed2["error"] is not None
    assert "too short" in parsed2["error"]

    # Test with wrong type
    wrong_type = struct.pack(
        "!BBHHBH",
        0x10,  # LOGIN7
        0x01,
        9 + len(payload),
        0x0000,
        0x01,
        0x0000,
    ) + payload
    parsed3 = _parse_prelogin_response(wrong_type)
    assert parsed3["error"] is not None
    assert "Expected PRELOGIN response" in parsed3["error"]


def test_assess_prelogin():
    """Test assessment function."""
    data = {
        "version": "16.0.0",
        "encryption": "REQUIRED",
        "instance_name": "MSSQLSERVER",
        "thread_id": 123,
        "error": None,
    }
    findings = _assess_prelogin(data)
    # Check that we have expected strings
    assert any("MSSQL server version: 16.0.0" in f for f in findings)
    assert any("Encryption: REQUIRED" in f for f in findings)
    assert any("Instance name: MSSQLSERVER" in f for f in findings)
    assert any("Thread ID (SPID): 123" in f for f in findings)
    # No error finding
    assert not any("Error:" in f for f in findings)

    # With error
    data2 = {
        "version": None,
        "encryption": None,
        "instance_name": None,
        "thread_id": None,
        "error": "Connection failed",
    }
    findings2 = _assess_prelogin(data2)
    assert any("Error: Connection failed" in f for f in findings2)


def test_run_mssql():
    """Test the run_mssql function with a mock connector."""
    # Mock connector that returns a predefined response
    def mock_connector(host, port, request, timeout):
        # Build a response similar to test_parse_prelogin_response
        version_val = struct.pack("!I", 0x0A000000)
        encryption_val = b"\x01"  # ON
        instance_val = b"INSTANCE1"
        threadid_val = struct.pack("!I", 99)
        payload = (
            _add_option(_OPTION_VERSION, version_val) +
            _add_option(_OPTION_ENCRYPTION, encryption_val) +
            _add_option(_OPTION_INSTINST, instance_val) +
            _add_option(_OPTION_THREADID, threadid_val)
        )
        return _tds_prelogin_resp(payload), None

    result = run_mssql(
        target="example.com:1433",
        port=1433,
        timeout=1.0,
        probes=["prelogin"],
        connector=mock_connector,
    )
    assert result["accessible"] is True
    assert result["host"] == "example.com"
    assert result["port"] == 1433
    assert result["version"] == "10.0.0"
    assert result["prelogin"]["encryption"] == "ON"
    assert result["prelogin"]["instance_name"] == "INSTANCE1"
    assert result["prelogin"]["thread_id"] == 99
    assert any("MSSQL server version: 10.0.0" in f for f in result["findings"])
    assert any("Encryption: ON" in f for f in result["findings"])
    assert any("Instance name: INSTANCE1" in f for f in result["findings"])
    assert any("Thread ID (SPID): 99" in f for f in result["findings"])
    assert result["error"] is None

    # Test with connection refused
    def mock_connector_refused(host, port, request, timeout):
        return None, "Connection refused"

    result2 = run_mssql(
        target="example.com",
        connector=mock_connector_refused,
    )
    assert result2["accessible"] is False
    assert result2["error"] == "Connection refused"

    # Test with timeout
    def mock_connector_timeout(host, port, request, timeout):
        return None, "Timeout"

    result3 = run_mssql(
        target="example.com",
        connector=mock_connector_timeout,
    )
    assert result3["accessible"] is False
    assert result3["error"] == "Timeout"


def test_formatters():
    """Test the formatter functions."""
    data = {
        "target": "testhost:1433",
        "host": "testhost",
        "port": 1433,
        "accessible": True,
        "version": "16.0.0",
        "prelogin": {
            "version": "16.0.0",
            "encryption": "REQUIRED",
            "instance_name": "MSSQLSERVER",
            "thread_id": 42,
        },
        "findings": [
            "MSSQL server version: 16.0.0",
            "Encryption: REQUIRED",
            "Instance name: MSSQLSERVER",
            "Thread ID (SPID): 42",
        ],
        "error": None,
    }

    json_out = format_mssql_report_json(data)
    parsed = json.loads(json_out)
    assert parsed["target"] == "testhost:1433"
    assert parsed["host"] == "testhost"
    assert parsed["port"] == 1433
    assert parsed["accessible"] is True
    assert parsed["version"] == "16.0.0"

    md_out = format_mssql_report_markdown(data)
    assert "# MSSQL Reconnaissance Report" in md_out
    assert "**Target:** testhost:1433" in md_out
    assert "**Host:** testhost" in md_out
    assert "**Port:** 1433" in md_out
    assert "**Accessible:** Yes" in md_out
    assert "**Server Version:** 16.0.0" in md_out
    assert "## PRELOGIN Response" in md_out
    assert "- **version:** 16.0.0" in md_out
    assert "- **encryption:** REQUIRED" in md_out
    assert "- **instance_name:** MSSQLSERVER" in md_out
    assert "- **thread_id:** 42" in md_out
    assert "## Findings" in md_out
    assert "- MSSQL server version: 16.0.0" in md_out
    assert "- Encryption: REQUIRED" in md_out
    assert "- Instance name: MSSQLSERVER" in md_out
    assert "- Thread ID (SPID): 42" in md_out

    csv_out = format_mssql_report_csv(data)
    # Check that the CSV contains the expected fields
    assert "testhost:1433" in csv_out
    assert "testhost" in csv_out
    assert "1433" in csv_out
    assert "true" in csv_out  # accessible
    assert "16.0.0" in csv_out
    assert "REQUIRED" in csv_out
    assert "MSSQLSERVER" in csv_out
    assert "42" in csv_out
    assert "MSSQL server version: 16.0.0" in csv_out
    assert "Encryption: REQUIRED" in csv_out
    assert "Instance name: MSSQLSERVER" in csv_out
    assert "Thread ID (SPID): 42" in csv_out