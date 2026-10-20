"""Tests for the ethscan fuzz module."""

import csv
import io
import threading
from unittest.mock import patch

from ethscan.fuzz import (
    DEFAULT_WORDLIST,
    _join_url,
    _normalize_base_url,
    format_fuzz_report_csv,
    format_fuzz_report_json,
    format_fuzz_report_markdown,
    fuzz_path,
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


def test_fuzz_path_reports_a_path_with_a_space_as_a_failed_probe() -> None:
    """A path that ``http.client`` refuses is a failed probe, not a crash.

    ``http.client.InvalidURL`` derives from ``HTTPException`` and not from
    ``ValueError``, so it used to escape the ``except`` of ``fuzz_path``.
    """
    result = fuzz_path("http://127.0.0.1", "/a b", timeout=1.0)
    assert result["status_code"] is None
    assert result["error"]
    assert result["path"] == "/a b"


def test_fuzz_path_reports_a_path_with_a_null_byte_as_a_failed_probe() -> None:
    result = fuzz_path("http://127.0.0.1", "/a\x00b", timeout=1.0)
    assert result["status_code"] is None
    assert result["error"]


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

def test_format_fuzz_report_csv() -> None:
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
    output = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "base_url", "path", "status_code", "error", "is_finding"]
    assert reader[1] == ["https://example.com", "https://example.com", "/admin", "200", "", "true"]
    assert reader[2] == ["https://example.com", "https://example.com", "/login", "404", "", "false"]


def test_format_fuzz_report_csv_empty() -> None:
    data = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 0,
        "findings": [],
        "all_results": [],
    }
    output = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0] == ["target", "base_url", "path", "status_code", "error", "is_finding"]


def test_format_fuzz_report_csv_error_escaping() -> None:
    data = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 1,
        "findings": [],
        "all_results": [
            {"path": "/a,b", "status_code": None, "error": 'connection "refused"'},
        ],
    }
    output = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][2] == "/a,b"
    assert reader[1][4] == 'connection "refused"'
    assert reader[1][3] == ""
    assert reader[1][5] == "false"


def test_run_fuzz_workers_single() -> None:
    """Test run_fuzz with default single worker."""
    results = run_fuzz("http://nonexistent.invalid.domain.tld", wordlist=["/admin", "/login", "/test"], timeout=1.0, workers=1)
    assert results["paths_tested"] == 3
    assert len(results["all_results"]) == 3
    # Results should be in original order
    paths = [r["path"] for r in results["all_results"]]
    assert paths == ["/admin", "/login", "/test"]


def test_run_fuzz_workers_multiple() -> None:
    """Test run_fuzz with multiple workers."""
    results = run_fuzz("http://nonexistent.invalid.domain.tld", wordlist=["/admin", "/login", "/test"], timeout=1.0, workers=3)
    assert results["paths_tested"] == 3
    assert len(results["all_results"]) == 3
    # Results should be in original order despite concurrent execution
    paths = [r["path"] for r in results["all_results"]]
    assert paths == ["/admin", "/login", "/test"]


def test_run_fuzz_workers_maintains_order() -> None:
    """Test that results maintain original path order regardless of completion order."""
    # Use a larger wordlist to increase chance of out-of-order completion
    paths = [f"/path{i}" for i in range(20)]
    results = run_fuzz("http://nonexistent.invalid.domain.tld", wordlist=paths, timeout=1.0, workers=10)
    assert results["paths_tested"] == 20
    assert len(results["all_results"]) == 20
    result_paths = [r["path"] for r in results["all_results"]]
    assert result_paths == paths  # Order preserved


def test_run_fuzz_workers_zero_defaults_to_one(monkeypatch) -> None:
    """Test that workers=0 is treated as 1 (no concurrency)."""
    # Mock fuzz_path to track calls
    call_count = {"count": 0}

    def mock_fuzz_path(base_url, path, timeout):
        call_count["count"] += 1
        return {"path": path, "status_code": 404, "error": None}

    with patch("ethscan.fuzz.fuzz_path", side_effect=mock_fuzz_path):
        run_fuzz("https://example.com", wordlist=["/a", "/b"], workers=0)

    # Should still process all paths (sequentially)
    assert call_count["count"] == 2


def test_run_fuzz_workers_negative_defaults_to_one(monkeypatch) -> None:
    """Test that negative workers is treated as 1."""
    call_count = {"count": 0}

    def mock_fuzz_path(base_url, path, timeout):
        call_count["count"] += 1
        return {"path": path, "status_code": 404, "error": None}

    with patch("ethscan.fuzz.fuzz_path", side_effect=mock_fuzz_path):
        run_fuzz("https://example.com", wordlist=["/a", "/b"], workers=-5)

    assert call_count["count"] == 2


def test_run_fuzz_workers_actually_concurrent() -> None:
    """Test that workers>1 dispatches fuzz_path calls to multiple threads."""
    seen_threads = []

    def mock_fuzz_path(base_url, path, timeout):
        seen_threads.append(threading.get_ident())
        return {"path": path, "status_code": 404, "error": None}

    with patch("ethscan.fuzz.fuzz_path", side_effect=mock_fuzz_path):
        run_fuzz("https://example.com", wordlist=[f"/p{i}" for i in range(10)], workers=4)

    # With >1 worker the ThreadPoolExecutor must exercise more than one thread.
    assert len(set(seen_threads)) >= 2


def test_run_fuzz_workers_single_is_sequential(monkeypatch) -> None:
    """Test that workers<=1 executes fuzz_path on a single thread (no pool)."""
    seen_threads = []

    def mock_fuzz_path(base_url, path, timeout):
        seen_threads.append(threading.get_ident())
        return {"path": path, "status_code": 404, "error": None}

    with patch("ethscan.fuzz.fuzz_path", side_effect=mock_fuzz_path):
        run_fuzz("https://example.com", wordlist=[f"/p{i}" for i in range(5)], workers=1)

    # Sequential branch must use exactly one thread.
    assert len(set(seen_threads)) == 1


def test_fuzz_path_success(monkeypatch) -> None:
    class _FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "ethscan.fuzz.urllib.request.urlopen",
        lambda request, timeout=None: _FakeResp(),
    )
    result = fuzz_path("https://example.com", "/admin", timeout=1.0)
    assert result == {"path": "/admin", "status_code": 200, "error": None}
