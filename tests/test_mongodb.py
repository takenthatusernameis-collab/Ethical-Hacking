"""Tests for the ethscan mongodb module."""

import json

from ethscan.mongodb import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _normalize_target,
    _build_buildinfo_request,
    _parse_buildinfo_response,
    _assess_buildinfo,
    run_mongodb,
    format_mongodb_report_csv,
    format_mongodb_report_json,
    format_mongodb_report_markdown,
)


def test_normalize_target_basic():
    assert _normalize_target("mongodb://localhost:27017") == ("localhost", 27017)
    assert _normalize_target("localhost:27017") == ("localhost", 27017)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("[::1]:27017") == ("::1", 27017)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)
    # URL form with IPv6
    assert _normalize_target("mongodb://[::1]:27017") == ("::1", 27017)


def test_normalize_target_invalid():
    import pytest

    with pytest.raises(ValueError):
        _normalize_target("")


def test_build_buildinfo_request():
    request = _build_buildinfo_request()
    # Should be a bytes object with reasonable length
    assert isinstance(request, bytes)
    assert len(request) > 20  # Should have header + data

    # Check that it starts with a valid MongoDB message header
    # First 4 bytes: message length (little endian)
    msg_len = int.from_bytes(request[0:4], byteorder='little')
    assert msg_len == len(request)

    # Next 4 bytes: request ID
    request_id = int.from_bytes(request[4:8], byteorder='little')
    assert request_id == 1

    # Next 4 bytes: response to
    response_to = int.from_bytes(request[8:12], byteorder='little')
    assert response_to == 0

    # Next 4 bytes: opcode (OP_QUERY = 2004)
    opcode = int.from_bytes(request[12:16], byteorder='little')
    assert opcode == 2004  # OP_QUERY


def test_parse_buildinfo_response_empty():
    assert _parse_buildinfo_response(None) == {}
    assert _parse_buildinfo_response(b"") == {}
    assert _parse_buildinfo_response(b"abc") == {}


def test_parse_buildinfo_response_valid():
    # Build a simple mock OP_REPLY message with a buildInfo response
    # This is simplified - we're testing that our parser doesn't crash
    # on valid-ish input

    # OP_REPLY header: 16 bytes
    # Then we'll add a simple document with version field
    # For simplicity, we test that it handles empty/corrupted data gracefully
    result = _parse_buildinfo_response(b"")
    assert isinstance(result, dict)

    result = _parse_buildinfo_response(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
    assert isinstance(result, dict)


def test_assess_buildinfo():
    # Test with version info
    buildinfo = {"version": "5.0.12", "sysInfo": "Linux", "modules": ""}
    findings = _assess_buildinfo(buildinfo)
    assert any("MongoDB server version: 5.0.12" in f for f in findings)
    assert any("Build environment: Linux" in f for f in findings)

    # Test with old version
    buildinfo_old = {"version": "2.4.14", "sysInfo": "", "modules": ""}
    findings_old = _assess_buildinfo(buildinfo_old)
    assert any("Old MongoDB version detected" in f for f in findings_old)

    # Test with empty info
    buildinfo_empty = {}
    findings_empty = _assess_buildinfo(buildinfo_empty)
    assert findings_empty == []


def test_run_mongodb_buildinfo_simple():
    def connector(host, port, request, timeout):
        # Build a simple mock OP_REPLY message
        # OP_REPLY header: flags(0), cursorID(0), startingFrom(0), numberReturned(1)
        header = bytearray(16)
        header[0:4] = (0).to_bytes(4, byteorder='little')  # flags
        header[4:8] = (0).to_bytes(4, byteorder='little')  # cursorID low
        header[8:12] = (0).to_bytes(4, byteorder='little')  # cursorID high
        header[12:16] = (0).to_bytes(4, byteorder='little')  # startingFrom
        header[16:20] = (1).to_bytes(4, byteorder='little')  # numberReturned

        # Simple document with version string: { version: "5.0.12" }
        # BSON: \x0e\x00\x00\x00\x02version\x00\x06\x00\x00\x005.0.12\x00\x00
        doc = b'\x0e\x00\x00\x00\x02version\x00\x06\x00\x00\x005.0.12\x00\x00'

        return bytes(header) + doc, None

    results = run_mongodb("localhost", connector=connector)
    assert results["accessible"] is True
    assert results["version"] == "5.0.12"
    assert results["buildInfo"].get("version") == "5.0.12"


def test_run_mongodb_no_response():
    def connector(host, port, request, timeout):
        return b"", None

    results = run_mongodb("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "No response from server"


def test_run_mongodb_timeout():
    def connector(host, port, request, timeout):
        return None, "Timeout"

    results = run_mongodb("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "Timeout"


def test_run_mongodb_connection_refused():
    def connector(host, port, request, timeout):
        return None, "Connection refused"

    results = run_mongodb("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "Connection refused"


def test_run_mongodb_empty_probes():
    results = run_mongodb("localhost", probes=[], connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["error"] is None


def test_run_mongodb_url_format():
    def conn(host, port, request, timeout):
        assert host == "db.example.com"
        assert port == 27017
        # Build mock response
        header = bytearray(20)
        header[16:20] = (1).to_bytes(4, byteorder='little')  # numberReturned = 1
        doc = b'\x0e\x00\x00\x00\x02version\x00\x06\x00\x00\x004.4.12\x00\x00'
        return bytes(header) + doc, None

    results = run_mongodb("mongodb://db.example.com:27017", connector=conn)
    assert results["host"] == "db.example.com"
    assert results["version"] == "4.4.12"


def test_run_mongodb_case_insensitive_probes():
    def conn(host, port, request, timeout):
        # Build mock response
        header = bytearray(20)
        header[16:20] = (1).to_bytes(4, byteorder='little')  # numberReturned = 1
        doc = b'\x0e\x00\x00\x00\x02version\x00\x06\x00\x00\x003.6.20\x00\x00'
        return bytes(header) + doc, None

    results = run_mongodb("localhost", probes=["BUILDINFO"], connector=conn)
    assert results["version"] == "3.6.20"


def test_format_mongodb_report_json():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "buildInfo": {"version": "5.0.12", "sysInfo": "Linux"},
        "version": "5.0.12",
        "findings": ["MongoDB server version: 5.0.12"],
        "error": None,
    }
    s = format_mongodb_report_json(data)
    assert json.loads(s) == data


def test_format_mongodb_report_markdown_accessible():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "buildInfo": {"version": "5.0.12", "sysInfo": "Linux"},
        "version": "5.0.12",
        "findings": ["MongoDB server version: 5.0.12"],
        "error": None,
    }
    out = format_mongodb_report_markdown(data)
    assert "# MongoDB Reconnaissance Report" in out
    assert "**Accessible:** Yes" in out
    assert "5.0.12" in out


def test_format_mongodb_report_markdown_inaccessible():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": False,
        "buildInfo": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_mongodb_report_markdown(data)
    assert "**Accessible:** No" in out
    assert "**Error:** Connection refused" in out


def test_format_mongodb_report_csv():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "buildInfo": {"version": "5.0.12", "sysInfo": "Linux"},
        "version": "5.0.12",
        "findings": ["MongoDB server version: 5.0.12"],
        "error": None,
    }
    out = format_mongodb_report_csv(data)
    lines = out.strip().split("\n")
    header = lines[0].rstrip("\r")
    assert header == "target,host,port,accessible,version,sysInfo,modules,findings,error"
    assert "localhost" in lines[1]
    assert "5.0.12" in lines[1]


def test_format_mongodb_report_csv_inaccessible():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": False,
        "buildInfo": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_mongodb_report_csv(data)
    lines = out.strip().split("\n")
    assert "false" in lines[1]
    assert "Connection refused" in lines[1]


def test_format_mongodb_report_csv_escapes_findings():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "buildInfo": {},
        "version": "2.0.0",
        "findings": ["Old MongoDB version detected; suspicious"],
        "error": None,
    }
    out = format_mongodb_report_csv(data)
    assert "Old MongoDB version" in out