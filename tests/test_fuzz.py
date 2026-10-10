"""Tests for the ethscan fuzz module."""

import pytest

from ethscan.fuzz import (
    DEFAULT_WORDLIST,
    _join_url,
    _normalize_base_url,
    format_fuzz_report_json,
    format_fuzz_report_markdown,
    load_wordlist,
    run_fuzz,
)


def test_normalize_base_url_https() -> None:
    base = _normalize_base_url("https://example.com")
    assert base == "https://example.com"


def test_normalize_base_url_http() -> None:
    base = _normalize_base_url("http://example.com")
    assert base == "http://example.com"


def test_normalize_base_url_with_port() -> None:
    base = _normalize_base_url("https://example.com:8443")
    assert base == "https://example.com:8443"


def test_normalize_base_url_bare_host() -> None:
    base = _normalize_base_url("example.com")
    assert base == "https://example.com"


def test_join_url_basic() -> None:
    url = _join_url("https://example.com", "/admin")
    assert url == "https://example.com/admin"


def test_join_url_no_leading_slash() -> None:
    url = _join_url("https://example.com", "admin")
    assert url == "https://example.com/admin"


def test_join_url_base_trailing_slash() -> None:
    url = _join_url("https://example.com/", "/admin")
    assert url == "https://example.com/admin"


def test_load_wordlist(tmp_path) -> None:
    wordlist_file = tmp_path / "wordlist.txt"
    wordlist_file.write_text("/admin\n/login\n\n# comment\n/test\n")
    paths = load_wordlist(str(wordlist_file))
    assert paths == ["/admin", "/login", "/test"]


def test_load_wordlist_skips_empty_and_comments(tmp_path) -> None:
    wordlist_file = tmp_path / "wordlist.txt"
    wordlist_file.write_text("\n\n# comment\n# another\n")
    paths = load_wordlist(str(wordlist_file))
    assert paths == []


def test_default_wordlist_not_empty() -> None:
    assert len(DEFAULT_WORDLIST) > 0
    assert "/admin" in DEFAULT_WORDLIST
    assert "/login" in DEFAULT_WORDLIST


def test_run_fuzz_offline_target() -> None:
    # Should not raise; returns structured results even on failure.
    results = run_fuzz("http://nonexistent.invalid.domain.tld", wordlist=["/admin", "/login"], timeout=1.0)
    assert results["target"].startswith("http://")
    assert results["base_url"] == "http://nonexistent.invalid.domain.tld"
    assert results["paths_tested"] == 2
    assert "findings" in results
    assert "all_results" in results
    assert len(results["all_results"]) == 2


def test_format_fuzz_report_json() -> None:
    data = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 2,
        "findings": [{"path": "/admin", "status_code": 200, "error": None}],
        "all_results": [
            {"path": "/admin", "status_code": 200, "error": None},
            {"path": "/login", "status_code": 404, "error": None},
        ],
    }
    output = format_fuzz_report_json(data)
    assert "example.com" in output
    assert "findings" in output
    assert "admin" in output


def test_format_fuzz_report_markdown() -> None:
    data = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 2,
        "findings": [{"path": "/admin", "status_code": 200, "error": None}],
        "all_results": [
            {"path": "/admin", "status_code": 200, "error": None},
            {"path": "/login", "status_code": 404, "error": None},
        ],
    }
    output = format_fuzz_report_markdown(data)
    assert "# ethscan HTTP Fuzz Report" in output
    assert "example.com" in output
    assert "## Findings" in output
    assert "## All Results" in output
    assert "/admin" in output
    assert "200" in output


def test_format_fuzz_report_markdown_no_findings() -> None:
    data = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 1,
        "findings": [],
        "all_results": [{"path": "/admin", "status_code": 404, "error": None}],
    }
    output = format_fuzz_report_markdown(data)
    assert "# ethscan HTTP Fuzz Report" in output
    assert "Findings (non-404): 0" in output or "Findings (non-404):** 0" in output
    assert "## Findings" not in output  # No findings section when empty
    assert "## All Results" in output