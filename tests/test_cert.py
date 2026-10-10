"""Tests for the ethscan cert module."""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from ethscan.cert import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT,
    CACHE_DIR,
    CACHE_FILE,
    CACHE_TTL,
    _normalize_target,
    _resolve_host,
    _load_cache,
    _save_cache,
    _is_cache_valid,
    _fetch_cert_data,
    _get_cached_or_fetch,
    _extract_subdomains,
    run_cert,
    format_cert_report_json,
    format_cert_report_markdown,
)


# ---------------------------------------------------------------------------
# Target normalization
# ---------------------------------------------------------------------------


def test_normalize_target_bare() -> None:
    assert _normalize_target("example.com") == "example.com"


def test_normalize_target_uppercase() -> None:
    assert _normalize_target("Example.COM") == "example.com"


def test_normalize_target_https_url() -> None:
    assert _normalize_target("https://example.com/path") == "example.com"


def test_normalize_target_http_url() -> None:
    assert _normalize_target("http://example.com/path") == "example.com"


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
    with patch("ethscan.cert.CACHE_FILE", Path("/nonexistent/path/cert_cache.json")):
        result = _load_cache()
        assert result == {}


def test_load_cache_invalid_json(tmp_path) -> None:
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text("not valid json")
    with patch("ethscan.cert.CACHE_FILE", cache_file):
        result = _load_cache()
        assert result == {}


def test_load_cache_valid(tmp_path) -> None:
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text('{"example.com": {"count": 5}}')
    with patch("ethscan.cert.CACHE_FILE", cache_file):
        result = _load_cache()
        assert "example.com" in result
        assert result["example.com"]["count"] == 5


def test_save_cache(tmp_path) -> None:
    cache_file = tmp_path / "cert_cache.json"
    with patch("ethscan.cert.CACHE_DIR", tmp_path):
        with patch("ethscan.cert.CACHE_FILE", cache_file):
            _save_cache({"example.com": {"count": 5}})
            assert cache_file.exists()
            data = json.loads(cache_file.read_text())
            assert data["example.com"]["count"] == 5


def test_is_cache_valid() -> None:
    entry = {"timestamp": time.time()}
    assert _is_cache_valid(entry, ttl=60) is True


def test_is_cache_valid_expired() -> None:
    entry = {"timestamp": time.time() - 100}
    assert _is_cache_valid(entry, ttl=60) is False


def test_is_cache_valid_missing_timestamp() -> None:
    entry = {"count": 5}
    assert _is_cache_valid(entry, ttl=60) is False


# ---------------------------------------------------------------------------
# _fetch_cert_data
# ---------------------------------------------------------------------------


def test_fetch_cert_data_success() -> None:
    entry = {
        "issuer_ca_id": 1234,
        "issuer_name": "Example CA",
        "name_value": "example.com",
        "common_name": "example.com",
        "entry_timestamp": "2024-01-01T00:00:00",
    }
    mock_data = json.dumps([entry]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_cert_data("example.com", timeout=1.0)

    assert result is not None
    assert result["domain"] == "example.com"
    assert result["count"] == 1
    assert len(result["entries"]) == 1


def test_fetch_cert_data_empty_list() -> None:
    mock_data = json.dumps([]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_cert_data("example.com", timeout=1.0)

    assert result is not None
    assert result["count"] == 0
    assert result["entries"] == []


def test_fetch_cert_data_non_list_response() -> None:
    mock_data = json.dumps({"not": "a list"}).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_cert_data("example.com", timeout=1.0)

    assert result is None


def test_fetch_cert_data_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = _fetch_cert_data("example.com", timeout=1.0)
        assert result is None


def test_fetch_cert_data_timeout() -> None:
    import socket

    with patch("urllib.request.urlopen", side_effect=socket.timeout()):
        result = _fetch_cert_data("example.com", timeout=1.0)
        assert result is None


def test_fetch_cert_data_invalid_json() -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"not json"

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_cert_data("example.com", timeout=1.0)
        assert result is None


def test_fetch_cert_data_custom_api_url() -> None:
    entry = {"name_value": "sub.example.com"}
    mock_data = json.dumps([entry]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    called_url = []

    def mock_urlopen_func(req, *args, **kwargs):
        called_url.append(req.full_url)
        return mock_urlopen

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_func):
        _fetch_cert_data("example.com", timeout=1.0, api_url="https://custom.example.com/")

    assert len(called_url) == 1
    assert called_url[0].startswith("https://custom.example.com/")


# ---------------------------------------------------------------------------
# _get_cached_or_fetch
# ---------------------------------------------------------------------------


def test_get_cached_or_fetch_cache_hit(tmp_path) -> None:
    cached_data = {
        "domain": "8.8.8.8",
        "entries": [{"name_value": "8.8.8.8"}],
        "count": 1,
        "timestamp": time.time(),
    }
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text(json.dumps({"example.com": cached_data}))

    with patch("ethscan.cert.CACHE_FILE", cache_file):
        result = _get_cached_or_fetch("example.com", 1.0, use_cache=True, offline_fallback=False, api_url=None)

    assert result["cached"] is True
    assert result["count"] == 1


def test_get_cached_or_fetch_cache_miss_fetches(monkeypatch) -> None:
    entry = {"name_value": "sub.example.com"}
    mock_data = json.dumps([entry]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", Path("/nonexistent/cert_cache.json"))

    result = _get_cached_or_fetch("example.com", 1.0, use_cache=True, offline_fallback=False, api_url=None)

    assert result["cached"] is False
    assert result["count"] == 1


def test_get_cached_or_fetch_fetch_fails_no_cache(tmp_path) -> None:
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text("{}")

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.cert.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch("example.com", 1.0, use_cache=True, offline_fallback=False, api_url=None)

    assert result["count"] == 0
    assert result["entries"] == []
    assert "error" in result
    assert result["cached"] is False


def test_get_cached_or_fetch_fetch_fails_offline_fallback(tmp_path) -> None:
    cached_data = {
        "domain": "example.com",
        "entries": [{"name_value": "cached.example.com"}],
        "count": 1,
        "timestamp": time.time() - 100000,
    }
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text(json.dumps({"example.com": cached_data}))

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.cert.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch("example.com", 1.0, use_cache=True, offline_fallback=True, api_url=None)

    assert result["cached"] is True
    assert result["offline_fallback"] is True
    assert result["count"] == 1


def test_get_cached_or_fetch_no_cache_disabled(monkeypatch) -> None:
    entry = {"name_value": "sub.example.com"}
    mock_data = json.dumps([entry]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)

    result = _get_cached_or_fetch("example.com", 1.0, use_cache=False, offline_fallback=False, api_url=None)

    assert result["cached"] is False
    assert result["count"] == 1


# ---------------------------------------------------------------------------
# _extract_subdomains
# ---------------------------------------------------------------------------


def test_extract_subdomains_basic() -> None:
    cert_data = {
        "entries": [
            {"name_value": "www.example.com"},
            {"name_value": "api.example.com"},
        ]
    }
    result = _extract_subdomains(cert_data)
    assert "www.example.com" in result
    assert "api.example.com" in result
    assert len(result) == 2


def test_extract_subdomains_dedupes() -> None:
    cert_data = {
        "entries": [
            {"name_value": "www.example.com"},
            {"name_value": "www.example.com"},
        ]
    }
    result = _extract_subdomains(cert_data)
    assert len(result) == 1


def test_extract_subdomains_common_name_fallback() -> None:
    cert_data = {
        "entries": [
            {"common_name": "mail.example.com"},
        ]
    }
    result = _extract_subdomains(cert_data)
    assert "mail.example.com" in result


def test_extract_subdomains_multiline_name_value() -> None:
    cert_data = {
        "entries": [
            {"name_value": "www.example.com\napi.example.com"},
        ]
    }
    result = _extract_subdomains(cert_data)
    assert "www.example.com" in result
    assert "api.example.com" in result


def test_extract_subdomains_empty() -> None:
    cert_data = {"entries": []}
    result = _extract_subdomains(cert_data)
    assert result == []


def test_extract_subdomains_no_entries() -> None:
    cert_data = {}
    result = _extract_subdomains(cert_data)
    assert result == []


def test_extract_subdomains_skips_non_dict() -> None:
    cert_data = {
        "entries": ["not a dict", None, {"name_value": "valid.example.com"}],
    }
    result = _extract_subdomains(cert_data)
    assert result == ["valid.example.com"]


def test_extract_subdomains_strips_whitespace() -> None:
    cert_data = {
        "entries": [
            {"name_value": "  www.example.com  "},
        ]
    }
    result = _extract_subdomains(cert_data)
    assert result == ["www.example.com"]


# ---------------------------------------------------------------------------
# run_cert
# ---------------------------------------------------------------------------


def test_run_cert_offline_target() -> None:
    with patch("ethscan.cert._resolve_host", return_value=None):
        result = run_cert("nonexistent.invalid.domain.tld")

    assert result["target"] == "nonexistent.invalid.domain.tld"
    assert result["domain"] == "nonexistent.invalid.domain.tld"
    assert result["ip"] is None
    assert result["cert_data"] is None
    assert result["subdomains"] == []
    assert any("Could not resolve" in note for note in result["notes"])


def test_run_cert_success(monkeypatch) -> None:
    entry = {"name_value": "www.example.com"}
    mock_data = json.dumps([entry]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", Path("/nonexistent/cert_cache.json"))

    result = run_cert("example.com", timeout=1.0)

    assert result["target"] == "example.com"
    assert result["domain"] == "example.com"
    assert result["ip"] == "93.184.216.34"
    assert result["cert_data"] is not None
    assert result["cert_data"]["count"] == 1
    assert result["subdomains"] == ["www.example.com"]


def test_run_cert_url_target(monkeypatch) -> None:
    mock_data = json.dumps([]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", Path("/nonexistent/cert_cache.json"))

    result = run_cert("https://example.com", timeout=1.0)

    assert result["domain"] == "example.com"
    assert result["ip"] == "93.184.216.34"


def test_run_cert_cached_result(monkeypatch, tmp_path) -> None:
    cached_data = {
        "domain": "example.com",
        "entries": [{"name_value": "cached.example.com"}],
        "count": 1,
        "timestamp": time.time(),
    }
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text(json.dumps({"example.com": cached_data}))

    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", cache_file)

    result = run_cert("example.com", timeout=1.0, use_cache=True)

    assert result["cert_data"]["cached"] is True
    assert "cached.example.com" in result["subdomains"]
    assert any("cache" in note.lower() for note in result["notes"])


def test_run_cert_custom_api_url(monkeypatch) -> None:
    mock_data = json.dumps([]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    called_url = []

    def mock_urlopen_func(req, *args, **kwargs):
        called_url.append(req.full_url)
        return mock_urlopen

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_func)
    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", Path("/nonexistent/cert_cache.json"))

    run_cert("example.com", timeout=1.0, api_url="https://custom.example.com/")

    assert len(called_url) == 1
    assert called_url[0].startswith("https://custom.example.com/")


def test_run_cert_api_fails_offline_fallback(monkeypatch, tmp_path) -> None:
    cached_data = {
        "domain": "example.com",
        "entries": [{"name_value": "cached.example.com"}],
        "count": 1,
        "timestamp": time.time() - 100000,
    }
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text(json.dumps({"example.com": cached_data}))

    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", cache_file)

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = run_cert("example.com", timeout=1.0, use_cache=True, offline_fallback=True)

    assert result["cert_data"]["cached"] is True
    assert result["cert_data"]["offline_fallback"] is True
    assert "cached.example.com" in result["subdomains"]
    assert any("offline fallback" in note.lower() for note in result["notes"])


def test_run_cert_no_cache(monkeypatch) -> None:
    mock_data = json.dumps([]).encode("utf-8")
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = mock_data

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_urlopen)
    monkeypatch.setattr("ethscan.cert._resolve_host", lambda h: "93.184.216.34")
    monkeypatch.setattr("ethscan.cert.CACHE_FILE", Path("/nonexistent/cert_cache.json"))

    result = run_cert("example.com", timeout=1.0, use_cache=False)

    assert result["use_cache"] is False


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_cert_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [{"name_value": "www.example.com"}],
            "count": 1,
            "cached": False,
        },
        "subdomains": ["www.example.com"],
        "notes": [],
    }
    output = format_cert_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["cert_data"]["count"] == 1
    assert parsed["subdomains"] == ["www.example.com"]


def test_format_cert_report_markdown_success() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [{"name_value": "www.example.com"}],
            "count": 1,
            "cached": False,
        },
        "subdomains": ["www.example.com", "api.example.com"],
        "notes": [],
    }
    output = format_cert_report_markdown(data)
    assert "# ethscan Certificate Transparency Report" in output
    assert "example.com" in output
    assert "93.184.216.34" in output
    assert "2" in output
    assert "www.example.com" in output
    assert "api.example.com" in output


def test_format_cert_report_markdown_fail() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [],
            "count": 0,
            "error": "Failed to fetch certificate transparency data",
            "cached": False,
        },
        "subdomains": [],
        "notes": [],
    }
    output = format_cert_report_markdown(data)
    assert "Failed to fetch" in output
    assert "No subdomains discovered" in output


def test_format_cert_report_markdown_no_data() -> None:
    data = {
        "target": "nonexistent.invalid.domain.tld",
        "domain": "nonexistent.invalid.domain.tld",
        "ip": None,
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": None,
        "subdomains": [],
        "notes": ["Could not resolve host"],
    }
    output = format_cert_report_markdown(data)
    assert "nonexistent.invalid.domain.tld" in output
    assert "No subdomains discovered" in output


def test_format_cert_report_markdown_cached() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [],
            "count": 0,
            "cached": True,
        },
        "subdomains": [],
        "notes": ["Result served from cache"],
    }
    output = format_cert_report_markdown(data)
    assert "**Cached:** Yes" in output


def test_format_cert_report_markdown_offline_fallback() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [],
            "count": 0,
            "cached": True,
            "offline_fallback": True,
        },
        "subdomains": [],
        "notes": ["API unavailable; used stale cached data (offline fallback)"],
    }
    output = format_cert_report_markdown(data)
    assert "**Offline Fallback:** Yes" in output


def test_format_cert_report_markdown_with_notes() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "cert_data": {
            "domain": "example.com",
            "entries": [],
            "count": 0,
            "cached": False,
        },
        "subdomains": [],
        "notes": ["Note 1", "Note 2"],
    }
    output = format_cert_report_markdown(data)
    assert "Note 1" in output
    assert "Note 2" in output
