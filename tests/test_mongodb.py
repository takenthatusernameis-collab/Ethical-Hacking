"""Tests for the ethscan mongodb module."""

import json
from unittest.mock import Mock, patch

from ethscan.mongodb import (
    DEFAULT_PORT,
    DEFAULT_PROBES,
    DEFAULT_TIMEOUT,
    _normalize_target,
    _build_buildinfo_request,
    _parse_buildinfo_response,
    _assess_buildinfo,
    _send_recv,
    run_mongodb,
    format_mongodb_report_csv,
    format_mongodb_report_json,
    format_mongodb_report_markdown,
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
