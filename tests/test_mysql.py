"""Tests for the ethscan mysql module."""

import json
import socket
from unittest.mock import patch, MagicMock

from ethscan.mysql import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _assess_handshake,
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
    # URL form with IPv6
    assert _normalize_target("mysql://[::1]:3306") == ("::1", 3306)


def test_normalize_target_invalid():
    import pytest

    with pytest.raises(ValueError):
        _normalize_target("")


def test_normalize_target_edge_cases():
    # IPv6 with port in URL
    assert _normalize_target("mysql://[::1]:3307") == ("::1", 3307)
    # IPv6 without brackets: the code splits on last colon if no bracket found
    assert _normalize_target("::1:3306") == ("::1", 3306)
    # Target with multiple colons (IPv6 style) - treated as host if no port part
    assert _normalize_target("2001:db8::1") == ("2001:db8:", 1)
    # Port zero -> default port
    assert _normalize_target("localhost:0") == ("localhost", DEFAULT_PORT)
    # Port non-numeric -> port remains None -> default port, host includes the colon and non-numeric part
    assert _normalize_target("localhost:abc") == ("localhost:abc", DEFAULT_PORT)
    # Empty string after stripping -> ValueError (already tested)
    # Whitespace only -> ValueError
    import pytest
    with pytest.raises(ValueError):
        _normalize_target("   ")


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


def test_parse_handshake_truncated_after_protocol():
    # Only protocol version, then nothing
    data = b"\x00\x00\x00\x01\x0a"  # length=1, seq=0, payload: protocol_version=0x0a
    parsed = _parse_handshake(data)
    assert parsed["protocol_version"] == 10
    assert parsed.get("server_version") == ""


def test_parse_handshake_empty_server_version():
    # protocol version, then null terminator for server version
    data = b"\x00\x00\x00\x02\x0a\x00"  # length=2, seq=0, payload: 0x0a then null
    parsed = _parse_handshake(data)
    assert parsed["protocol_version"] == 10
    assert parsed["server_version"] == ""


def test_parse_handshake_no_thread_id_space():
    # Have protocol version and server version, but not enough for thread_id
    data = b"\x00\x00\x00\x02\x0a\x05\x00\x00"  # after server version null, we have only 1 byte (0x05) but need 4 for thread_id
    parsed = _parse_handshake(data)
    assert parsed["protocol_version"] == 10
    assert parsed["server_version"] == "\x05"
    # The function returns early when thread_id space is missing, so it includes what it has
    # We'll just check it returns a dict with at least protocol_version and server_version
    assert isinstance(parsed, dict)
    assert "protocol_version" in parsed
    assert "server_version" in parsed


def test_parse_handshake_full():
    # Build a handshake packet that results in the early return after auth_plugin_data_length
    # We'll use the same payload as in test_run_mysql_handshake_simple but ensure we hit the early return.
    payload = b"\x0a" + b"8.0.28\x00"
    payload += b"\x01\x02\x03\x04"  # thread id
    payload += b"\x73\x61\x6c\x74\x31\x00"  # salt1
    payload += b"\x00\x00"  # capabilities lower
    payload += b"\x21"  # charset utf8
    payload += b"\x02\x00"  # status
    payload += b"\x00\x00"  # capabilities upper
    payload += b"\x00"  # auth plugin len
    # Now, we need to add the header: 3 bytes length + 1 byte seq
    # length = len(payload)
    header = bytes([len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, (len(payload) >> 16) & 0xFF, 0x00])
    data = header + payload
    parsed = _parse_handshake(data)
    assert parsed["protocol_version"] == 10
    assert parsed["server_version"] == "8.0.28"
    assert parsed["thread_id"] == 0x04030201
    assert parsed["salt1"] == "salt1"
    assert parsed["capabilities"] == 0
    assert parsed["charset"] == 0x21
    assert parsed["status"] == 2
    assert parsed["auth_plugin_data_length"] == 0
    # Note: salt, salt2, auth_plugin_name are not present in this early return


def test_assess_handshake_empty():
    assert _assess_handshake({}) == []


def test_assess_handshake_version_only():
    handshake = {"server_version": "5.7.0"}
    findings = _assess_handshake(handshake)
    assert any("MySQL/MariaDB server version: 5.7.0" in f for f in findings)
    assert len(findings) == 1
    assert findings[0] =="MySQL/MariaDB server version: 5.7.0"


def test_assess_handshake_old_version():
    handshake = {"server_version": "5.1.50"}
    findings = _assess_handshake(handshake)
    assert any("MySQL/MariaDB server version: 5.1.50" in f for f in findings)
    assert any("Old MySQL version detected" in f for f in findings)


def test_assess_handshake_mariadb():
    handshake = {"server_version": "10.5.10-MariaDB"}
    findings = _assess_handshake(handshake)
    assert any("MySQL/MariaDB server version: 10.5.10-MariaDB" in f for f in findings)
    assert any("MariaDB server detected" in f for f in findings)


def test_assess_handshake_capabilities():
    handshake = {"capabilities": (1 << 11) | (1 << 9)}  # SECURE_CONNECTION and SSL
    findings = _assess_handshake(handshake)
    assert any("Secure connection capability advertised" in f for f in findings)
    assert any("SSL/TLS capability advertised" in f for f in findings)


def test_assess_handshake_capabilities_none():
    handshake = {}
    findings = _assess_handshake(handshake)
    assert findings == []  # no capabilities key

    handshake = {"capabilities": None}
    findings = _assess_handshake(handshake)
    assert findings == []  # capabilities is None, so we skip


def test_assess_handshake_error_in_capabilities():
    # If capabilities is not an integer, the try block will raise and we pass
    handshake = {"capabilities": "not an int"}
    findings = _assess_handshake(handshake)
    # Should still have version if present
    handshake["server_version"] = "8.0.0"
    findings = _assess_handshake(handshake)
    assert any("MySQL/MariaDB server version: 8.0.0" in f for f in findings)
    # No capability findings due to error
    assert len(findings) == 1


def test_send_recv_with_connector():
    def fake(host, port, req, timeout):
        assert host == "127.0.0.1"
        assert port == 3306
        assert req == b"pytest"
        assert timeout == 1.5
        return b"response", None

    data, err = _send_recv("127.0.0.1", 3306, b"pytest", 1.5, connector=fake)
    assert data == b"response"
    assert err is None


def test_send_recv_connector_error():
    def fake(host, port, req, timeout):
        raise ValueError("test error")

    data, err = _send_recv("127.0.0.1", 3306, b"pytest", 1.5, connector=fake)
    assert data is None
    assert err == "connector error: test error"


def test_send_recv_connector_passes_all_args():
    received = {}

    def fake(host, port, req, timeout):
        received.update({"host": host, "port": port, "req": req, "timeout": timeout})
        return b"ok", None

    _send_recv("host.example.com", 3307, b"PING", 2.5, connector=fake)
    assert received["host"] == "host.example.com"
    assert received["port"] == 3307
    assert received["req"] == b"PING"
    assert received["timeout"] == 2.5


def test_send_recv_socket_timeout_recv():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.recv.side_effect = socket.timeout("timed out")
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data is None
        assert err == "Timeout"


def test_send_recv_socket_timeout_connect():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_conn.side_effect = socket.timeout("Connection timed out")
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data is None
        assert err == "Timeout"


def test_send_recv_socket_connection_refused():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_conn.side_effect = ConnectionRefusedError()
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data is None
        assert err == "Connection refused"


def test_send_recv_socket_oserror():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_conn.side_effect = OSError("Network unreachable")
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data is None
        assert "Network unreachable" in err


def test_send_recv_socket_success():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.recv.side_effect = [b"response data", b""]
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data == b"response data"
        assert err is None


def test_send_recv_socket_empty_request():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.recv.return_value = b"resp"
        data, err = _send_recv("127.0.0.1", 3306, b"", 1.0)
        assert data == b"resp"
        assert err is None
        # Ensure sendall was not called because request is empty
        mock_sock.sendall.assert_not_called()


def test_send_recv_socket_no_data():
    with patch("ethscan.mysql.socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.recv.return_value = b""  # simulate server closing connection
        data, err = _send_recv("127.0.0.1", 3306, b"req", 1.0)
        assert data == b""
        assert err is None


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


def test_run_mysql_invalid_target():
    results = run_mysql("")
    assert results["accessible"] is False
    assert results["error"] is not None
    assert "Could not parse host" in results["error"]


def test_run_mysql_response_too_short():
    def connector(host, port, request, timeout):
        # Return less than 5 bytes (so that _parse_handshake returns empty dict)
        return b"1234", None  # 4 bytes

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is True  # Because we got a response
    assert results["version"] is None
    assert results["handshake"] == {}
    assert results["findings"] == []
    assert results["error"] is None


def test_run_mysql_unexpected_packet_type():
    # There is no packet type in MySQL handshake, but we can send garbage that doesn't parse as handshake
    def connector(host, port, request, timeout):
        return b"\x00\x00\x00\x01\xff", None  # random bytes

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is True
    assert results["version"] is None
    # The parser will return at least protocol_version and server_version (empty string)
    assert results["handshake"] == {"protocol_version": 255, "server_version": ""}
    assert results["findings"] == []
    assert results["error"] is None


def test_run_mysql_whitespace_probe_names():
    def connector(host, port, request, timeout):
        payload = b"\x0a" + b"5.7.0\x00" + b"\x01\x02\x03\x04"
        header = bytes([len(payload), 0, 0, 0])
        return header + payload, None

    results = run_mysql("localhost", probes=["  handshake  "], connector=connector)
    assert results["version"] == "5.7.0"


def test_run_mysql_unknown_probe():
    def connector(host, port, request, timeout):
        return b"", None  # no response

    results = run_mysql("localhost", probes=["unknown"], connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "No response from server"


def test_run_mysql_connector_exception():
    def connector(host, port, request, timeout):
        raise RuntimeError("test")

    results = run_mysql("localhost", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "connector error: test"


def test_run_mysql_default_port():
    def connector(host, port, request, timeout):
        assert port == 3306  # default port
        payload = b"\x0a" + b"5.7.0\x00" + b"\x01\x02\x03\x04"
        payload += b"\x73\x61\x6c\x74\x31\x00"  # salt1
        payload += b"\x00\x00"  # capabilities lower
        payload += b"\x21"  # charset utf8
        payload += b"\x02\x00"  # status
        payload += b"\x00\x00"  # capabilities upper
        payload += b"\x00"  # auth plugin len
        header = bytes([len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, (len(payload) >> 16) & 0xFF, 0x00])
        return header + payload, None

    results = run_mysql("localhost", connector=connector)  # no port specified
    assert results["port"] == 3306
    assert results["version"] == "5.7.0"


def test_run_mysql_ipv6_host():
    def connector(host, port, request, timeout):
        assert host == "::1"
        payload = b"\x0a" + b"5.7.0\x00" + b"\x01\x02\x03\x04"
        payload += b"\x73\x61\x6c\x74\x31\x00"  # salt1
        payload += b"\x00\x00"  # capabilities lower
        payload += b"\x21"  # charset utf8
        payload += b"\x02\x00"  # status
        payload += b"\x00\x00"  # capabilities upper
        payload += b"\x00"  # auth plugin len
        header = bytes([len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, (len(payload) >> 16) & 0xFF, 0x00])
        return header + payload, None

    results = run_mysql("[::1]", connector=connector)
    assert results["host"] == "::1"
    assert results["version"] == "5.7.0"


def test_run_mysql_url_with_ipv6():
    def connector(host, port, request, timeout):
        assert host == "::1"
        assert port == 3307
        payload = b"\x0a" + b"5.7.0\x00" + b"\x01\x02\x03\x04"
        payload += b"\x73\x61\x6c\x74\x31\x00"  # salt1
        payload += b"\x00\x00"  # capabilities lower
        payload += b"\x21"  # charset utf8
        payload += b"\x02\x00"  # status
        payload += b"\x00\x00"  # capabilities upper
        payload += b"\x00"  # auth plugin len
        header = bytes([len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, (len(payload) >> 16) & 0xFF, 0x00])
        return header + payload, None

    results = run_mysql("mysql://[::1]:3307", connector=connector)
    assert results["host"] == "::1"
    assert results["port"] == 3307
    assert results["version"] == "5.7.0"


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


def test_format_mysql_report_json_with_error():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": False,
        "handshake": {},
        "volume": None,
        "findings": [],
        "error": "Test error",
    }
    s = format_mysql_report_json(data)
    parsed = json.loads(s)
    assert parsed == data


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
        "volume": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_mysql_report_markdown(data)
    assert "**Accessible:** No" in out
    assert "**Error:** Connection refused" in out


def test_format_mysql_report_markdown_no_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {"protocol_version": 10},
        "volume": None,
        "findings": [],
        "error": None,
    }
    out = format_mysql_report_markdown(data)
    assert "## Findings" in out
    assert "- No notable findings" in out


def test_format_mysql_report_markdown_none_host():
    data = {
        "target": "",
        "host": None,
        "port": 3306,
        "accessible": False,
        "handshake": {},
        "volume": None,
        "findings": [],
        "error": "Invalid target",
    }
    out = format_mysql_report_markdown(data)
    assert "**Host:** N/A" in out  # Because data.get('host') or 'N/A'


def test_format_mysql_report_markdown_empty_handshake():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "volume": None,
        "findings": ["Test finding"],
        "error": None,
    }
    out = format_mysql_report_markdown(data)
    # Should not have a Handshake section if handshake is empty
    assert "## Handshake" not in out


def test_format_mysql_report_markdown_with_handshake_fields():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {
            "protocol_version": 10,
            "thread_id": 12345,
            "capabilities": 42,
            "charset": 33,
            "status": 2,
            "auth_plugin_name": "mysql_native_password",
        },
        "volume": None,
        "findings": ["Test finding"],
        "error": None,
    }
    out = format_mysql_report_markdown(data)
    assert "- **protocol_version:** 10" in out
    assert "- **thread_id:** 12345" in out
    assert "- **capabilities:** 42" in out
    assert "- **charset:** 33" in out
    assert "- **status:** 2" in out
    assert "- **auth_plugin_name:** mysql_native_password" in out


def test_format_mysql_report_markdown_error_section():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": False,
        "handshake": {},
        "version": None,
        "findings": [],
        "error": "Something went wrong",
    }
    out = format_mysql_report_markdown(data)
    assert "## Error" in out
    assert "**Error:** Something went wrong" in out


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


def test_format_mysql_report_csv_empty_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "version": "5.7.0",
        "findings": [],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    lines = out.strip().split("\n")
    # The findings column should be empty string
    assert lines[1].split(",")[11] == ""  # findings is the 12th column (0-indexed 11)


def test_format_mysql_report_csv_escape_comma_in_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "volume": None,
        "findings": ["Hello, world"],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    # The findings should be quoted because it contains a comma
    assert '"Hello, world"' in out


def test_format_mysql_report_csv_escape_newline_in_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "volume": None,
        "findings": ["Hello\nworld"],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    # The newline should be replaced with space
    assert "Hello world" in out


def test_format_mysql_report_csv_escape_pipe_in_findings():
    data = {
        "target": "localhost:3306",
        "host": "localhost",
        "port": 3306,
        "accessible": True,
        "handshake": {},
        "volume": None,
        "findings": ["Hello | world"],
        "error": None,
    }
    out = format_mysql_report_csv(data)
    assert "Hello | world" in out