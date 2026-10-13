"""Tests for the ethscan mysql module."""

import json

from ethscan.mysql import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _normalize_target,
    _parse_handshake,
    _send_recv,
    format_mysql_report_csv,
    format_mysql_report_json,
    format_mysql_report_markdown,
    run_mysql,
)


def test_normalize_target_basic():
    assert _normalize_target("mysql://localhost:3306") == ("localhost", 3306)
    assert _normalize_target("localhost:3306") == ("localhost", 3306)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("[::1]:3306") == ("::1", 3306)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)


def test_normalize_target_invalid():
    import pytest

    with pytest.raises(ValueError):
        _normalize_target("")


def test_parse_handshake_empty():
    assert _parse_handshake(None) == {}
    assert _parse_handshake(b"") == {}
    assert _parse_handshake(b"abc") == {}


def test_parse_handshake_minimal():
    # Minimal: protocol version 10, server version "5.7.0", then terminator
    data = b"\x00\x00\x00\x01" + b"\x0a" + b"5.7.0\x00"
    parsed = _parse_handshake(data)
    assert parsed["protocol_version"] == 10
    assert parsed["server_version"] == "5.7.0"


def test_run_mysql_handshake_simple():
    def connector(host, port, request, timeout):
        # Server handshake V10 - construct a minimal one
        payload = b"\x0a" + b"8.0.28\x00"
        payload += b"\x01\x02\x03\x04"  # thread id
        payload += b"\x73\x61\x6c\x74\x31\x00"  # salt1
        payload += b"\x00\x00"  # capabilities lower
        payload += b"\x21"  # charset utf8
        payload += b"\x02\x00"  # status
        payload += b"\x00\x00"  # capabilities upper
        payload += b"\x00"  # auth plugin len
        # pack with header (len 4 byte header total, payload length)
        header = bytes([len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, (len(payload) >> 16) & 0xFF, 0x00])
        return header + payload, None

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is True
    assert results["version"] == "8.0.28"
    assert results["handshake"]["protocol_version"] == 10


def test_run_mysql_no_response():
    def connector(host, port, request, timeout):
        return b"", None

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "No response from server"


def test_run_mysql_timeout():
    def connector(host, port, request, timeout):
        return None, "Timeout"

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "Timeout"


def test_run_mysql_connection_refused():
    def connector(host, port, request, timeout):
        return None, "Connection refused"

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "Connection refused"


def test_run_mysql_empty_probes():
    results = run_mysql("localhost", probes=[], connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["error"] is None


def test_run_mysql_port_override():
    def connector(host, port, request, timeout):
        assert port == 3307
        return b"\x0a5.6.51\x00", None  # minimal

    # with header for minimal
    def conn(host, port, request, timeout):
        payload = b"\x0a" + b"5.6.51\x00" + b"\x01\x00\x00\x00"
        header = bytes([len(payload), 0, 0, 0])
        return header + payload, None

    results = run_mysql("localhost", port=3307, connector=conn)
    assert results["port"] == 3307


def test_run_mysql_url_format():
    def conn(host, port, request, timeout):
        assert host == "db.example.com"
        assert port == 3306
        payload = b"\x0a" + b"5.7.44\x00" + b"\x01\x00\x00\x00"
        header = bytes([len(payload), 0, 0, 0])
        return header + payload, None

    results = run_mysql("mysql://db.example.com:3306", connector=conn)
    assert results["host"] == "db.example.com"
    assert results["version"] == "5.7.44"


def test_run_mysql_case_insensitive_probes():
    def conn(host, port, request, timeout):
        payload = b"\x0a" + b"8.0.0\x00" + b"\x01\x00\x00\x00"
        header = bytes([len(payload), 0, 0, 0])
        return header + payload, None

    results = run_mysql("localhost", probes=["HANDSHAKE"], connector=conn)
    assert results["version"] == "8.0.0"


def test_format_mysql_report_json():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {"protocol_version": 10, "server_version": "8.0.28"},
        "version": "8.0.28",
        "findings": ["MySQL/MariaDB server version: 8.0.28"],
        "error": None,
    }
    s = format_mysql_report_json(data)
    assert json.loads(s) == data


def test_format_mysql_report_markdown_accessible():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {"protocol_version": 10, "server_version": "8.0.28"},
        "version": "8.0.28",
        "findings": ["MySQL/MariaDB server version: 8.0.28"],
        "error": None,
    }
    out = format_mysql_report_markdown(data)
    assert "# MySQL Reconnaissance Report" in out
    assert "**Accessible:** Yes" in out
    assert "8.0.28" in out


def test_format_mysql_report_markdown_inaccessible():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": False,
        "handshake": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_mysql_report_markdown(data)
    assert "**Accessible:** No" in out
    assert "**Error:** Connection refused" in out


def test_format_mysql_report_csv():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {
            "protocol_version": 10,
            "thread_id": 1,
            "capabilities": 65535,
            "charset": 33,
            "status": 2,
            "auth_plugin_name": "caching_sha2_password",
        },
        "version": "8.0.28",
        "findings": ["MySQL/MariaDB server version: 8.0.28"],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    lines = out.strip().split("\n")
    header = lines[0].rstrip("\r")
    assert header == "target,host,port,accessible,version,protocol_version,thread_id,capabilities,charset,status,auth_plugin_name,findings,error"
    assert "localhost" in lines[1]
    assert "8.0.28" in lines[1]


def test_format_mysql_report_csv_inaccessible():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": False,
        "handshake": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_mysql_report_csv(data)
    lines = out.strip().split("\n")
    assert "false" in lines[1]
    assert "Connection refused" in lines[1]


def test_format_mysql_report_csv_escapes_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "version": "5.5.5",
        "findings": ["Old MySQL version detected; suspicious"],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    assert "Old MySQL version" in out
