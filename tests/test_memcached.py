"""Tests for the ethscan memcached module."""

import json
import pytest

from ethscan.memcached import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _build_memcached_request,
    _normalize_target,
    _parse_stats_response,
    _parse_version_response,
    _send_recv,
    format_memcached_report_csv,
    format_memcached_report_json,
    format_memcached_report_markdown,
    run_memcached,
)


def test_normalize_target_basic():
    assert _normalize_target("memcached://localhost:11211") == ("localhost", 11211)
    assert _normalize_target("localhost:11211") == ("localhost", 11211)
    assert _normalize_target("127.0.0.1") == ("127.0.0.1", DEFAULT_PORT)
    assert _normalize_target("example.com") == ("example.com", DEFAULT_PORT)


def test_normalize_target_ipv6():
    assert _normalize_target("[::1]:11211") == ("::1", 11211)
    assert _normalize_target("[::1]") == ("::1", DEFAULT_PORT)


def test_normalize_target_invalid():
    with pytest.raises(ValueError):
        _normalize_target("")


def test_build_memcached_request_version():
    assert _build_memcached_request("version") == b"version\r\n"


def test_build_memcached_request_stats():
    assert _build_memcached_request("stats") == b"stats\r\n"


def test_build_memcached_request_strips_existing_crlf():
    assert _build_memcached_request("stats\r\n") == b"stats\r\n"


def test_parse_version_response_simple():
    data = b"VERSION 1.6.14\r\n"
    assert _parse_version_response(data) == "1.6.14"


def test_parse_version_response_with_extra_lines():
    data = b"extra\r\nVERSION 1.6.14\r\nmore\r\n"
    assert _parse_version_response(data) == "1.6.14"


def test_parse_version_response_empty():
    assert _parse_version_response(None) is None
    assert _parse_version_response(b"") is None


def test_parse_version_response_non_version():
    assert _parse_version_response(b"END\r\n") is None
    assert _parse_version_response(b"ERROR\r\n") is None


def test_parse_version_response_bare_token():
    assert _parse_version_response(b"1.4.0\r\n") == "1.4.0"


def test_parse_stats_response_full():
    data = (
        b"STAT pid 12345\r\n"
        b"STAT uptime 3600\r\n"
        b"STAT bytes 1048576\r\n"
        b"STAT curr_connections 10\r\n"
        b"STAT get_hits 500\r\n"
        b"STAT get_misses 50\r\n"
        b"STAT evictions 0\r\n"
        b"END\r\n"
    )
    stats = _parse_stats_response(data)
    assert stats["pid"] == "12345"
    assert stats["uptime"] == "3600"
    assert stats["bytes"] == "1048576"
    assert stats["curr_connections"] == "10"
    assert stats["get_hits"] == "500"
    assert stats["get_misses"] == "50"
    assert stats["evictions"] == "0"


def test_parse_stats_response_empty():
    assert _parse_stats_response(None) == {}
    assert _parse_stats_response(b"") == {}


def test_parse_stats_response_end_terminates():
    data = b"STAT pid 1\r\nEND\r\nSTAT ignored 2\r\n"
    stats = _parse_stats_response(data)
    assert stats == {"pid": "1"}


def test_parse_stats_response_no_end():
    data = b"STAT pid 1\r\nSTAT uptime 2\r\n"
    stats = _parse_stats_response(data)
    assert stats == {"pid": "1", "uptime": "2"}


def test_parse_stats_response_value_with_spaces():
    data = b"STAT some_key some value here\r\nEND\r\n"
    stats = _parse_stats_response(data)
    assert stats["some_key"] == "some value here"


def test_parse_stats_response_invalid_lines_ignored():
    data = b"STAT pid 1\r\nGARBAGE\r\nSTAT uptime 2\r\nEND\r\n"
    stats = _parse_stats_response(data)
    assert stats == {"pid": "1", "uptime": "2"}


def test_parse_stats_response_tab_separator():
    data = b"STAT\tpid\t123\r\nEND\r\n"
    stats = _parse_stats_response(data)
    assert stats["pid"] == "123"

def test_run_memcached_version_only():
    """Test run_memcached with only version probe using a fake connector."""
    def connector(host, port, request, timeout):
        if request == b"version\r\n":
            return b"VERSION 1.6.14\r\n", None
        return None, "unexpected request"

    results = run_memcached("localhost", probes=["version"], connector=connector)
    assert results["accessible"] is True
    assert results["version"] == "1.6.14"
    assert results["stats"] == {}


def test_run_memcached_stats_only():
    """Test run_memcached with only stats probe using a fake connector."""
    def connector(host, port, request, timeout):
        if request == b"stats\r\n":
            return (
                b"STAT pid 12345\r\n"
                b"STAT uptime 3600\r\n"
                b"STAT bytes 1024\r\n"
                b"END\r\n",
                None,
            )
        return None, "unexpected request"

    results = run_memcached("localhost", probes=["stats"], connector=connector)
    assert results["accessible"] is True
    assert results["version"] is None
    assert results["stats"]["pid"] == "12345"
    assert results["stats"]["uptime"] == "3600"
    assert results["findings"] == []


def test_run_memcached_both_probes():
    """Test run_memcached with both probes using a fake connector."""
    responses = {
        b"version\r\n": b"VERSION 1.5.22\r\n",
        b"stats\r\n": (
            b"STAT pid 54321\r\n"
            b"STAT uptime 7200\r\n"
            b"STAT bytes 2048\r\n"
            b"STAT curr_connections 5\r\n"
            b"STAT cmd_get 100\r\n"
            b"STAT cmd_set 50\r\n"
            b"STAT get_hits 80\r\n"
            b"STAT get_misses 20\r\n"
            b"STAT evictions 0\r\n"
            b"END\r\n"
        ),
    }

    def connector(host, port, request, timeout):
        if request in responses:
            return responses[request], None
        return None, "unexpected request"

    results = run_memcached("localhost", probes=["version", "stats"], connector=connector)
    assert results["accessible"] is True
    assert results["version"] == "1.5.22"
    assert results["stats"]["pid"] == "54321"
    assert results["stats"]["uptime"] == "7200"
    assert results["stats"]["curr_connections"] == "5"


def test_run_memcached_version_timeout():
    """Test run_memcached handles timeout on version probe."""
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_memcached("localhost", probes=["version"], connector=connector)
    assert results["accessible"] is False
    assert "timeout" in results["error"]


def test_run_memcached_version_connection_refused():
    """Test run_memcached handles connection refused."""
    def connector(host, port, request, timeout):
        return None, "Connection refused"

    results = run_memcached("localhost", probes=["version"], connector=connector)
    assert results["accessible"] is False
    assert "Connection refused" in results["error"]


def test_run_memcached_version_no_response():
    """Test run_memcached handles no response (empty data)."""
    def connector(host, port, request, timeout):
        return b"", None

    results = run_memcached("localhost", probes=["version"], connector=connector)
    assert results["accessible"] is False
    assert "no response" in results["error"]


def test_run_memcached_stats_error_does_not_mask_version():
    """Test that stats probe error doesn't mask version success when version runs first."""
    # Actually our implementation runs probes sequentially and returns on first error
    # This test verifies the current behavior
    def connector(host, port, request, timeout):
        if request == b"version\r\n":
            return b"VERSION 1.6.14\r\n", None
        if request == b"stats\r\n":
            return None, "timeout"

    results = run_memcached("localhost", probes=["version", "stats"], connector=connector)
    assert results["accessible"] is True
    assert results["version"] == "1.6.14"
    assert "timeout" in results["error"]


def test_run_memcached_port_override():
    """Test that explicit port overrides parsed port."""
    def connector(host, port, request, timeout):
        assert port == 11212
        return b"VERSION 1.6.14\r\n", None

    results = run_memcached("localhost:11211", port=11212, probes=["version"], connector=connector)
    assert results["port"] == 11212


def test_run_memcached_custom_timeout_passthrough():
    """Test that custom timeout is passed to connector."""
    received = {}

    def connector(host, port, request, timeout):
        received["timeout"] = timeout
        return b"VERSION 1.6.14\r\n", None

    run_memcached("localhost", timeout=5.0, probes=["version"], connector=connector)
    assert received["timeout"] == 5.0


def test_run_memcached_probes_defaults():
    """Test that default probes are version and stats."""
    assert DEFAULT_PROBES == ("version", "stats")


def test_format_memcached_report_json():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": True,
        "version": "1.6.14",
        "stats": {"pid": "123", "uptime": "3600"},
        "findings": [],
        "error": None,
    }
    output = format_memcached_report_json(data)
    parsed = json.loads(output)
    assert parsed["version"] == "1.6.14"
    assert parsed["stats"]["pid"] == "123"


def test_format_memcached_report_markdown():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": True,
        "version": "1.6.14",
        "stats": {"pid": "123", "uptime": "3600", "curr_connections": "5"},
        "findings": [],
        "error": None,
    }
    output = format_memcached_report_markdown(data)
    assert "# ethscan Memcached Reconnaissance Report" in output
    assert "**Target:** localhost:11211" in output
    assert "**Memcached Version:** 1.6.14" in output
    assert "pid" in output
    assert "uptime" in output


def test_format_memcached_report_markdown_inaccessible():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": False,
        "version": None,
        "stats": {},
        "findings": [],
        "error": "Connection refused",
    }
    output = format_memcached_report_markdown(data)
    assert "**Accessible:** No" in output
    assert "**Error:** Connection refused" in output


def test_format_memcached_report_csv():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": True,
        "version": "1.6.14",
        "stats": {
            "uptime": "3600",
            "bytes": "1024",
            "curr_connections": "5",
            "cmd_get": "100",
            "cmd_set": "50",
            "get_hits": "80",
            "get_misses": "20",
            "evictions": "0",
        },
        "findings": [],
        "error": None,
    }
    output = format_memcached_report_csv(data)
    lines = output.strip().split("\n")
    # CSV lines may end with \r\n, strip \r for comparison
    header = lines[0].rstrip("\r")
    assert header == "target,host,port,accessible,version,uptime,bytes,curr_connections,cmd_get,cmd_set,get_hits,get_misses,evictions,findings,error"
    assert "localhost" in lines[1]
    assert "1.6.14" in lines[1]


def test_format_memcached_report_csv_inaccessible():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": False,
        "version": None,
        "stats": {},
        "findings": [],
        "error": "Connection refused",
    }
    output = format_memcached_report_csv(data)
    lines = output.strip().split("\n")
    assert "false" in lines[1]
    assert "Connection refused" in lines[1]


def test_format_memcached_report_csv_escapes_findings():
    data = {
        "target": "localhost:11211",
        "host": "localhost",
        "port": 11211,
        "accessible": True,
        "version": "1.6.14",
        "stats": {"evictions": "5"},
        "findings": ["evictions are occurring (cache pressure)"],
        "error": None,
    }
    output = format_memcached_report_csv(data)
    assert "evictions are occurring" in output


def test_run_memcached_probe_list_case_insensitive():
    """Test that probe names are case-insensitive."""
    def connector(host, port, request, timeout):
        if request == b"version\r\n":
            return b"VERSION 1.6.14\r\n", None
        if request == b"stats\r\n":
            return b"STAT pid 1\r\nEND\r\n", None
        return None, "unexpected"

    results = run_memcached("localhost", probes=["VERSION", "Stats"], connector=connector)
    assert results["version"] == "1.6.14"
    assert "pid" in results["stats"]


def test_run_memcached_empty_probes_list():
    """Test that empty probes list means no probes run."""
    results = run_memcached("localhost", probes=[], connector=lambda *a: (b"", None))
    assert results["accessible"] is False
    assert results["error"] is None
