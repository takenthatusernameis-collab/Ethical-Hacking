"""Tests for the ethscan geo module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ethscan.geo import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT,
    CACHE_DIR,
    CACHE_FILE,
    CACHE_TTL,
    FIELDS,
    _normalize_target,
    _resolve_host,
    _load_cache,
    _save_cache,
    _is_cache_valid,
    _fetch_geo_data,
    _get_cached_or_fetch,
    run_geo,
    format_geo_report_json,
    format_geo_report_markdown,
)


# ---------------------------------------------------------------------------
# Host normalization
# ---------------------------------------------------------------------------


def test_normalize_target_bare() -> None:
    assert _normalize_target("example.com") == "example.com"


def test_normalize_target_uppercase() -> None:
    assert _normalize_target("Example.COM") == "example.com"


def test_normalize_target_https_url() -> None:
    assert _normalize_target("https://example.com/path") == "example.com"


def test_normalize_target_strips_whitespace() -> None:
    assert _normalize_target("  example.com  ") == "example.com"


def test_normalize_target_with_port() -> None:
    assert _normalize_target("http://example.com:8080") == "example.com"


def test_normalize_target_ip_address() -> None:
    assert _normalize_target("192.168.1.1") == "192.168.1.1"


# ---------------------------------------------------------------------------
# Host resolution
# ---------------------------------------------------------------------------


def test_resolve_host_ip() -> None:
    result = _resolve_host("127.0.0.1")
    assert result == "127.0.0.1"


def test_resolve_host_localhost() -> None:
    result = _resolve_host("localhost")
    assert result == "127.0.0.1"


def test_resolve_host_invalid() -> None:
    result = _resolve_host("nonexistent.invalid.domain.tld")
    assert result is None


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------


def test_load_cache_missing() -> None:
    with patch("ethscan.geo.CACHE_FILE", Path("/nonexistent/path/cache.json")):
        result = _load_cache()
        assert result == {}


def test_load_cache_invalid_json(tmp_path) -> None:
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("not valid json")
    with patch("ethscan.geo.CACHE_FILE", cache_file):
        result = _load_cache()
        assert result == {}


def test_load_cache_valid(tmp_path) -> None:
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"8.8.8.8": {"status": "success", "country": "US"}}')
    with patch("ethscan.geo.CACHE_FILE", cache_file):
        result = _load_cache()
        assert "8.8.8.8" in result
        assert result["8.8.8.8"]["country"] == "US"


def test_save_cache(tmp_path) -> None:
    cache_file = tmp_path / "cache.json"
    with patch("ethscan.geo.CACHE_DIR", tmp_path):
        with patch("ethscan.geo.CACHE_FILE", cache_file):
            _save_cache({"8.8.8.8": {"status": "success", "country": "US"}})
            assert cache_file.exists()
            data = json.loads(cache_file.read_text())
            assert data["8.8.8.8"]["country"] == "US"


def test_is_cache_valid() -> None:
    entry = {"timestamp": __import__("time").time()}
    assert _is_cache_valid(entry, ttl=60) is True


def test_is_cache_valid_expired() -> None:
    entry = {"timestamp": __import__("time").time() - 100}
    assert _is_cache_valid(entry, ttl=60) is False


def test_is_cache_valid_missing_timestamp() -> None:
    entry = {"status": "success"}
    assert _is_cache_valid(entry, ttl=60) is False


# ---------------------------------------------------------------------------
# _fetch_geo_data
# ---------------------------------------------------------------------------


def test_fetch_geo_data_success() -> None:
    mock_response = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "countryCode": "US",
        "region": "CA",
        "regionName": "California",
        "city": "Mountain View",
        "zip": "94035",
        "lat": 37.4056,
        "lon": -122.0775,
        "timezone": "America/Los_Angeles",
        "isp": "Google LLC",
        "org": "Google Public DNS",
        "as": "AS15169 Google LLC",
        "reverse": "dns.google",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_geo_data("8.8.8.8", timeout=1.0)

    assert result is not None
    assert result["status"] == "success"
    assert result["country"] == "United States"
    assert "timestamp" in result


def test_fetch_geo_data_fail_status() -> None:
    mock_response = {"status": "fail", "message": "private range"}
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_geo_data("192.168.1.1", timeout=1.0)

    assert result is None


def test_fetch_geo_data_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = _fetch_geo_data("8.8.8.8", timeout=1.0)
        assert result is None


def test_fetch_geo_data_timeout() -> None:
    import socket

    with patch("urllib.request.urlopen", side_effect=socket.timeout()):
        result = _fetch_geo_data("8.8.8.8", timeout=1.0)
        assert result is None


def test_fetch_geo_data_invalid_json() -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"not json"

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_geo_data("8.8.8.8", timeout=1.0)
        assert result is None


# ---------------------------------------------------------------------------
# _get_cached_or_fetch
# ---------------------------------------------------------------------------


def test_get_cached_or_fetch_cache_hit(tmp_path) -> None:
    cached_data = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "timestamp": __import__("time").time(),
    }
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"8.8.8.8": cached_data}))

    with patch("ethscan.geo.CACHE_FILE", cache_file):
        result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=True, offline_fallback=False)

    assert result["cached"] is True
    assert result["country"] == "United States"


def test_get_cached_or_fetch_cache_miss_fetches() -> None:
    mock_response = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        with patch("ethscan.geo.CACHE_FILE", Path("/nonexistent/cache.json")):
            result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=True, offline_fallback=False)

    assert result["cached"] is False
    assert result["country"] == "United States"


def test_get_cached_or_fetch_fetch_fails_no_cache(tmp_path) -> None:
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.geo.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=True, offline_fallback=False)

    assert result["status"] == "fail"
    assert "error" in result
    assert result["cached"] is False


def test_get_cached_or_fetch_fetch_fails_offline_fallback(tmp_path) -> None:
    cached_data = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "timestamp": __import__("time").time() - 100000,  # expired cache
    }
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"8.8.8.8": cached_data}))

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.geo.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=True, offline_fallback=True)

    assert result["cached"] is True
    assert result["offline_fallback"] is True
    assert result["country"] == "United States"


def test_get_cached_or_fetch_no_cache_disabled() -> None:
    mock_response = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=False, offline_fallback=False)

    assert result["cached"] is False
    assert result["country"] == "United States"


# ---------------------------------------------------------------------------
# run_geo
# ---------------------------------------------------------------------------


def test_run_geo_offline_target() -> None:
    with patch("ethscan.geo._resolve_host", return_value=None):
        result = run_geo("nonexistent.invalid.domain.tld")

    assert result["target"] == "nonexistent.invalid.domain.tld"
    assert result["host"] == "nonexistent.invalid.domain.tld"
    assert result["ip"] is None
    assert result["geolocation"] is None
    assert any("Could not resolve" in note for note in result["notes"])


def test_run_geo_success(monkeypatch) -> None:
    mock_response = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "countryCode": "US",
        "region": "CA",
        "regionName": "California",
        "city": "Mountain View",
        "zip": "94035",
        "lat": 37.4056,
        "lon": -122.0775,
        "timezone": "America/Los_Angeles",
        "isp": "Google LLC",
        "org": "Google Public DNS",
        "as": "AS15169 Google LLC",
        "reverse": "dns.google",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.geo._resolve_host", lambda h: "8.8.8.8")
    monkeypatch.setattr("ethscan.geo.CACHE_FILE", Path("/nonexistent/cache.json"))

    result = run_geo("8.8.8.8", timeout=1.0)

    assert result["target"] == "8.8.8.8"
    assert result["host"] == "8.8.8.8"
    assert result["ip"] == "8.8.8.8"
    assert result["geolocation"]["status"] == "success"
    assert result["geolocation"]["country"] == "United States"
    assert result["geolocation"]["cached"] is False


def test_run_geo_url_target(monkeypatch) -> None:
    mock_response = {
        "status": "success",
        "query": "93.184.216.34",
        "country": "United States",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.geo._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.geo.CACHE_FILE", Path("/nonexistent/cache.json"))

    result = run_geo("https://example.com", timeout=1.0)

    assert result["host"] == "example.com"
    assert result["ip"] == "93.184.216.34"


def test_run_geo_cached_result(monkeypatch, tmp_path) -> None:
    cached_data = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "timestamp": __import__("time").time(),
    }
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"8.8.8.8": cached_data}))

    monkeypatch.setattr("ethscan.geo._resolve_host", lambda h: "8.8.8.8")
    monkeypatch.setattr("ethscan.geo.CACHE_FILE", cache_file)

    result = run_geo("8.8.8.8", timeout=1.0, use_cache=True)

    assert result["geolocation"]["cached"] is True
    assert any("cache" in note.lower() for note in result["notes"])


def test_run_geo_custom_api_url(monkeypatch) -> None:
    mock_response = {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
    }
    mock_data = json.dumps(mock_response).encode("utf-8")

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    called_url = []

    def mock_urlopen_func(req, *args, **kwargs):
        called_url.append(req.full_url)
        return mock_urlopen

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_func)
    monkeypatch.setattr("ethscan.geo._resolve_host", lambda h: "8.8.8.8")
    monkeypatch.setattr("ethscan.geo.CACHE_FILE", Path("/nonexistent/cache.json"))

    run_geo("8.8.8.8", timeout=1.0, api_url="https://custom-api.example.com/")

    assert len(called_url) == 1
    assert called_url[0].startswith("https://custom-api.example.com/")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_geo_report_json() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "countryCode": "US",
            "region": "CA",
            "regionName": "California",
            "city": "Mountain View",
            "zip": "94035",
            "lat": 37.4056,
            "lon": -122.0775,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC",
            "org": "Google Public DNS",
            "as": "AS15169 Google LLC",
            "reverse": "dns.google",
            "cached": False,
        },
        "notes": [],
    }
    output = format_geo_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "8.8.8.8"
    assert parsed["geolocation"]["country"] == "United States"


def test_format_geo_report_markdown_success() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "countryCode": "US",
            "region": "CA",
            "regionName": "California",
            "city": "Mountain View",
            "zip": "94035",
            "lat": 37.4056,
            "lon": -122.0775,
            "timezone": "America/Los_Angeles",
            "isp": "Google LLC",
            "org": "Google Public DNS",
            "as": "AS15169 Google LLC",
            "reverse": "dns.google",
            "cached": False,
        },
        "notes": [],
    }
    output = format_geo_report_markdown(data)
    assert "# ethscan IP Geolocation Report" in output
    assert "8.8.8.8" in output
    assert "United States" in output
    assert "Mountain View" in output
    assert "Google LLC" in output


def test_format_geo_report_markdown_fail() -> None:
    data = {
        "target": "192.168.1.1",
        "host": "192.168.1.1",
        "ip": "192.168.1.1",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "fail",
            "query": "192.168.1.1",
            "error": "private range",
            "cached": False,
        },
        "notes": [],
    }
    output = format_geo_report_markdown(data)
    assert "fail" in output
    assert "private range" in output


def test_format_geo_report_markdown_no_geolocation() -> None:
    data = {
        "target": "nonexistent.invalid.domain.tld",
        "host": "nonexistent.invalid.domain.tld",
        "ip": None,
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": None,
        "notes": ["Could not resolve host"],
    }
    output = format_geo_report_markdown(data)
    assert "No geolocation data available" in output


def test_format_geo_report_markdown_cached() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": True,
        },
        "notes": ["Result served from cache"],
    }
    output = format_geo_report_markdown(data)
    assert "**Cached:** Yes" in output


def test_format_geo_report_markdown_offline_fallback() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": True,
            "offline_fallback": True,
        },
        "notes": ["API unavailable; used stale cached data (offline fallback)"],
    }
    output = format_geo_report_markdown(data)
    assert "**Offline Fallback:** Yes" in output


def test_format_geo_report_markdown_with_notes() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
        },
        "notes": ["Note 1", "Note 2"],
    }
    output = format_geo_report_markdown(data)
    assert "Note 1" in output
    assert "Note 2" in output