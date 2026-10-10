"""Tests for the ethscan cve module."""

import json
from unittest.mock import patch, MagicMock

from ethscan.cve import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT,
    CACHE_DIR,
    CACHE_FILE,
    CACHE_TTL,
    SEVERITIES,
    _normalize_target,
    _resolve_host,
    _load_cache,
    _save_cache,
    _is_cache_valid,
    _fetch_cve_data,
    _get_cached_or_fetch,
    _parse_cve_response,
    _score_to_severity,
    _parse_banner_product,
    run_cve,
    format_cve_report_json,
    format_cve_report_markdown,
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
    assert _resolve_host("127.0.0.1") == "127.0.0.1"


def test_resolve_host_localhost() -> None:
    assert _resolve_host("localhost") == "127.0.0.1"


def test_resolve_host_invalid() -> None:
    assert _resolve_host("nonexistent.invalid.domain.tld") is None


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------

def test_load_cache_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", tmp_path / "cache.json")
    assert _load_cache() == {}


def test_save_cache_writes(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    _save_cache({"key": {"value": 1}})
    data = json.loads(cache_file.read_text())
    assert data == {"key": {"value": 1}}


def test_is_cache_valid_no_timestamp() -> None:
    assert _is_cache_valid({}) is False


def test_is_cache_valid_fresh() -> None:
    import time
    assert _is_cache_valid({"timestamp": time.time()}) is True


def test_is_cache_valid_expired() -> None:
    import time
    assert _is_cache_valid({"timestamp": time.time() - 100000}, ttl=10) is False


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def test_fetch_cve_data_success(monkeypatch) -> None:
    payload = {"vulnerabilities": []}
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)
    fake_resp.read.return_value = b'{"vulnerabilities": []}'
    monkeypatch.setattr("ethscan.cve.urllib.request.urlopen", lambda *a, **k: fake_resp)
    result = _fetch_cve_data("OpenSSH", "7.2")
    assert result == payload


def test_fetch_cve_data_network_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("boom")
    monkeypatch.setattr("ethscan.cve.urllib.request.urlopen", boom)
    assert _fetch_cve_data("OpenSSH", "7.2") is None


def test_fetch_cve_data_timeout(monkeypatch) -> None:
    def boom(*a, **k):
        raise TimeoutError()
    monkeypatch.setattr("ethscan.cve.urllib.request.urlopen", boom)
    assert _fetch_cve_data("OpenSSH", "7.2") is None


def test_fetch_cve_data_invalid_json(monkeypatch) -> None:
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)
    fake_resp.read.return_value = b'not json'
    monkeypatch.setattr("ethscan.cve.urllib.request.urlopen", lambda *a, **k: fake_resp)
    assert _fetch_cve_data("OpenSSH", "7.2") is None


def test_fetch_cve_data_custom_api_url(monkeypatch) -> None:
    captured = {}
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)
    fake_resp.read.return_value = b'{"vulnerabilities": []}'
    def fake_urlopen(req, *a, **k):
        captured["url"] = req.full_url
        return fake_resp
    monkeypatch.setattr("ethscan.cve.urllib.request.urlopen", fake_urlopen)
    _fetch_cve_data("OpenSSH", "7.2", api_url="https://example.com/cve")
    assert "https://example.com/cve" in captured["url"]


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def test_parse_cve_response_empty() -> None:
    assert _parse_cve_response({"vulnerabilities": []}) == []


def test_parse_cve_response_single() -> None:
    data = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2020-1234",
                    "descriptions": [{"lang": "en", "value": "Test vulnerability"}],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseScore": 7.5}}
                        ]
                    },
                    "published": "2020-01-01T00:00:00.000",
                }
            }
        ]
    }
    result = _parse_cve_response(data)
    assert len(result) == 1
    assert result[0]["id"] == "CVE-2020-1234"
    assert result[0]["severity"] == "high"


def test_parse_cve_response_missing_fields() -> None:
    data = {"vulnerabilities": [{"cve": {"id": "CVE-2020-1"}}]}
    result = _parse_cve_response(data)
    assert len(result) == 1
    assert result[0]["id"] == "CVE-2020-1"
    assert result[0]["severity"] == "unknown"


# ---------------------------------------------------------------------------
# Score to severity
# ---------------------------------------------------------------------------

def test_score_to_severity_critical() -> None:
    assert _score_to_severity(9.5) == "critical"


def test_score_to_severity_high() -> None:
    assert _score_to_severity(7.5) == "high"


def test_score_to_severity_medium() -> None:
    assert _score_to_severity(5.0) == "medium"


def test_score_to_severity_low() -> None:
    assert _score_to_severity(1.0) == "low"


def test_score_to_severity_none() -> None:
    assert _score_to_severity(None) == "unknown"


# ---------------------------------------------------------------------------
# Banner parsing
# ---------------------------------------------------------------------------

def test_parse_banner_openssh() -> None:
    product, version = _parse_banner_product("SSH-2.0-OpenSSH_7.2p2")
    assert product == "OpenSSH"
    assert version == "7.2p2"


def test_parse_banner_vsftpd() -> None:
    product, version = _parse_banner_product("220 vsFTPD 2.3.4")
    assert product == "vsftpd"
    assert version == "2.3.4"


def test_parse_banner_proftpd() -> None:
    product, version = _parse_banner_product("220 ProFTPD 1.3.5")
    assert product == "ProFTPD"
    assert version == "1.3.5"


def test_parse_banner_unknown() -> None:
    product, version = _parse_banner_product("some unknown banner")
    assert product is None
    assert version is None


def test_parse_banner_empty() -> None:
    product, version = _parse_banner_product("")
    assert product is None
    assert version is None


# ---------------------------------------------------------------------------
# Cached or fetch
# ---------------------------------------------------------------------------

def test_get_cached_or_fetch_cache_hit(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    _save_cache({"OpenSSH|7.2": {"product": "OpenSSH", "version": "7.2", "findings": [], "timestamp": __import__("time").time()}})
    result = _get_cached_or_fetch("OpenSSH", "7.2", 1.0, True, True, None)
    assert result["cached"] is True


def test_get_cached_or_fetch_fetch_success(tmp_path, monkeypatch) -> None:
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: {"vulnerabilities": []})
    result = _get_cached_or_fetch("OpenSSH", "7.2", 1.0, True, True, None)
    assert result["cached"] is False
    assert result["findings"] == []


def test_get_cached_or_fetch_failed_no_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", tmp_path / "cache.json")
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)
    result = _get_cached_or_fetch("OpenSSH", "7.2", 1.0, False, False, None)
    assert result["findings"] == []
    assert "error" in result


def test_get_cached_or_fetch_offline_fallback(tmp_path, monkeypatch) -> None:
    import time
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr("ethscan.cve.CACHE_FILE", cache_file)
    _save_cache({"OpenSSH|7.2": {"product": "OpenSSH", "version": "7.2", "findings": [{"id": "CVE-X"}], "timestamp": time.time() - 100000}})
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)
    result = _get_cached_or_fetch("OpenSSH", "7.2", 1.0, True, True, None)
    assert result["offline_fallback"] is True
    assert result["cached"] is True


# ---------------------------------------------------------------------------
# run_cve
# ---------------------------------------------------------------------------

def test_run_cve_no_services(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "127.0.0.1")
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: {"results": []})
    monkeypatch.setattr("ethscan.cve._get_cached_or_fetch", lambda *a, **k: {"findings": []})
    result = run_cve("127.0.0.1")
    assert result["services_checked"] == 0
    assert result["finding_count"] == 0


def test_run_cve_with_services(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "example.com")
    services = {"results": [{"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"}]}
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: services)
    monkeypatch.setattr("ethscan.cve._get_cached_or_fetch", lambda *a, **k: {"findings": [{"id": "CVE-2020-1", "severity": "high"}]})
    result = run_cve("example.com")
    assert result["services_checked"] == 1
    assert result["finding_count"] == 1


def test_run_cve_severity_filter(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "example.com")
    services = {"results": [{"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"}]}
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: services)
    monkeypatch.setattr("ethscan.cve._get_cached_or_fetch", lambda *a, **k: {
        "findings": [
            {"id": "CVE-H", "severity": "high"},
            {"id": "CVE-L", "severity": "low"},
        ]
    })
    result = run_cve("example.com", severity="high")
    assert result["finding_count"] == 1
    assert result["findings"][0]["id"] == "CVE-H"


def test_run_cve_url_target(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "example.com")
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: {"results": []})
    monkeypatch.setattr("ethscan.cve._get_cached_or_fetch", lambda *a, **k: {"findings": []})
    result = run_cve("https://example.com")
    assert result["host"] == "example.com"


def test_run_cve_skip_unparseable_banner(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "example.com")
    services = {"results": [{"port": 80, "banner": "HTTP/1.0 200 OK"}]}
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: services)
    monkeypatch.setattr("ethscan.cve._get_cached_or_fetch", lambda *a, **k: {"findings": []})
    result = run_cve("example.com")
    assert result["services_checked"] == 0


def test_run_cve_custom_api_url(monkeypatch) -> None:
    captured = {}
    def fake_fetch(product, version, timeout, api_url=None):
        captured["api_url"] = api_url
        return {"vulnerabilities": []}
    monkeypatch.setattr("ethscan.cve._normalize_target", lambda t: "example.com")
    monkeypatch.setattr("ethscan.cve.run_service", lambda *a, **k: {"results": [{"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"}]})
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", fake_fetch)
    run_cve("example.com", api_url="https://custom.cve.api/")
    assert captured["api_url"] == "https://custom.cve.api/"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def test_format_cve_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_queries": [],
        "findings": [{"id": "CVE-2020-1", "product": "OpenSSH", "version": "7.2", "port": 22, "severity": "high", "title": "Test"}],
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_json(data)
    parsed = json.loads(output)
    assert parsed["finding_count"] == 1


def test_format_cve_report_json_empty() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 0,
        "cve_queries": [],
        "findings": [],
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["No service banners with parseable product/version detected"],
    }
    output = format_cve_report_json(data)
    parsed = json.loads(output)
    assert parsed["finding_count"] == 0


def test_format_cve_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_queries": [],
        "findings": [{"id": "CVE-2020-1", "product": "OpenSSH", "version": "7.2", "port": 22, "severity": "high", "title": "Test vuln"}],
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "ethscan CVE Lookup Report" in output
    assert "CVE-2020-1" in output
    assert "OpenSSH" in output
    assert "HIGH" in output


def test_format_cve_report_markdown_empty() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 0,
        "cve_queries": [],
        "findings": [],
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["No known CVEs matched"],
    }
    output = format_cve_report_markdown(data)
    assert "No known CVEs matched" in output


def test_format_cve_report_markdown_pipe_escape() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 1,
        "cve_queries": [],
        "findings": [{"id": "CVE-2020-1", "product": "A|B", "version": "1.0", "port": 22, "severity": "high", "title": "Test"}],
        "finding_count": 1,
        "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
        "notes": [],
    }
    output = format_cve_report_markdown(data)
    assert "A\\|B" in output


def test_format_cve_report_markdown_notes() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 10.0,
        "use_cache": True,
        "offline_fallback": True,
        "api_url": None,
        "severity_filter": None,
        "services_checked": 0,
        "cve_queries": [],
        "findings": [],
        "finding_count": 0,
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "notes": ["Note one", "Note two"],
    }
    output = format_cve_report_markdown(data)
    assert "## Notes" in output
    assert "Note one" in output
    assert "Note two" in output
