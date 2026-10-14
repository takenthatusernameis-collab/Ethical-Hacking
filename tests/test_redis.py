"""Tests for the ethscan redis module."""
import csv
import io
import json

import pytest

from ethscan.redis import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _build_resp_array,
    _normalize_target,
    _parse_config,
    _parse_info,
    _parse_resp,
    _parse_resp_bulk_string,
    _parse_resp_simple_string,
    _send_recv,
    format_redis_report_csv,
    format_redis_report_json,
    format_redis_report_markdown,
    run_redis,
)


def test_normalize_target_basic():
    assert _normalize_target("redis://localhost:6379") == ("localhost", 6379)
    assert _normalize_target("localhost:6379") == ("localhost", 6379)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("redis://[::1]:6379") == ("::1", 6379)
    assert _normalize_target("[::1]:6379") == ("::1", 6379)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)


def test_build_resp_array_ping():
    req = _build_resp_array("PING")
    assert req == b"*1\r\n$4\r\nPING\r\n"


def test_build_resp_array_multi():
    req = _build_resp_array("INFO", "server")
    assert req == b"*2\r\n$4\r\nINFO\r\n$6\r\nserver\r\n"


def test_parse_resp_simple_string():
    parsed, c = _parse_resp(b"+PONG\r\n")
    assert parsed == "PONG"
    assert c == 7


def test_parse_resp_bulk_string():
    parsed, c = _parse_resp_bulk_string(b"$5\r\nhello\r\n")
    assert parsed == "hello"
    assert c == 11


def test_parse_resp_bulk_string_null():
    parsed, c = _parse_resp_bulk_string(b"$-1\r\n")
    assert parsed is None
    assert c == 5


def test_parse_resp_array():
    resp = b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n"
    parsed, c = _parse_resp(resp)
    assert parsed == ["hello", "world"]


def test_parse_info():
    content = "redis_version:6.2.0\r\nos:Linux\r\nrole:master\r\n"
    bcontent = content.encode('utf-8')
    data = b'$' + str(len(bcontent)).encode('ascii') + b'\r\n' + bcontent + b'\r\n'
    info = _parse_info(data)
    assert info["redis_version"] == "6.2.0"
    assert info["os"] == "Linux"


def test_parse_config():
    data = b'*4\r\n$4\r\nbind\r\n$7\r\n0.0.0.0\r\n$11\r\nrequirepass\r\n$0\r\n\r\n'
    cfg = _parse_config(data)
    assert cfg["bind"] == "0.0.0.0"
    assert cfg["requirepass"] == ""


def test_send_recv_with_connector():
    def fake(host, port, req, timeout):
        return b"+PONG\r\n", None
    data, err = _send_recv("h", 6379, b"req", 5.0, connector=fake)
    assert data == b"+PONG\r\n"
    assert err is None


def test_send_recv_connector_error():
    def fake(host, port, req, timeout):
        return None, "boom"
    data, err = _send_recv("h", 6379, b"req", 5.0, connector=fake)
    assert data is None
    assert err == "boom"


def test_run_redis_ping_only():
    calls = []

    def fake(host, port, req, timeout):
        calls.append(req)
        return b"+PONG\r\n", None

    res = run_redis("example.com", port=6379, timeout=5.0, probes=["ping"], connector=fake)
    assert res["ping"] == "PONG"
    assert res["accessible"] is True
    assert len(calls) == 1


def test_run_redis_all_probes():
    def fake(host, port, req, timeout):
        s = req.decode('utf-8', errors='replace')
        if 'PING' in s:
            return b"+PONG\r\n", None
        elif 'INFO' in s:
            content = 'redis_version:6.2.0\r\nos:Linux\r\nrole:master\r\nconnected_clients:2\r\n'
            bcontent = content.encode('utf-8')
            return b'$' + str(len(bcontent)).encode('ascii') + b'\r\n' + bcontent + b'\r\n', None
        elif 'CONFIG' in s:
            return b'*4\r\n$4\r\nbind\r\n$7\r\n0.0.0.0\r\n$11\r\nrequirepass\r\n$0\r\n\r\n', None
        return b"+OK\r\n", None

    res = run_redis("example.com", port=6379, timeout=5.0, connector=fake)
    assert res["ping"] == "PONG"
    assert res["info"]["redis_version"] == "6.2.0"
    assert "bind is set to 0.0.0.0" in res["dangerous_findings"][0]


def test_format_redis_json():
    data = {"target": "example.com", "host": "example.com", "port": 6379, "ping": "PONG", "accessible": True}
    out = format_redis_report_json(data)
    assert json.loads(out)["target"] == "example.com"


def test_format_redis_markdown():
    data = {"target": "example.com", "host": "example.com", "port": 6379, "ping": "PONG", "accessible": True,
            "info": {"redis_version": "6.2.0"}, "config": {}, "dangerous_findings": []}
    out = format_redis_report_markdown(data)
    assert "# ethscan Redis Reconnaissance Report" in out
    assert "PONG" in out


def test_format_redis_csv():
    data = {"target": "example.com", "host": "example.com", "port": 6379, "ping": "PONG", "accessible": True,
            "info": {"redis_version": "6.2.0", "os": "Linux", "role": "master", "connected_clients": "1"},
            "config": {"bind": "127.0.0.1", "requirepass": "pw"}, "dangerous_findings": [],
            "error": None}
    out = format_redis_report_csv(data)
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0][0] == "target"
    assert rows[1][0] == "example.com"
    assert rows[1][3] == "true"
