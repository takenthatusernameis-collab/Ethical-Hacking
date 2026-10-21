"""Tests for the ethscan mongodb module."""

import socket
from unittest.mock import patch

from ethscan.mongodb import (
    DEFAULT_PORT,
    _assess_buildinfo,
    _build_buildinfo_request,
    _normalize_target,
    _parse_buildinfo_response,
    _send_recv,
    format_mongodb_report_csv,
    format_mongodb_report_json,
    format_mongodb_report_markdown,
    run_mongodb,
)


# Copy key existing tests
def test_normalize_target_basic():
    assert _normalize_target("mongodb://localhost:27017") == ("localhost", 27017)
    assert _normalize_target("localhost:27017") == ("localhost", 27017)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("[::1]:27017") == ("::1", 27017)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)
    assert _normalize_target("mongodb://[::1]:27017") == ("::1", 27017)


def test_normalize_target_invalid():
    import pytest
    with pytest.raises(ValueError):
        _normalize_target("")
    with pytest.raises(ValueError):
        _normalize_target("   ")
    with pytest.raises(ValueError):
        _normalize_target(":27017")
    with pytest.raises(ValueError):
        _normalize_target("mongodb://")


def test_normalize_target_url_schemes():
    assert _normalize_target("mongodb://localhost") == ("localhost", DEFAULT_PORT)
    assert _normalize_target("mongodb://localhost:1234") == ("localhost", 1234)
    assert _normalize_target("mongo://localhost") == ("localhost", DEFAULT_PORT)
    assert _normalize_target("mongodb://user:pass@localhost:27017") == ("localhost", 27017)
    assert _normalize_target("mongodb://localhost/mydb") == ("localhost", DEFAULT_PORT)
    assert _normalize_target("mongodb://localhost:27017?ssl=true") == ("localhost", 27017)


def test_normalize_target_edge_cases():
    assert _normalize_target("  localhost:27017  ") == ("localhost", 27017)
    assert _normalize_target("localhost:0") == ("localhost", DEFAULT_PORT)
    assert _normalize_target("[::1]:0") == ("::1", DEFAULT_PORT)
    result = _normalize_target("2001:db8::1")
    assert isinstance(result[0], str)
    assert isinstance(result[1], int)


def test_build_buildinfo_request():
    request = _build_buildinfo_request()
    assert isinstance(request, bytes)
    assert len(request) > 20
    msg_len = int.from_bytes(request[0:4], byteorder='little')
    assert msg_len == len(request)
    request_id = int.from_bytes(request[4:8], byteorder='little')
    assert request_id == 1
    response_to = int.from_bytes(request[8:12], byteorder='little')
    assert response_to == 0
    opcode = int.from_bytes(request[12:16], byteorder='little')
    assert opcode == 2004


def test_parse_buildinfo_response_empty():
    assert _parse_buildinfo_response(None) == {}
    assert _parse_buildinfo_response(b"") == {}
    assert _parse_buildinfo_response(b"abc") == {}


def _buildinfo_payload(**fields: str) -> bytes:
    """Build a fake OP_REPLY payload whose document holds the given string fields."""
    doc = b""
    for name, value in fields.items():
        encoded = value.encode("utf-8")
        doc += b"\x02" + name.encode("utf-8") + b"\x00"
        doc += len(encoded).to_bytes(4, byteorder="little")
        doc += encoded
        doc += b"\x00"
    header = b"\x00" * 16 + (1).to_bytes(4, byteorder="little")  # numberReturned = 1
    return header + doc


def test_parse_buildinfo_response_version_string():
    result = _parse_buildinfo_response(_buildinfo_payload(version="5.0.0"))
    assert result["version"] == "5.0.0"


def test_parse_buildinfo_response_sysinfo_and_modules():
    result = _parse_buildinfo_response(
        _buildinfo_payload(version="4.4.1", sysInfo="Linux x86_64", modules="ssl")
    )
    assert result["version"] == "4.4.1"
    assert result["sysInfo"] == "Linux x86_64"
    assert result["modules"] == "ssl"


def test_parse_buildinfo_response_truncated_length():
    # Document declares a string length that runs past the end of the payload:
    # the version must be skipped, not crash.
    doc = b"\x02version\x00" + (100).to_bytes(4, byteorder="little") + b"short\x00"
    result = _parse_buildinfo_response(b"\x00" * 20 + doc)
    assert result == {}


def test_parse_buildinfo_response_version_zero_length():
    # The dedicated version block reads the length at version_pos + 8 (one byte
    # into the field's null terminator). A zero length there passes the size
    # check and stores an empty version string.
    doc = b"\x02version\x00" + (0).to_bytes(4, byteorder="little") + b"\x00"
    header = b"\x00" * 16 + (1).to_bytes(4, byteorder="little")  # numberReturned = 1
    result = _parse_buildinfo_response(header + doc)
    assert result["version"] == ""


def test_send_recv_socket_timeout():
    with patch("ethscan.mongodb.socket.create_connection") as mock_create:
        mock_create.side_effect = socket.timeout()
        data, err = _send_recv("localhost", 27017, b"\x00", 1.0)
    assert data is None
    assert err == "Timeout"


def test_send_recv_connection_refused():
    with patch("ethscan.mongodb.socket.create_connection") as mock_create:
        mock_create.side_effect = ConnectionRefusedError()
        data, err = _send_recv("localhost", 27017, b"\x00", 1.0)
    assert data is None
    assert err == "Connection refused"


def test_send_recv_oserror():
    with patch("ethscan.mongodb.socket.create_connection") as mock_create:
        mock_create.side_effect = OSError("network unreachable")
        data, err = _send_recv("localhost", 27017, b"\x00", 1.0)
    assert data is None
    assert err == "network unreachable"


def test_send_recv_real_socket_path():
    """The non-connector path: create_connection, sendall, recv."""

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def sendall(self, data):
            self.sent = data

        def recv(self, n):
            return b"pong"

    with patch("ethscan.mongodb.socket.create_connection") as mock_create:
        mock_create.return_value = FakeConn()
        data, err = _send_recv("localhost", 27017, b"ping", 1.0)
    assert data == b"pong"
    assert err is None


def test_send_recv_connector_error():
    def failing_connector(host, port, request, timeout):
        raise ValueError("connector boom")

    data, err = _send_recv(
        "localhost", 27017, b"\x00", 1.0, connector=failing_connector
    )
    assert data is None
    assert "connector error" in err
    assert "connector boom" in err


def test_assess_buildinfo_version():
    findings = _assess_buildinfo({"version": "5.0.0"})
    assert any("MongoDB server version: 5.0.0" in f for f in findings)


def test_assess_buildinfo_old_version():
    findings = _assess_buildinfo({"version": "2.4.1"})
    assert any("Old MongoDB version detected" in f for f in findings)


def test_assess_buildinfo_sysinfo_and_modules():
    findings = _assess_buildinfo({"sysInfo": "Linux x86_64", "modules": "ssl"})
    assert any("Build environment: Linux x86_64" in f for f in findings)
    assert any("Modules: ssl" in f for f in findings)


def test_assess_buildinfo_empty():
    assert _assess_buildinfo({}) == []


def test_run_mongodb_value_error():
    result = run_mongodb("")
    assert result["accessible"] is False
    assert result["host"] is None
    assert "Could not parse host" in result["error"]


def test_run_mongodb_empty_probes():
    result = run_mongodb("localhost", probes=[], connector=lambda *a: (b"x", None))
    assert result["accessible"] is False
    assert result["error"] is None


def test_run_mongodb_connector_error():
    result = run_mongodb(
        "localhost", connector=lambda h, p, r, t: (None, "Connection refused")
    )
    assert result["accessible"] is False
    assert result["error"] == "Connection refused"

def test_run_mongodb_transport_failure_is_reported(monkeypatch):
    """A transport failure of an unnamed type is reported, not raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.mongodb.socket.create_connection", boom)

    results = run_mongodb("localhost")
    assert results["accessible"] is False
    assert "hostile transport" in results["error"]


def test_run_mongodb_no_response():
    result = run_mongodb("localhost", connector=lambda *a: (b"", None))
    assert result["accessible"] is False
    assert "No response from server" in result["error"]


def test_run_mongodb_success():
    result = run_mongodb(
        "localhost",
        connector=lambda h, p, r, t: (_buildinfo_payload(version="5.0.0"), None),
    )
    assert result["accessible"] is True
    assert result["version"] == "5.0.0"
    assert result["buildInfo"]["version"] == "5.0.0"
    assert any("MongoDB server version" in f for f in result["findings"])


def test_run_mongodb_old_version_finding():
    result = run_mongodb(
        "mongodb://localhost:27017",
        connector=lambda h, p, r, t: (_buildinfo_payload(version="2.6.9"), None),
    )
    assert result["version"] == "2.6.9"
    assert any("Old MongoDB version detected" in f for f in result["findings"])


def test_run_mongodb_port_override():
    captured = {}

    def connector(host, port, request, timeout):
        captured["port"] = port
        return (_buildinfo_payload(version="5.0.0"), None)

    result = run_mongodb("localhost", port=27018, connector=connector)
    assert captured["port"] == 27018
    assert result["port"] == 27018


def test_format_mongodb_report_markdown_no_findings():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": False,
        "version": None,
        "buildInfo": {},
        "findings": [],
        "error": None,
    }
    output = format_mongodb_report_markdown(data)
    assert "No notable findings" in output


def test_format_mongodb_report_markdown_with_error():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": False,
        "version": None,
        "buildInfo": {},
        "findings": [],
        "error": "Connection refused",
    }
    output = format_mongodb_report_markdown(data)
    assert "## Error" in output
    assert "**Error:** Connection refused" in output


def test_format_mongodb_report_markdown_full():
    data = {
        "target": "mongodb://localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "version": "5.0.0",
        "buildInfo": {"version": "5.0.0", "sysInfo": "Linux x86_64", "modules": "ssl"},
        "findings": ["MongoDB server version: 5.0.0"],
        "error": None,
    }
    output = format_mongodb_report_markdown(data)
    assert "**Server Version:** 5.0.0" in output
    assert "**sysInfo:** Linux x86_64" in output
    assert "**modules:** ssl" in output
    assert "- MongoDB server version: 5.0.0" in output


def test_format_mongodb_report_json_basic():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "version": "5.0.0",
        "buildInfo": {"version": "5.0.0"},
        "findings": ["MongoDB server version: 5.0.0"],
        "error": None,
    }
    output = format_mongodb_report_json(data)
    assert '"target": "localhost:27017"' in output
    assert '"accessible": true' in output


def test_format_mongodb_report_csv_basic():
    data = {
        "target": "localhost:27017",
        "host": "localhost",
        "port": 27017,
        "accessible": True,
        "version": "5.0.0",
        "buildInfo": {"version": "5.0.0", "sysInfo": "Linux x86_64", "modules": "ssl"},
        "findings": ["a", "b"],
        "error": None,
    }
    output = format_mongodb_report_csv(data)
    assert "target,host,port,accessible,version,sysInfo,modules,findings,error" in output
    assert "localhost:27017" in output
    assert "a; b" in output


def test_format_mongodb_report_csv_empty():
    data = {
        "target": "localhost:27017",
        "host": None,
        "port": 27017,
        "accessible": False,
        "version": None,
        "buildInfo": None,
        "findings": [],
        "error": "Connection refused",
    }
    output = format_mongodb_report_csv(data)
    assert "Connection refused" in output

def test_parse_buildinfo_handles_decode_edge_case():
    from ethscan.mongodb import _parse_buildinfo_response
    # Try to construct data that might exercise edge cases
    _parse_buildinfo_response(b'')
    _parse_buildinfo_response(b'\x00\x00\x00\x00' * 5)
