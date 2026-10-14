"""Tests for the ethscan oracle module."""

import json
import struct

from ethscan.oracle import (
    DEFAULT_PORT,
    _normalize_target,
    _build_connect_request,
    _parse_accept_response,
    _parse_refuse_response,
    _assess_version,
    run_oracle,
    format_oracle_report_csv,
    format_oracle_report_json,
    format_oracle_report_markdown,
)


def _tns_header(pkt_type: int, total_length: int) -> bytes:
    """Build a TNS header.

    Args:
        pkt_type: Packet type (0x01=Connect, 0x02=Accept, 0x04=Refuse)
        total_length: Total length of the packet (including the header)
    """
    return struct.pack("!HHBBH", total_length, 0x0000, pkt_type, 0x00, 0x0000)


def _build_accept_response(version: int) -> bytes:
    """Build a TNS Accept response packet.

    The Accept payload is simplified to just the version (2 bytes) for testing.
    """
    payload = struct.pack("!H", version)  # version agreed
    total_length = 8 + len(payload)
    header = _tns_header(0x02, total_length)  # Accept packet type
    return header + payload


def _build_refuse_response(error_data: str = "(DESCRIPTION=(ERR=12514))") -> bytes:
    """Build a TNS Refuse response packet.

    The Refuse payload: reason (2 bytes, 0), data length (2 bytes), data (n bytes)
    """
    error_bytes = error_data.encode("utf-8")
    data_length = len(error_bytes)
    payload = bytearray()
    payload.extend(struct.pack("!H", 0x0000))  # reason (unused)
    payload.extend(struct.pack("!H", data_length))  # data length
    payload.extend(error_bytes)
    total_length = 8 + len(payload)
    header = _tns_header(0x04, total_length)  # Refuse packet type
    return header + bytes(payload)


def test_normalize_target():
    """Test target normalization."""
    assert _normalize_target("localhost") == ("localhost", DEFAULT_PORT)
    assert _normalize_target("localhost:1522") == ("localhost", 1522)
    assert _normalize_target("oracle://localhost:1522") == ("localhost", 1522)
    assert _normalize_target("tns://localhost:1522") == ("localhost", 1522)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)
    assert _normalize_target("[::1]:1522") == ("::1", 1522)
    assert _normalize_target("oracle://[::1]:1522") == ("::1", 1522)
    assert _normalize_target("tns://[::1]:1522") == ("::1", 1522)


def test_build_connect_request():
    """Test building a TNS Connect request."""
    req = _build_connect_request(
        desired_version=0x03FF,
        min_version=0x0000,
        connect_data="(DESCRIPTION=(CONNECT_DATA=(SERVICE_NAME=TEST)))(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))",
    )
    # Check that the packet starts with the TNS header for a Connect packet
    assert len(req) > 8
    pkt_type = struct.unpack("!B", req[4:5])[0]
    assert pkt_type == 0x01  # Connect
    # Check that the version fields are set
    desired_version = struct.unpack("!H", req[8:10])[0]
    assert desired_version == 0x03FF
    min_version = struct.unpack("!H", req[10:12])[0]
    assert min_version == 0x0000
    # Check that the connect data length is set correctly
    # We'll just check that the packet is long enough to contain the connect data
    assert len(req) > 58  # offset to connect data in our build


def test_parse_accept_response():
    """Test parsing an Accept response."""
    accept_pkt = _build_accept_response(0x03EF)  # version 1007
    parsed = _parse_accept_response(accept_pkt)
    assert parsed["version"] == "1007"
    assert parsed["error"] is None


def test_parse_accept_response_truncated():
    """Test parsing a truncated Accept response."""
    # Too short for TNS header
    parsed = _parse_accept_response(b"")
    assert parsed["error"] is not None
    # TNS header but too short for payload
    parsed = _parse_accept_response(_tns_header(0x02, 8))  # header only, no payload
    assert parsed["error"] is not None


def test_parse_refuse_response():
    """Test parsing a Refuse response."""
    refuse_pkt = _build_refuse_response("(DESCRIPTION=(ERR=12514))")
    parsed = _parse_refuse_response(refuse_pkt)
    assert parsed["error"] == "(DESCRIPTION=(ERR=12514))"
    assert parsed["error_code"] == 12514


def test_parse_refuse_response_no_error_code():
    """Test parsing a Refuse response without an error code."""
    refuse_pkt = _build_refuse_response("Some error message")
    parsed = _parse_refuse_response(refuse_pkt)
    assert parsed["error"] == "Some error message"
    assert parsed["error_code"] is None


def test_assess_version():
    """Test version assessment."""
    accept_resp = {"version": "12.2.0.1", "error": None}
    findings = _assess_version(accept_resp)
    assert any("Oracle TNS server version: 12.2.0.1" in f for f in findings)
    assert not any("Error:" in f for f in findings)

    accept_resp = {"version": "12.2.0.1", "error": "Some error"}
    findings = _assess_version(accept_resp)
    assert any("Oracle TNS server version: 12.2.0.1" in f for f in findings)
    assert any("Error: Some error" in f for f in findings)


def _mock_connector_success(host, port, request, timeout):
    """Mock connector that returns a successful Accept response."""
    # We'll return an Accept packet with version 0x03EF (1007)
    return _build_accept_response(0x03EF), None


def _mock_connector_refuse(host, port, request, timeout):
    """Mock connector that returns a Refuse response."""
    return _build_refuse_response("(DESCRIPTION=(ERR=12514))"), None


def _mock_connector_timeout(host, port, request, timeout):
    """Mock connector that simulates a timeout."""
    return None, "Timeout"


def test_run_oracle_success():
    """Test run_oracle with a successful Accept response."""
    results = run_oracle(
        "localhost",
        port=1521,
        timeout=1.0,
        probes=["version"],
        connector=_mock_connector_success,
    )
    assert results["accessible"] is True
    assert results["version"] == "1007"
    assert any("Oracle TNS server version: 1007" in f for f in results["findings"])
    assert results["error"] is None


def test_run_oracle_refuse():
    """Test run_oracle with a Refuse response."""
    results = run_oracle(
        "localhost",
        port=1521,
        timeout=1.0,
        probes=["version"],
        connector=_mock_connector_refuse,
    )
    assert results["accessible"] is True  # We got a response, so accessible
    assert results["version"] is None
    assert results["error"] == "(DESCRIPTION=(ERR=12514))"
    assert any("Error: (DESCRIPTION=(ERR=12514))" in f for f in results["findings"])


def test_run_oracle_timeout():
    """Test run_oracle with a timeout."""
    results = run_oracle(
        "localhost",
        port=1521,
        timeout=1.0,
        probes=["version"],
        connector=_mock_connector_timeout,
    )
    assert results["accessible"] is False
    assert results["version"] is None
    assert results["error"] == "Timeout"
    assert results["findings"] == []


def test_run_oracle_defaults():
    """Test run_oracle with default arguments."""
    results = run_oracle(
        "localhost",
        connector=_mock_connector_success,
    )
    assert results["port"] == DEFAULT_PORT
    assert results["accessible"] is True


def test_format_oracle_report_json():
    """Test JSON formatting."""
    data = {
        "target": "localhost",
        "host": "localhost",
        "port": 1521,
        "accessible": True,
        "version": "1007",
        "findings": ["Oracle TNS server version: 1007"],
        "error": None,
    }
    json_output = format_oracle_report_json(data)
    parsed = json.loads(json_output)
    assert parsed["target"] == "localhost"
    assert parsed["version"] == "1007"


def test_format_oracle_report_markdown():
    """Test Markdown formatting."""
    data = {
        "target": "localhost",
        "host": "localhost",
        "port": 1521,
        "accessible": True,
        "version": "1007",
        "findings": ["Oracle TNS server version: 1007"],
        "error": None,
    }
    md_output = format_oracle_report_markdown(data)
    assert "# Oracle Reconnaissance Report" in md_output
    assert "**Server Version:** 1007" in md_output
    assert "- Oracle TNS server version: 1007" in md_output


def test_format_oracle_report_csv():
    """Test CSV formatting."""
    data = {
        "target": "localhost",
        "host": "localhost",
        "port": 1521,
        "accessible": True,
        "version": "1007",
        "error": None,
    }
    csv_output = format_oracle_report_csv(data)
    lines = csv_output.strip().splitlines()
    assert len(lines) == 2  # header + one data row
    assert "localhost" in lines[1]
    assert "1007" in lines[1]
    assert "true" in lines[1]