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
    format_geo_report_csv,
    format_geo_report_json,
    format_geo_report_markdown,
)

_GEO_CSV_HEADER = [
    "target",
    "ip",
    "country",
    "region",
    "city",
    "lat",
    "lon",
    "isp",
    "org",
    "as_number",
    "reverse_dns",
    "cached",
    "offline_fallback",
    "hop",
    "host",
    "response_type",
    "rtt_avg_ms",
]


# ---------------------------------------------------------------------------
# Host normalization
# ---------------------------------------------------------------------------


def test_normalize_target_bare() -> None:
    assert _normalize_target("example.com") == "example.com"


def test_normalize_target_uppercase() -> None:
    assert _normalize_target("Example.COM") == "example.com"


def test_normalize_target_https_url() -> None:
    assert _normalize_target("https://example.com/path") == "example.com"


def test_normalize_target_ipv6_url() -> None:
    assert _normalize_target("https://[::1]/path") == "::1"
    assert _normalize_target("http://[fd00::1]:8443/path") == "fd00::1"


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
    with patch("ethscan.geo.CACHE_DIR", tmp_path), patch("ethscan.geo.CACHE_FILE", cache_file):
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

    with patch("urllib.request.urlopen", return_value=mock_urlopen), patch("ethscan.geo.CACHE_FILE", Path("/nonexistent/cache.json")):
            result = _get_cached_or_fetch("8.8.8.8", 1.0, use_cache=True, offline_fallback=False)

    assert result["cached"] is False
    assert result["country"] == "United States"


def test_get_cached_or_fetch_fetch_fails_no_cache(tmp_path) -> None:
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{}")

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")), patch("ethscan.geo.CACHE_FILE", cache_file):
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

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")), patch("ethscan.geo.CACHE_FILE", cache_file):
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
def test_format_geo_report_csv_basic() -> None:
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
            "region": "CA",
            "city": "Mountain View",
            "lat": 37.386,
            "lon": -122.0838,
            "isp": "Google LLC",
            "org": "Google LLC",
            "as": "AS15169 Google LLC",
            "reverse": "dns.google",
            "cached": False,
            "offline_fallback": False,
        },
        "notes": [],
    }
    output = format_geo_report_csv(data)
    import csv as _csv

    rows = list(_csv.reader(output.splitlines()))
    assert rows[0] == _GEO_CSV_HEADER
    # primary row: 13 geo cols + 4 empty hop transport cols
    assert rows[1] == [
        "8.8.8.8",
        "8.8.8.8",
        "United States",
        "CA",
        "Mountain View",
        "37.386",
        "-122.0838",
        "Google LLC",
        "Google LLC",
        "AS15169 Google LLC",
        "dns.google",
        "false",
        "false",
        "",
        "",
        "",
        "",
    ]


def test_format_geo_report_csv_empty() -> None:
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
    output = format_geo_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == ",".join(_GEO_CSV_HEADER)
    assert "nonexistent.invalid.domain.tld" in lines[1]


def test_format_geo_report_csv_missing_fields() -> None:
    data = {
        "target": "1.1.1.1",
        "host": "1.1.1.1",
        "ip": "1.1.1.1",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "1.1.1.1",
            "cached": True,
        },
        "notes": [],
    }
    output = format_geo_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == ",".join(_GEO_CSV_HEADER)
    assert "1.1.1.1" in lines[1]
    assert "true" in lines[1]


def test_format_geo_report_csv_field_escaping() -> None:
    data = {
        "target": "1.2.3.4",
        "host": "1.2.3.4",
        "ip": "1.2.3.4",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "1.2.3.4",
            "org": 'Org, Inc',
            "cached": False,
            "offline_fallback": False,
        },
        "notes": [],
    }
    output = format_geo_report_csv(data)
    assert '"Org, Inc"' in output


def test_format_geo_report_csv_offline_fallback() -> None:
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
        "notes": [],
    }
    output = format_geo_report_csv(data)
    assert "true" in output


def test_format_geo_report_csv_recursive_hops() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "recursive": True,
        "hops": [
            {
                "hop": 1,
                "ip": "10.0.0.1",
                "host": "router.local",
                "response_type": "TTL",
                "rtt_avg_ms": 1.5,
                "geolocation": {
                    "status": "success",
                    "query": "10.0.0.1",
                    "country": "United States",
                    "region": "VA",
                    "regionName": "Virginia",
                    "city": "Ashburn",
                    "isp": "ISP-A",
                    "cached": False,
                    "offline_fallback": False,
                },
            },
            {
                "hop": 2,
                "ip": "10.0.0.2",
                "host": None,
                "response_type": "TTL",
                "rtt_avg_ms": 2.5,
                "geolocation": {
                    "status": "success",
                    "query": "10.0.0.2",
                    "country": "Germany",
                    "city": "Frankfurt",
                    "org": "Org, Inc.",
                    "cached": True,
                    "offline_fallback": True,
                },
            },
        ],
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": False,
        },
        "notes": [],
    }
    output = format_geo_report_csv(data)
    import csv as _csv

    rows = list(_csv.reader(output.splitlines()))
    # header + primary result row + one row per hop
    assert len(rows) == 4
    assert rows[0] == _GEO_CSV_HEADER
    # primary row: 13 geo cols + 4 empty hop transport cols
    assert rows[1] == [
        "8.8.8.8",
        "8.8.8.8",
        "United States",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "false",
        "false",
        "",
        "",
        "",
        "",
    ]
    # hop rows preserve order and carry hop geo + hop transport metadata
    assert rows[2] == [
        "8.8.8.8",
        "10.0.0.1",
        "United States",
        "VA",
        "Ashburn",
        "",
        "",
        "ISP-A",
        "",
        "",
        "",
        "false",
        "false",
        "1",
        "router.local",
        "TTL",
        "1.5",
    ]
    assert rows[3] == [
        "8.8.8.8",
        "10.0.0.2",
        "Germany",
        "",
        "Frankfurt",
        "",
        "",
        "",
        "Org, Inc.",
        "",
        "",
        "true",
        "true",
        "2",
        "",
        "TTL",
        "2.5",
    ]
    # transport fields only populated on hop rows, empty on the primary row
    assert rows[1][13:] == ["", "", "", ""]
    assert rows[2][13:] == ["1", "router.local", "TTL", "1.5"]
    assert rows[3][13:] == ["2", "", "TTL", "2.5"]


def test_format_geo_report_csv_hop_transport_missing_fields() -> None:
    """Hop transport columns are populated positionally and empty when absent."""
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "recursive": True,
        "hops": [
            {
                "hop": 1,
                "ip": "10.0.0.1",
                "host": None,
                "response_type": None,
                "rtt_avg_ms": None,
                "geolocation": {
                    "status": "success",
                    "query": "10.0.0.1",
                    "country": "United States",
                    "cached": False,
                },
            },
        ],
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": False,
        },
    }
    output = format_geo_report_csv(data)
    import csv as _csv

    rows = list(_csv.reader(output.splitlines()))
    idx = {name: i for i, name in enumerate(_GEO_CSV_HEADER)}
    # primary row: transport columns empty
    assert rows[1][idx["hop"]] == ""
    assert rows[1][idx["host"]] == ""
    assert rows[1][idx["response_type"]] == ""
    assert rows[1][idx["rtt_avg_ms"]] == ""
    # hop row: hop number present, absent optional fields rendered empty
    assert rows[2][idx["hop"]] == "1"
    assert rows[2][idx["host"]] == ""
    assert rows[2][idx["response_type"]] == ""
    assert rows[2][idx["rtt_avg_ms"]] == ""
    assert rows[2][idx["ip"]] == "10.0.0.1"


def test_format_geo_report_csv_no_hops_is_single_row() -> None:
    data = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": False,
        },
    }
    output = format_geo_report_csv(data)
    lines = output.splitlines()
    assert len(lines) == 2
    assert lines[0] == ",".join(_GEO_CSV_HEADER)


def test_run_geo_offline_fallback_note():
    with patch("ethscan.geo._resolve_host", return_value="8.8.8.8"), patch(
        "ethscan.geo._get_cached_or_fetch",
        return_value={
            "status": "success",
            "country": "United States",
            "cached": True,
            "offline_fallback": True,
        },
    ):
        result = run_geo("8.8.8.8", timeout=1.0, use_cache=True, offline_fallback=True)

    assert result["geolocation"]["offline_fallback"] is True
    assert any("offline fallback" in note.lower() for note in result["notes"])


def test_run_geo_recursive_success():
    with patch("ethscan.geo._resolve_host", return_value="8.8.8.8"), patch(
        "ethscan.geo._get_cached_or_fetch",
        return_value={
            "status": "success",
            "country": "United States",
            "cached": False,
            "offline_fallback": False,
        },
    ), patch(
        "ethscan.trace.run_trace",
        return_value={
            "hops": [
                {
                    "hop": 1,
                    "ip": "10.0.0.1",
                    "host": "router.local",
                    "response_type": "TTL",
                    "rtt_avg_ms": 1.5,
                    "notes": [],
                },
                {
                    "hop": 2,
                    "ip": "10.0.0.1",
                    "host": "dup.local",
                    "response_type": "TTL",
                    "rtt_avg_ms": 2.0,
                    "notes": [],
                },
            ],
            "notes": ["trace note"],
        },
    ):
        result = run_geo("8.8.8.8", timeout=1.0, recursive=True)

    assert result["recursive"] is True
    assert result["hop_count"] == 1
    assert result["hops"][0]["ip"] == "10.0.0.1"
    assert any("traceroute" in note for note in result["notes"])


def test_run_geo_recursive_exception():
    with patch("ethscan.geo._resolve_host", return_value="8.8.8.8"), patch(
        "ethscan.geo._get_cached_or_fetch",
        return_value={
            "status": "success",
            "country": "United States",
            "cached": False,
            "offline_fallback": False,
        },
    ), patch("ethscan.trace.run_trace", side_effect=Exception("trace failed")):
        result = run_geo("8.8.8.8", timeout=1.0, recursive=True)

    assert any("recursive hop geolocation failed" in note for note in result["notes"])
