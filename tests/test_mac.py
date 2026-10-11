"""Tests for the ethscan mac module."""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from ethscan.mac import (
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
    _fetch_mac_data,
    _get_cached_or_fetch,
    _extract_oui,
    _is_mac_address,
    run_mac,
    format_mac_report_json,
    format_mac_report_markdown,
)


# ---------------------------------------------------------------------------
# Target normalization
# ---------------------------------------------------------------------------


def test_normalize_target_bare_mac() -> None:
    assert _normalize_target("00:1A:2B:3C:4D:5E") == "00:1a:2b:3c:4d:5e"


def test_normalize_target_dashes() -> None:
    assert _normalize_target("00-1A:2B-3C:4D-5E") == "00-1a:2b-3c:4d-5e"


def test_normalize_target_strips_whitespace() -> None:
    assert _normalize_target("  00:1A:2B:3C:4D:5E  ") == "00:1a:2b:3c:4d:5e"


def test_normalize_target_url() -> None:
    result = _normalize_target("https://example.com/path")
    assert result == "example.com"


def test_normalize_target_hostname() -> None:
    assert _normalize_target("example.com") == "example.com"


def test_normalize_target_ip() -> None:
    assert _normalize_target("8.8.8.8") == "8.8.8.8"


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
    with patch("ethscan.mac.CACHE_FILE", Path("/nonexistent/path/mac_cache.json")):
        result = _load_cache()
        assert result == {}


def test_load_cache_invalid_json(tmp_path) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text("not valid json")
    with patch("ethscan.mac.CACHE_FILE", cache_file):
        result = _load_cache()
        assert result == {}


def test_load_cache_valid(tmp_path) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text('{"00:1a:2b:3c:4d:5e": {"vendor": "Cisco"}}')
    with patch("ethscan.mac.CACHE_FILE", cache_file):
        result = _load_cache()
        assert "00:1a:2b:3c:4d:5e" in result
        assert result["00:1a:2b:3c:4d:5e"]["vendor"] == "Cisco"


def test_load_cache_non_dict(tmp_path) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text('["not", "a", "dict"]')
    with patch("ethscan.mac.CACHE_FILE", cache_file):
        result = _load_cache()
        assert result == {}


def test_save_cache(tmp_path) -> None:
    cache_file = tmp_path / "mac_cache.json"
    with patch("ethscan.mac.CACHE_DIR", tmp_path):
        with patch("ethscan.mac.CACHE_FILE", cache_file):
            _save_cache({"00:1a:2b:3c:4d:5e": {"vendor": "Cisco"}})
            assert cache_file.exists()
            data = json.loads(cache_file.read_text())
            assert data["00:1a:2b:3c:4d:5e"]["vendor"] == "Cisco"





def test_is_cache_valid() -> None:
    entry = {"timestamp": time.time()}
    assert _is_cache_valid(entry, ttl=60) is True


def test_is_cache_valid_expired() -> None:
    entry = {"timestamp": time.time() - 100}
    assert _is_cache_valid(entry, ttl=60) is False


def test_is_cache_valid_missing_timestamp() -> None:
    entry = {"vendor": "Cisco"}
    assert _is_cache_valid(entry, ttl=60) is False


# ---------------------------------------------------------------------------
# _fetch_mac_data
# ---------------------------------------------------------------------------


def test_fetch_mac_data_success() -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _fetch_mac_data("00:1a:2b:3c:4d:5e", timeout=1.0)

    assert result is not None
    assert result["mac"] == "00:1a:2b:3c:4d:5e"
    assert result["vendor"] == "Cisco Systems"
    assert "timestamp" in result


def test_fetch_mac_data_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = _fetch_mac_data("00:1a:2b:3c:4d:5e", timeout=1.0)
        assert result is None


def test_fetch_mac_data_timeout() -> None:
    import socket

    with patch("urllib.request.urlopen", side_effect=socket.timeout()):
        result = _fetch_mac_data("00:1a:2b:3c:4d:5e", timeout=1.0)
        assert result is None


def test_fetch_mac_data_url_error() -> None:
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("404")):
        result = _fetch_mac_data("00:1a:2b:3c:4d:5e", timeout=1.0)
        assert result is None


def test_fetch_mac_data_custom_api_url() -> None:
    called_urls = []
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Custom Vendor"

    def mock_urlopen_func(req, *args, **kwargs):
        called_urls.append(req.full_url)
        return mock_urlopen

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_func):
        result = _fetch_mac_data(
            "00:1a:2b:3c:4d:5e",
            timeout=1.0,
            api_url="https://custom-api.example.com",
        )

    assert result is not None
    assert result["vendor"] == "Custom Vendor"
    assert len(called_urls) == 1
    assert called_urls[0].startswith("https://custom-api.example.com/")


# ---------------------------------------------------------------------------
# _get_cached_or_fetch
# ---------------------------------------------------------------------------


def test_get_cached_or_fetch_cache_hit(tmp_path) -> None:
    cached_data = {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Cisco",
        "timestamp": time.time(),
    }
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text(json.dumps({"00:1a:2b:3c:4d:5e": cached_data}))

    with patch("ethscan.mac.CACHE_FILE", cache_file):
        result = _get_cached_or_fetch(
            "00:1a:2b:3c:4d:5e", 1.0, use_cache=True, offline_fallback=False, api_url=None
        )

    assert result["cached"] is True
    assert result["vendor"] == "Cisco"


def test_get_cached_or_fetch_cache_miss_fetches() -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        with patch("ethscan.mac.CACHE_FILE", Path("/nonexistent/cache.json")):
            result = _get_cached_or_fetch(
                "00:1a:2b:3c:4d:5e", 1.0, use_cache=True, offline_fallback=False, api_url=None
            )

    assert result["cached"] is False
    assert result["vendor"] == "Cisco Systems"


def test_get_cached_or_fetch_fetch_fails_no_cache(tmp_path) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text("{}")

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.mac.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch(
                "00:1a:2b:3c:4d:5e", 1.0, use_cache=True, offline_fallback=False, api_url=None
            )

    assert result["cached"] is False
    assert result["vendor"] is None
    assert "error" in result


def test_get_cached_or_fetch_fetch_fails_offline_fallback(tmp_path) -> None:
    cached_data = {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Cisco",
        "timestamp": time.time() - 100000,
    }
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text(json.dumps({"00:1a:2b:3c:4d:5e": cached_data}))

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        with patch("ethscan.mac.CACHE_FILE", cache_file):
            result = _get_cached_or_fetch(
                "00:1a:2b:3c:4d:5e", 1.0, use_cache=True, offline_fallback=True, api_url=None
            )

    assert result["cached"] is True
    assert result["offline_fallback"] is True
    assert result["vendor"] == "Cisco"


def test_get_cached_or_fetch_no_cache_disabled() -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        result = _get_cached_or_fetch(
            "00:1a:2b:3c:4d:5e", 1.0, use_cache=False, offline_fallback=False, api_url=None
        )

    assert result["cached"] is False
    assert result["vendor"] == "Cisco Systems"


def test_get_cached_or_fetch_no_cache_disabled_fetch_fails() -> None:
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = _get_cached_or_fetch(
            "00:1a:2b:3c:4d:5e", 1.0, use_cache=False, offline_fallback=True, api_url=None
        )

    assert result["cached"] is False
    assert result["vendor"] is None
    assert "error" in result


# ---------------------------------------------------------------------------
# _extract_oui / _is_mac_address
# ---------------------------------------------------------------------------


def test_extract_oui_colon_format() -> None:
    assert _extract_oui("00:1A:2B:3C:4D:5e") == "001a2b3c"


def test_extract_oui_dash_format() -> None:
    assert _extract_oui("00-1A-2B-3C-4D-5E") == "001a2b3c"


def test_extract_oui_dot_format() -> None:
    assert _extract_oui("001A.2B3C.4D5E") == "001a2b3c"


def test_extract_oui_plain() -> None:
    assert _extract_oui("001A2B3C4D5E") == "001a2b3c"


def test_is_mac_address_true() -> None:
    assert _is_mac_address("00:1A:2B:3C:4D:5E") is True


def test_is_mac_address_dashes() -> None:
    assert _is_mac_address("00-1A-2B-3C-4D-5E") is True


def test_is_mac_address_plain() -> None:
    assert _is_mac_address("001A2B3C4D5E") is True


def test_is_mac_address_false_short() -> None:
    assert _is_mac_address("00:1A:2B") is False


def test_is_mac_address_false_non_hex() -> None:
    assert _is_mac_address("GG:1A:2B:3C:4D:5E") is False


def test_is_mac_address_false_hostname() -> None:
    assert _is_mac_address("example.com") is False


# ---------------------------------------------------------------------------
# run_mac
# ---------------------------------------------------------------------------


def test_run_mac_offline_target(monkeypatch) -> None:
    mock_data = {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Cisco Systems",
        "timestamp": time.time(),
    }
    cache_file = Path("/nonexistent/cache.json")

    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: "00:1a:2b:3c:4d:5e")
    monkeypatch.setattr("ethscan.mac._get_cached_or_fetch",
                        lambda *a, **kw: {"mac": "00:1a:2b", "vendor": "Cisco", "cached": False})
    monkeypatch.setattr("ethscan.mac.CACHE_FILE", cache_file)

    result = run_mac("00:1A:2B:3C:4D:5E", timeout=1.0)

    assert result["target"] == "00:1A:2B:3C:4D:5E"
    assert result["mac"] == "00:1a:2b:3c:4d:5e"
    assert result["oui"] == "001a2b3c"
    assert result["timeout"] == 1.0
    assert result["use_cache"] is True
    assert result["offline_fallback"] is True
    assert result["mac_data"]["vendor"] == "Cisco"


def test_run_mac_hostname_unresolvable(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: None)

    result = run_mac("nonexistent.invalid.domain.tld", timeout=1.0, use_cache=False)

    assert result["target"] == "nonexistent.invalid.domain.tld"
    assert result["mac"] is None
    assert result["oui"] is None
    assert result["mac_data"] is None
    assert any("Could not resolve" in note for note in result["notes"])


def test_run_mac_success(monkeypatch) -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: mock_urlopen)
    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: "00:1a:2b:3c:4d:5e")
    monkeypatch.setattr("ethscan.mac.CACHE_FILE", Path("/nonexistent/cache.json"))

    result = run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=False, offline_fallback=False)

    assert result["target"] == "00:1A:2B:3C:4D:5E"
    assert result["mac"] == "00:1a:2b:3c:4d:5e"
    assert result["oui"] == "001a2b3c"
    assert result["mac_data"]["vendor"] == "Cisco Systems"
    assert result["mac_data"]["cached"] is False
    assert result["use_cache"] is False


def test_run_mac_url_target(monkeypatch) -> None:
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"
    called_url = []

    def mock_urlopen_func(req, *args, **kwargs):
        called_url.append(req.full_url)
        return mock_urlopen

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_func)
    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: "00:1a:2b:3c:4d:5e")
    monkeypatch.setattr("ethscan.mac.CACHE_FILE", Path("/nonexistent/cache.json"))

    result = run_mac(
        "https://example.com/00:1A:2B:3C:4D:5E",
        timeout=1.0,
        api_url="https://custom.example.com",
    )

    assert result["target"] == "https://example.com/00:1A:2B:3C:4D:5E"
    assert result["mac"] == "00:1a:2b:3c:4d:5e"
    assert result["oui"] == "001a2b3c"
    assert len(called_url) == 1
    assert called_url[0].startswith("https://custom.example.com/")


def test_run_mac_cached_result(monkeypatch, tmp_path) -> None:
    cached_data = {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Cisco",
        "timestamp": time.time(),
    }
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text(json.dumps({"00:1a:2b:3c:4d:5e": cached_data}))

    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: "00:1a:2b:3c:4d:5e")
    monkeypatch.setattr("ethscan.mac.CACHE_FILE", cache_file)

    result = run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=True)

    assert result["mac_data"]["cached"] is True
    assert any("cache" in note.lower() for note in result["notes"])


def test_run_mac_custom_api_url(monkeypatch) -> None:
    called_urls = []
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value.read.return_value = b"Cisco Systems"

    def mock_urlopen_func(req, *args, **kwargs):
        called_urls.append(req.full_url)
        return mock_urlopen

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_func)
    monkeypatch.setattr("ethscan.mac._resolve_host", lambda h: "00:1a:2b:3c:4d:5e")
    monkeypatch.setattr("ethscan.mac.CACHE_FILE", Path("/nonexistent/cache.json"))

    run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=False, api_url="https://custom.example.com")

    assert len(called_urls) == 1
    assert called_urls[0].startswith("https://custom.example.com/")


def test_run_mac_offline_fallback_note(monkeypatch, tmp_path) -> None:
    cached_data = {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Cisco",
        "timestamp": time.time() - 100000,
    }
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text(json.dumps({"00:1a:2b:3c:4d:5e": cached_data}))

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        monkeypatch.setattr("ethscan.mac.CACHE_FILE", cache_file)

        result = run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=True, offline_fallback=True)

    assert result["mac_data"]["cached"] is True
    assert result["mac_data"]["offline_fallback"] is True
    assert any("offline fallback" in note.lower() for note in result["notes"])


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_mac_report_json() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Cisco Systems",
            "cached": False,
        },
        "notes": [],
    }
    output = format_mac_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "00:1A:2B:3C:4D:5E"
    assert parsed["mac_data"]["vendor"] == "Cisco Systems"


def test_format_mac_report_markdown_success() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Cisco Systems",
            "cached": False,
        },
        "notes": [],
    }
    output = format_mac_report_markdown(data)
    assert "# ethscan MAC Vendor Lookup Report" in output
    assert "00:1a:2b:3c:4d:5e" in output
    assert "Cisco Systems" in output
    assert "001a2b3c" in output


def test_format_mac_report_markdown_offline_target() -> None:
    data = {
        "target": "nonexistent.invalid.domain.tld",
        "mac": None,
        "oui": None,
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": None,
        "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld' to a MAC address"],
    }
    output = format_mac_report_markdown(data)
    assert "# ethscan MAC Vendor Lookup Report" in output
    assert "No MAC vendor data available" in output
    assert "Could not resolve" in output


def test_format_mac_report_markdown_cached() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Cisco",
            "cached": True,
        },
        "notes": ["Result served from cache"],
    }
    output = format_mac_report_markdown(data)
    assert "**Cached:** Yes" in output


def test_format_mac_report_markdown_offline_fallback() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Cisco",
            "cached": True,
            "offline_fallback": True,
        },
        "notes": ["API unavailable; used stale cached data (offline fallback)"],
    }
    output = format_mac_report_markdown(data)
    assert "**Offline Fallback:** Yes" in output


def test_format_mac_report_markdown_error() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": False,
        "offline_fallback": False,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": None,
            "error": "Failed to fetch MAC vendor data",
            "cached": False,
        },
        "notes": [],
    }
    output = format_mac_report_markdown(data)
    assert "**Error:**" in output
    assert "Failed to fetch MAC vendor data" in output


def test_format_mac_report_markdown_with_notes() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Cisco",
            "cached": False,
        },
        "notes": ["Note 1", "Note 2"],
    }
    output = format_mac_report_markdown(data)
    assert "Note 1" in output
    assert "Note 2" in output


def test_format_mac_report_markdown_empty_vendor() -> None:
    data = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": None,
            "cached": False,
        },
        "notes": [],
    }
    output = format_mac_report_markdown(data)
    assert "No MAC vendor data available" not in output or "*No MAC vendor data" not in output
    assert "MAC Vendor Data" in output
