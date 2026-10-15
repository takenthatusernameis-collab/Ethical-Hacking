"""Tests for the ethscan postgresql module."""

import json

from ethscan.postgresql import (
    DEFAULT_PORT,
    _normalize_target,
    _build_startup_request,
    _parse_startup_response,
    _parse_error_fields,
    _assess_startup,
    _AUTH_TYPE_NAMES,
    run_postgresql,
    format_postgresql_report_csv,
    format_postgresql_report_json,
    format_postgresql_report_markdown,
)


def _pg_msg(msg_type: bytes, body: bytes = b"") -> bytes:
    """Build a length-prefixed PostgreSQL backend message (big-endian)."""
    length = 4 + len(body)
    return msg_type + length.to_bytes(4, "big") + body


def _pg_parameter_status(name: str, value: str) -> bytes:
    body = name.encode("utf-8") + b"\x00" + value.encode("utf-8") + b"\x00"
    return _pg_msg(b"S", body)


def _pg_authentication(code: int) -> bytes:
    return _pg_msg(b"R", code.to_bytes(4, "big"))


def _pg_backend_key_data(pid: int) -> bytes:
    return _pg_msg(b"K", pid.to_bytes(4, "big") + (0).to_bytes(4, "big"))


def _pg_error_message(severity: str, code: str, message: str) -> bytes:
    # ErrorResponse field format: <type-byte><value>\0, list terminated by \0.
    body = b"S" + severity.encode("utf-8") + b"\x00"
    body += b"C" + code.encode("utf-8") + b"\x00"
    body += b"M" + message.encode("utf-8") + b"\x00"
    body += b"\x00"
    return _pg_msg(b"E", body)


def _pg_greeting(server_version="16.2", auth_code=0, pid=12345) -> bytes:
    msg = _pg_parameter_status("server_version", server_version)
    msg += _pg_parameter_status("client_encoding", "UTF8")
    msg += _pg_authentication(auth_code)
    msg += _pg_backend_key_data(pid)
    msg += _pg_msg(b"Z", b"I")  # ReadyForQuery
    return msg


# --- target normalization -------------------------------------------------


def test_normalize_target_basic():
    assert _normalize_target("postgresql://localhost:5432") == ("localhost", 5432)
    assert _normalize_target("postgres://localhost:5432") == ("localhost", 5432)
    assert _normalize_target("localhost:5432") == ("localhost", 5432)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("[::1]:5432") == ("::1", 5432)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)
    # URL form with IPv6
    assert _normalize_target("postgresql://[::1]:5432") == ("::1", 5432)


def test_normalize_target_invalid():
    import pytest

    with pytest.raises(ValueError):
        _normalize_target("")
    with pytest.raises(ValueError):
        _normalize_target("://no-host")


def test_normalize_target_port_override_in_url():
    assert _normalize_target("postgresql://db.example.com:5433") == ("db.example.com", 5433)


# --- request building -----------------------------------------------------


def test_build_startup_request():
    request = _build_startup_request()
    assert isinstance(request, bytes)
    assert len(request) > 8
    # Total message length is the first 4 bytes (big-endian), incl. itself.
    msg_len = int.from_bytes(request[0:4], "big")
    assert msg_len == len(request)
    # Protocol version is 3.0 (0x00030000) big-endian.
    proto = int.from_bytes(request[4:8], "big")
    assert proto == 0x00030000
    # Parameter list contains the user slot, null-terminated.
    assert b"user\x00ethscan\x00\x00" in request


def test_build_startup_request_custom_user():
    request = _build_startup_request(user="postgres")
    assert b"user\x00postgres\x00\x00" in request


# --- response parsing -----------------------------------------------------


def test_parse_startup_response_empty():
    empty = {
        "server_version": None,
        "auth_type_code": None,
        "auth_type_name": None,
        "process_id": None,
        "parameters": {},
        "errors": [],
        "notices": [],
    }
    assert _parse_startup_response(None) == empty
    assert _parse_startup_response(b"") == empty


def test_parse_error_fields_empty():
    assert _parse_error_fields(b"") == {}


def test_parse_startup_response_valid():
    resp = _parse_startup_response(_pg_greeting("7.4.5", auth_code=0, pid=5555))
    assert resp["server_version"] == "7.4.5"
    assert resp["auth_type_code"] == 0
    assert resp["auth_type_name"] == "Ok"
    assert resp["process_id"] == 5555
    assert resp["parameters"]["client_encoding"] == "UTF8"
    assert resp["parameters"]["server_version"] == "7.4.5"
    assert resp["errors"] == []
    assert resp["notices"] == []


def test_parse_startup_response_md5_auth():
    resp = _parse_startup_response(_pg_greeting("15.3", auth_code=3, pid=4242))
    assert resp["server_version"] == "15.3"
    assert resp["auth_type_code"] == 3
    assert resp["auth_type_name"] == "MD5Password"
    assert resp["process_id"] == 4242


def test_parse_startup_response_error():
    greeting = _pg_parameter_status("server_version", "16.2") + _pg_error_message(
        "FATAL", "28P01", "password authentication failed for user \"ethscan\""
    )
    resp = _parse_startup_response(greeting)
    assert resp["server_version"] == "16.2"
    assert len(resp["errors"]) == 1
    assert "password authentication failed" in resp["errors"][0]["message"]
    assert resp["errors"][0]["fields"]["C"] == "28P01"


def test_parse_startup_response_truncated():
    # Only a type byte with no length -> parser stops gracefully.
    assert _parse_startup_response(b"S")["parameters"] == {}
    # A length field pointing past the buffer is tolerated.
    assert _parse_startup_response(b"S" + (100).to_bytes(4, "big") + b"partial")["parameters"] == {}


def test_auth_type_names_coverage():
    # Sanity-check the well-known codes map to stable names.
    assert _AUTH_TYPE_NAMES[0] == "Ok"
    assert _AUTH_TYPE_NAMES[3] == "MD5Password"
    assert _AUTH_TYPE_NAMES[10] == "SASL"


# --- assessment -----------------------------------------------------------


def test_assess_startup_with_version():
    findings = _assess_startup({"server_version": "16.2", "auth_type_name": "SASL", "auth_type_code": 10, "process_id": 1234})
    assert any("PostgreSQL server version: 16.2" in f for f in findings)
    assert any("Authentication method: SASL" in f for f in findings)
    assert any("Backend process id: 1234" in f for f in findings)


def test_assess_startup_old_version():
    findings = _assess_startup({"server_version": "8.4.1", "auth_type_name": "MD5Password", "auth_type_code": 3, "process_id": None})
    assert any("Old PostgreSQL version detected" in f for f in findings)
    assert any("Authentication method: MD5Password" in f for f in findings)


def test_assess_startup_empty():
    assert _assess_startup({}) == []


# --- run_postgresql -------------------------------------------------------


def test_run_postgresql_startup():
    results = run_postgresql("localhost", connector=lambda *a: (_pg_greeting("7.4.5", 0, 5555), None))
    assert results["accessible"] is True
    assert results["host"] == "localhost"
    assert results["port"] == DEFAULT_PORT
    assert results["version"] == "7.4.5"
    assert results["startup"]["server_version"] == "7.4.5"
    assert results["startup"]["auth_type_name"] == "Ok"
    assert results["startup"]["process_id"] == 5555


def test_run_postgresql_no_response():
    results = run_postgresql("localhost", connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["error"] == "No response from server"
    assert results["version"] is None


def test_run_postgresql_timeout():
    results = run_postgresql("localhost", connector=lambda *a: (None, "Timeout"))
    assert results["accessible"] is False
    assert results["error"] == "Timeout"


def test_run_postgresql_connection_refused():
    results = run_postgresql("localhost", connector=lambda *a: (None, "Connection refused"))
    assert results["accessible"] is False
    assert results["error"] == "Connection refused"


def test_run_postgresql_empty_probes():
    results = run_postgresql("localhost", probes=[], connector=lambda *a: (_pg_greeting(), None))
    assert results["accessible"] is False
    assert results["error"] is None
    assert results["version"] is None


def test_run_postgresql_url_format():
    captured = {}

    def conn(host, port, request, timeout):
        captured["host"] = host
        captured["port"] = port
        return _pg_greeting("14.1", 3, 99), None

    results = run_postgresql("postgresql://db.example.com:5432", connector=conn)
    assert captured["host"] == "db.example.com"
    assert captured["port"] == 5432
    assert results["host"] == "db.example.com"
    assert results["version"] == "14.1"
    assert results["startup"]["auth_type_name"] == "MD5Password"


def test_run_postgresql_port_override():
    captured = {}

    def conn(host, port, request, timeout):
        captured["port"] = port
        return _pg_greeting(), None

    results = run_postgresql("localhost", port=5433, connector=conn)
    assert captured["port"] == 5433
    assert results["port"] == 5433


def test_run_postgresql_invalid_target():
    results = run_postgresql("", connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["host"] is None
    assert "Could not parse host" in (results["error"] or "")


def test_run_postgresql_case_insensitive_probes():
    called = {"n": 0}

    def conn(host, port, request, timeout):
        called["n"] += 1
        return _pg_greeting("13.2", 0, 111), None

    results = run_postgresql("localhost", probes=["STARTUP"], connector=conn)
    assert results["version"] == "13.2"
    assert called["n"] == 1


# --- formatters -----------------------------------------------------------


def test_format_postgresql_report_json():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": True,
        "startup": {"server_version": "16.2", "auth_type_name": "Ok", "auth_type_code": 0, "process_id": 1, "parameters": {}},
        "version": "16.2",
        "findings": ["PostgreSQL server version: 16.2"],
        "error": None,
    }
    s = format_postgresql_report_json(data)
    assert json.loads(s) == data


def test_format_postgresql_report_markdown_accessible():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": True,
        "startup": {"server_version": "16.2", "auth_type_name": "Ok", "auth_type_code": 0, "process_id": 1, "parameters": {"client_encoding": "UTF8"}},
        "version": "16.2",
        "findings": ["PostgreSQL server version: 16.2"],
        "error": None,
    }
    out = format_postgresql_report_markdown(data)
    assert "# PostgreSQL Reconnaissance Report" in out
    assert "**Accessible:** Yes" in out
    assert "16.2" in out
    assert "client_encoding" in out


def test_format_postgresql_report_markdown_inaccessible():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": False,
        "startup": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_postgresql_report_markdown(data)
    assert "**Accessible:** No" in out
    assert "**Error:** Connection refused" in out


def test_format_postgresql_report_csv():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": True,
        "startup": {"server_version": "16.2", "auth_type_name": "MD5Password", "auth_type_code": 3, "process_id": 4242, "parameters": {}},
        "version": "16.2",
        "findings": ["PostgreSQL server version: 16.2", "Authentication method: MD5Password (code 3)"],
        "error": None,
    }
    out = format_postgresql_report_csv(data)
    lines = out.strip().split("\n")
    assert lines[0].rstrip("\r") == "target,host,port,accessible,version,auth_type,process_id,findings,error"
    assert "localhost" in lines[1]
    assert "16.2" in lines[1]
    assert "MD5Password" in lines[1]
    assert "4242" in lines[1]


def test_format_postgresql_report_csv_inaccessible():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": False,
        "startup": {},
        "version": None,
        "findings": [],
        "error": "Connection refused",
    }
    out = format_postgresql_report_csv(data)
    lines = out.strip().split("\n")
    assert "false" in lines[1]
    assert "Connection refused" in lines[1]


def test_format_postgresql_report_csv_escapes_findings():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": True,
        "startup": {},
        "version": None,
        "findings": ["Old PostgreSQL version detected; suspicious"],
        "error": None,
    }
    out = format_postgresql_report_csv(data)
    # Findings with embedded newlines/special chars are flattened for CSV.
    assert "Old PostgreSQL version detected; suspicious" in out
    header = out.split("\n", 1)[0]
    body = out.split("\n", 1)[1]
    assert "\n" not in body




def test_parse_error_fields_with_truncated():
    body = b"M" + b"message without nul"
    fields = _parse_error_fields(body)
    assert fields["M"] == "message without nul"


def test_parse_error_fields_multiple_fields():
    body = b"SERROR\x00" + b"C28000\x00" + b"Minvalid\x00" + b"\x00"
    fields = _parse_error_fields(body)
    assert fields["S"] == "ERROR"
    assert fields["C"] == "28000"
    assert fields["M"] == "invalid"


def test_parse_startup_response_sasl_auth():
    resp = _parse_startup_response(_pg_greeting("16.2", auth_code=10, pid=4242))
    assert resp["auth_type_code"] == 10
    assert resp["auth_type_name"] == "SASL"


def test_parse_startup_response_cleartext_auth():
    resp = _parse_startup_response(_pg_greeting("16.2", auth_code=2, pid=100))
    assert resp["auth_type_code"] == 2
    assert resp["auth_type_name"] == "CleartextPassword"


def test_parse_startup_response_unknown_auth():
    resp = _parse_startup_response(_pg_greeting("16.2", auth_code=99, pid=100))
    assert resp["auth_type_code"] == 99
    assert resp["auth_type_name"] == "Unknown(99)"


def test_parse_startup_response_notice():
    greeting = _pg_parameter_status("server_version", "16.2") + _pg_authentication(0) + _pg_msg(
        b"N", b"Mnotice message\x00\x00"
    )
    resp = _parse_startup_response(greeting)
    assert len(resp["notices"]) == 1
    assert "notice message" in resp["notices"][0]["message"]


def test_assess_startup_trust_ok():
    findings = _assess_startup({"auth_type_name": "Ok", "auth_type_code": 0})
    assert any("authentication method 'Ok' / trust" in f for f in findings)


def test_assess_startup_error_message():
    startup = {"errors": [{"message": "Connection refused"}]}
    findings = _assess_startup(startup)
    assert any("Server error: Connection refused" in f for f in findings)


def test_assess_startup_version_weird():
    findings = _assess_startup({"server_version": "beta-1.0"})
    assert any("PostgreSQL server version: beta-1.0" in f for f in findings)


def test_run_postgresql_with_probes_none_explicit():
    results = run_postgresql("localhost", probes=None, connector=lambda *a: (_pg_greeting(), None))
    assert results["version"] is not None


def test_run_postgresql_exception_handling():
    def bad_conn(*a):
        raise RuntimeError("boom")
    results = run_postgresql("localhost", connector=bad_conn)
    assert results["accessible"] is False
    assert "boom" in (results["error"] or "")


def test_run_postgresql_invalid_target_url_no_host():
    results = run_postgresql("://no-host", connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["host"] is None


def test_format_postgresql_report_markdown_no_parameters():
    data = {
        "target": "localhost:5432",
        "host": "localhost",
        "port": 5432,
        "accessible": True,
        "startup": {"server_version": "16.2", "auth_type_name": "Ok", "auth_type_code": 0, "process_id": 1},
        "version": "16.2",
        "findings": [],
        "error": None,
    }
    out = format_postgresql_report_markdown(data)
    assert "# PostgreSQL Reconnaissance Report" in out
    assert "No notable findings" in out
