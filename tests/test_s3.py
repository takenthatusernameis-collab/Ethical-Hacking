"""Tests for the ethscan s3 module."""
from __future__ import annotations

import http.client
import json
import socket
import urllib.error

from ethscan.s3 import (
    DEFAULT_BUCKET_NAMES,
    DEFAULT_REGION,
    DEFAULT_TIMEOUT,
    S3_REGIONS,
    _bucket_name_problem,
    _build_bucket_candidates,
    _build_s3_url,
    _normalize_target,
    _resolve_s3_endpoint,
    check_bucket_public,
    format_s3_report_csv,
    format_s3_report_json,
    format_s3_report_markdown,
    run_s3,
)

# ---------------------------------------------------------------------------
# Fake HTTP response helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status: int, body: bytes = b"<?xml>contents</xml>"):
        self._status = status
        self._body = body

    def getcode(self) -> int:
        return self._status

    def read(self, n: int | None = -1) -> bytes:
        if n is None or n < 0:
            return self._body
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _mock_dns(resolved: str | None = "1.2.3.4"):
    return lambda bucket_name, region, timeout=5.0: resolved


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_domain() -> None:
    assert _normalize_target("example.com") == "example.com"


def test_normalize_target_uppercase() -> None:
    assert _normalize_target("Example.COM") == "example.com"


def test_normalize_target_https_url() -> None:
    assert _normalize_target("https://example.com/path") == "example.com"


def test_normalize_target_http_url_with_port() -> None:
    assert _normalize_target("http://example.com:8080/path") == "example.com"


def test_normalize_target_strips_whitespace() -> None:
    assert _normalize_target("  example.com  ") == "example.com"


def test_normalize_target_empty() -> None:
    assert _normalize_target("") == ""


def test_normalize_target_ipv6_url() -> None:
    assert _normalize_target("https://[::1]/path") == "::1"
    assert _normalize_target("http://[fd00::1]:8443/path") == "fd00::1"


# ---------------------------------------------------------------------------
# _build_s3_url
# ---------------------------------------------------------------------------


def test_build_s3_url_us_east_1() -> None:
    assert _build_s3_url("mybucket", "us-east-1") == "https://mybucket.s3.amazonaws.com/"


def test_build_s3_url_other_region() -> None:
    assert (
        _build_s3_url("mybucket", "eu-west-1")
        == "https://mybucket.s3.eu-west-1.amazonaws.com/"
    )


def test_build_s3_url_empty_region() -> None:
    assert _build_s3_url("mybucket", "") == "https://mybucket.s3.amazonaws.com/"


# ---------------------------------------------------------------------------
# _build_bucket_candidates
# ---------------------------------------------------------------------------


def test_build_candidates_basic() -> None:
    candidates = _build_bucket_candidates("example.com")
    assert "example-com" in candidates
    assert "example" in candidates
    assert "example.com" in candidates
    assert len(candidates) > 3


def test_build_candidates_strips_www() -> None:
    candidates = _build_bucket_candidates("www.example.com")
    assert "example-com" in candidates
    assert candidates[0] == "example-com"


def test_build_candidates_dedup_case_insensitive() -> None:
    candidates = _build_bucket_candidates("example.com", wordlist=["example-com"])
    lower = [c.lower() for c in candidates]
    assert lower.count("example-com") == 1


def test_build_candidates_with_wordlist() -> None:
    candidates = _build_bucket_candidates("example.com", wordlist=["backups", "dev"])
    assert "backups" in candidates
    assert "backups-example-com" in candidates
    assert "example-com-backups" in candidates


def test_build_candidates_wordlist_strips_empty() -> None:
    candidates = _build_bucket_candidates("example.com", wordlist=["", "  ", "dev"])
    assert candidates == _build_bucket_candidates("example.com", wordlist=["dev"])


def test_build_candidates_empty_target() -> None:
    assert _build_bucket_candidates("", None) == []


def test_build_candidates_default_names_present() -> None:
    candidates = _build_bucket_candidates("example.com")
    for word in DEFAULT_BUCKET_NAMES:
        assert f"example-com-{word}" in candidates


# ---------------------------------------------------------------------------
# _resolve_s3_endpoint
# ---------------------------------------------------------------------------


def test_resolve_s3_endpoint_success(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3.socket.gethostbyname", lambda host: "9.9.9.9")
    result = _resolve_s3_endpoint("mybucket", "us-east-1", timeout=1.0)
    assert result == "9.9.9.9"


def test_resolve_s3_endpoint_failure(monkeypatch) -> None:
    def _raise(host):
        raise socket.gaierror("resolution failed")

    monkeypatch.setattr("ethscan.s3.socket.gethostbyname", _raise)
    result = _resolve_s3_endpoint("mybucket", "us-east-1", timeout=1.0)
    assert result is None


# ---------------------------------------------------------------------------
# _bucket_name_problem
# ---------------------------------------------------------------------------


def test_bucket_name_problem_accepts_valid_names() -> None:
    assert _bucket_name_problem("mybucket") is None
    assert _bucket_name_problem("example-com") is None
    assert _bucket_name_problem("example.com") is None
    assert _bucket_name_problem("a1-b2") is None
    assert _bucket_name_problem("ab1") is None


def test_bucket_name_problem_rejects_invalid_names() -> None:
    assert _bucket_name_problem("ab") is not None
    assert _bucket_name_problem("a" * 64) is not None
    assert _bucket_name_problem("MyBucket") is not None
    assert _bucket_name_problem("::1") is not None
    assert _bucket_name_problem("fd00::1") is not None
    assert _bucket_name_problem("my_bucket") is not None
    assert _bucket_name_problem("-bucket") is not None
    assert _bucket_name_problem("bucket-") is not None
    assert _bucket_name_problem("my..bucket") is not None
    assert _bucket_name_problem("192.168.5.4") is not None


# ---------------------------------------------------------------------------
# check_bucket_public
# ---------------------------------------------------------------------------


def test_check_bucket_public_200(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))
    monkeypatch.setattr(
        "ethscan.s3.urllib.request.urlopen",
        lambda req, timeout=None: _FakeResponse(200),
    )
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["bucket"] == "mybucket"
    assert result["region"] == "us-east-1"
    assert result["dns_resolved"] == "1.2.3.4"
    assert result["status_code"] == 200
    assert result["exists"] is True
    assert result["public"] is True
    assert result["error"] is None


def test_check_bucket_public_403(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req, timeout=None):
        raise urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 403
    assert result["exists"] is True
    assert result["public"] is False


def test_check_bucket_public_404(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req, timeout=None):
        raise urllib.error.HTTPError("https://x", 404, "Not Found", {}, None)

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 404
    assert result["exists"] is False
    assert result["public"] is False


def test_check_bucket_public_400(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req, timeout=None):
        raise urllib.error.HTTPError("https://x", 400, "Bad Request", {}, None)

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 400
    assert result["exists"] is False
    assert result["error"] == "Invalid bucket name or request"


def test_check_bucket_public_url_error(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns(None))

    def _raise(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["exists"] is False
    assert result["public"] is False
    assert result["error"] is not None


def test_check_bucket_public_timeout(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req, timeout=None):
        raise socket.timeout("timed out")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["exists"] is False
    assert result["public"] is False
    assert result["error"] is not None


def test_check_bucket_public_transport_failure(monkeypatch) -> None:
    # A transport failure of a type the guard does not name is a failed
    # probe, not a crash.
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    def _raise(req, timeout=None):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["exists"] is False
    assert result["public"] is False
    assert "hostile transport" in result["error"]


def test_check_bucket_public_url_and_region_fields(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns(None))
    monkeypatch.setattr(
        "ethscan.s3.urllib.request.urlopen",
        lambda req, timeout=None: _FakeResponse(200),
    )
    result = check_bucket_public("mybucket", "eu-west-1", 1.0)
    assert result["url"] == "https://mybucket.s3.eu-west-1.amazonaws.com/"
    assert result["region"] == "eu-west-1"


def test_check_bucket_public_invalid_bucket_name_is_not_requested(monkeypatch) -> None:
    """A name that cannot be an S3 bucket name is reported, not requested."""

    def _no_request(*args, **kwargs):
        raise AssertionError("no request may be sent for an invalid name")

    def _no_dns(*args, **kwargs):
        raise AssertionError("no DNS lookup may be sent for an invalid name")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _no_request)
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _no_dns)

    result = check_bucket_public("::1", "us-east-1", 1.0)
    assert result["error"] == (
        "Invalid bucket name: contains characters that are not allowed "
        "in a bucket name"
    )
    assert result["dns_resolved"] is None
    assert result["status_code"] is None
    assert result["exists"] is False
    assert result["public"] is False
    assert result["url"] == "https://::1.s3.amazonaws.com/"


def test_check_bucket_public_invalid_url_is_reported(monkeypatch) -> None:
    """``http.client.InvalidURL`` is a probe failure, not a crash."""
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns(None))

    def _raise(req, timeout=None):
        raise http.client.InvalidURL("nonnumeric port: '1.s3.amazonaws.com'")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["error"] == "nonnumeric port: '1.s3.amazonaws.com'"
    assert result["status_code"] is None
    assert result["exists"] is False
    assert result["public"] is False


# ---------------------------------------------------------------------------
# run_s3
# ---------------------------------------------------------------------------


def _make_check_result(bucket, region, exists=False, public=False, status=404, error=None):
    return {
        "bucket": bucket,
        "region": region,
        "url": _build_s3_url(bucket, region),
        "dns_resolved": "1.2.3.4" if exists else None,
        "status_code": status,
        "exists": exists,
        "public": public,
        "error": error,
    }


def test_run_s3_default_region(monkeypatch) -> None:
    probed_regions = set()

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        probed_regions.add(region)
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=1.0, max_workers=5)
    assert results["region"] == "us-east-1"
    assert results["regions_checked"] == ["us-east-1"]
    assert probed_regions == {"us-east-1"}
    assert results["candidates_tested"] > 0
    assert results["public_buckets"] == []
    assert results["existing_buckets"] == []
    assert results["private_buckets"] == []
    assert results["wordlist_used"] is False


def test_run_s3_detects_public_bucket(monkeypatch) -> None:
    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        if bucket_name == "example-com":
            return _make_check_result(bucket_name, region, exists=True, public=True, status=200)
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=1.0, max_workers=5)
    assert len(results["public_buckets"]) == 1
    assert results["public_buckets"][0]["bucket"] == "example-com"
    assert results["public_buckets"][0]["public"] is True
    assert len(results["existing_buckets"]) == 1


def test_run_s3_detects_private_bucket(monkeypatch) -> None:
    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        if bucket_name == "example-com":
            return _make_check_result(bucket_name, region, exists=True, public=False, status=403)
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=1.0, max_workers=5)
    assert len(results["private_buckets"]) == 1
    assert results["private_buckets"][0]["bucket"] == "example-com"
    assert results["private_buckets"][0]["public"] is False
    assert len(results["public_buckets"]) == 0


def test_run_s3_with_wordlist(monkeypatch) -> None:
    captured = {}

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        captured[bucket_name] = region
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3(
        "example.com", wordlist=["mybucket"], timeout=1.0, max_workers=5
    )
    assert results["wordlist_used"] is True
    assert "mybucket" in captured
    assert "mybucket-example-com" in captured
    assert "example-com-mybucket" in captured


def test_run_s3_region_all(monkeypatch) -> None:
    probed = []

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        probed.append(region)
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", region="all", timeout=1.0, max_workers=10)
    assert results["region"] == "all"
    assert results["regions_checked"] == S3_REGIONS
    candidates = results["candidates_tested"]
    assert len(probed) == candidates * len(S3_REGIONS)
    assert "Checked" in results["notes"][0]


def test_run_s3_empty_target() -> None:
    results = run_s3("", timeout=1.0, max_workers=5)
    assert results["candidates_tested"] == 0
    assert results["results"] == []
    assert results["public_buckets"] == []
    assert len(results["notes"]) >= 1


def test_run_s3_results_sorted(monkeypatch) -> None:
    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        return _make_check_result(bucket_name, region, exists=True, public=True, status=200)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=1.0, max_workers=2)
    buckets = [r["bucket"] for r in results["results"]]
    assert buckets == sorted(buckets)


def test_run_s3_passes_timeout_and_workers(monkeypatch) -> None:
    captured = {}

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        captured["timeout"] = timeout
        captured["workers"] = None
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=3.0, max_workers=7, region="us-east-1")
    assert captured["timeout"] == 3.0
    assert results["timeout"] == 3.0
    assert results["workers"] == 7


def test_run_s3_region_normalization(monkeypatch) -> None:
    captured = set()

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        captured.add(region)
        return _make_check_result(bucket_name, region, exists=False, status=404)

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    run_s3("example.com", region="US-WEST-2", timeout=1.0, max_workers=3)
    assert "us-west-2" in captured


def test_run_s3_ipv6_target_reports_invalid_bucket_names(monkeypatch) -> None:
    """A bracketed IPv6 target must not crash the command."""

    def _no_request(*args, **kwargs):
        raise AssertionError("no request may be sent for an invalid name")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _no_request)

    results = run_s3("[::1]:443", timeout=1.0, max_workers=5)
    assert results["domain"] == "::1"
    assert results["candidates_tested"] > 0
    assert results["results"]
    assert results["public_buckets"] == []
    assert results["private_buckets"] == []
    assert results["existing_buckets"] == []
    for entry in results["results"]:
        assert entry["error"].startswith("Invalid bucket name")
        assert entry["exists"] is False
        assert entry["public"] is False
    assert any(
        "None of the" in note and "valid S3 bucket name" in note
        for note in results["notes"]
    )


def test_run_s3_probe_exception_is_reported(monkeypatch) -> None:
    """A failing probe must not abort the report of the other probes."""

    def mock_check(bucket_name, region=DEFAULT_REGION, timeout=5.0):
        raise RuntimeError("probe exploded")

    monkeypatch.setattr("ethscan.s3.check_bucket_public", mock_check)

    results = run_s3("example.com", timeout=1.0, max_workers=5)
    assert results["results"]
    for entry in results["results"]:
        assert entry["error"] == "RuntimeError: probe exploded"
        assert entry["exists"] is False
        assert entry["public"] is False
    assert results["public_buckets"] == []


def test_run_s3_invalid_url_is_reported(monkeypatch) -> None:
    """A malformed endpoint URL is reported per probe, not raised."""
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns(None))

    def _raise(req, timeout=None):
        raise http.client.InvalidURL("URL can't contain control characters.")

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", _raise)

    results = run_s3("example.com", region="a b", timeout=1.0, max_workers=5)
    assert results["results"]
    for entry in results["results"]:
        assert entry["error"] == "URL can't contain control characters."
        assert entry["exists"] is False
        assert entry["public"] is False


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_s3_report_json_basic() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 3,
        "regions_checked": ["us-east-1"],
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": ["sample note"],
    }
    output = format_s3_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["candidates_tested"] == 3
    assert parsed["public_buckets"] == []
    assert parsed["notes"] == ["sample note"]


def test_format_s3_report_json_with_public_bucket() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": ["us-east-1"],
        "results": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200)
        ],
        "public_buckets": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200)
        ],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_json(data)
    parsed = json.loads(output)
    assert parsed["public_buckets"][0]["bucket"] == "example-com"
    assert parsed["public_buckets"][0]["public"] is True


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_s3_report_markdown_full() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": True,
        "candidates_tested": 2,
        "regions_checked": ["us-east-1"],
        "results": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200),
            _make_check_result("dev-example-com", "us-east-1", exists=True, public=False, status=403),
        ],
        "public_buckets": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200)
        ],
        "private_buckets": [
            _make_check_result("dev-example-com", "us-east-1", exists=True, public=False, status=403)
        ],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "S3 Bucket Enumeration Report" in output
    assert "**Target:** example.com" in output
    assert "**Region:** us-east-1" in output
    assert "**Public Buckets:** 1" in output
    assert "**Private Buckets:** 1" in output
    assert "## Public Buckets (Accessible)" in output
    assert "example-com" in output
    assert "## All Bucket Results" in output
    assert "**Existing Buckets:** 0" in output or "Existing Buckets" in output


def test_format_s3_report_markdown_no_public() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": ["us-east-1"],
        "results": [
            _make_check_result("example-com", "us-east-1", exists=False, status=404)
        ],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "**Public Buckets:** 0" in output
    assert "No publicly accessible buckets found" in output


def test_format_s3_report_markdown_no_results() -> None:
    data = {
        "target": "",
        "domain": "",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": ["No bucket candidates could be derived from the target."],
    }
    output = format_s3_report_markdown(data)
    assert "No buckets were tested" in output
    assert "No bucket candidates could be derived" in output


def test_format_s3_report_markdown_pipe_escaping() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": ["us-east-1"],
        "results": [
            {
                "bucket": "weird|bucket",
                "region": "us-east-1",
                "url": "https://weird|bucket.s3.amazonaws.com/",
                "dns_resolved": None,
                "status_code": 404,
                "exists": False,
                "public": False,
                "error": "pipe|error|msg",
            }
        ],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "weird\\|bucket" in output
    assert "pipe\\|error\\|msg" in output


def test_format_s3_report_markdown_all_regions() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "all",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": S3_REGIONS,
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": ["Checked 20 regions for each of 1 bucket candidates."],
    }
    output = format_s3_report_markdown(data)
    assert "**Region:** all" in output
    assert ", ".join(S3_REGIONS) in output
    assert "Checked 20 regions" in output


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_s3_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 2,
        "regions_checked": ["us-east-1"],
        "results": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200),
            _make_check_result("dev-example-com", "us-east-1", exists=True, public=False, status=403),
        ],
        "public_buckets": [
            _make_check_result("example-com", "us-east-1", exists=True, public=True, status=200)
        ],
        "private_buckets": [
            _make_check_result("dev-example-com", "us-east-1", exists=True, public=False, status=403)
        ],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error"
    assert "example-com" in lines[1]
    assert "200" in lines[1]
    assert "True" in lines[1]  # public
    assert "403" in lines[2]
    assert "False" in lines[2]  # public


def test_format_s3_report_csv_empty() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": ["us-east-1"],
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error"


def test_format_s3_report_csv_missing_optional_fields() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": ["us-east-1"],
        "results": [
            {
                "bucket": "example-com",
                "region": "us-east-1",
                # missing dns_resolved, url, status_code, exists, public, error
            }
        ],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)

    lines = output.strip().split("\n")
    assert "example-com" in lines[1]
    # 4 empty optional fields (status_code, exists, public, error) = 4 trailing commas
    assert ",,,," in lines[1]


def test_format_s3_report_csv_pipe_escaping() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 1,
        "regions_checked": ["us-east-1"],
        "results": [
            {
                "bucket": "weird|bucket",
                "region": "us-east-1",
                "url": "https://weird|bucket.s3.amazonaws.com/",
                "dns_resolved": None,
                "status_code": 404,
                "exists": False,
                "public": False,
                "error": "pipe|error|msg",
            }
        ],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)

    # With QUOTE_MINIMAL, pipe characters don't require quoting
    assert "weird|bucket" in output
    assert "pipe|error|msg" in output


def test_format_s3_report_csv_preserves_url_and_dns_resolved() -> None:
    """Every bucket probe row carries its URL and DNS resolution (no data loss)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 2,
        "regions_checked": ["us-east-1"],
        "results": [
            {
                "bucket": "public-bucket",
                "region": "us-east-1",
                "url": "https://public-bucket.s3.amazonaws.com/",
                "dns_resolved": "1.2.3.4",
                "status_code": 200,
                "exists": True,
                "public": True,
                "error": None,
            },
            {
                "bucket": "missing-bucket",
                "region": "eu-west-1",
                "url": "https://missing-bucket.s3.eu-west-1.amazonaws.com/",
                "dns_resolved": None,
                "status_code": 404,
                "exists": False,
                "public": False,
                "error": "Connection reset",
            },
        ],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)

    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error"
    # Public bucket row: URL + DNS resolved preserved.
    assert "public-bucket" in lines[1]
    assert "https://public-bucket.s3.amazonaws.com/" in lines[1]
    assert "1.2.3.4" in lines[1]
    assert "True" in lines[1]  # exists
    assert "True" in lines[1]  # public
    # Missing bucket row: URL preserved, DNS resolved empty, error preserved.
    assert "missing-bucket" in lines[2]
    assert "https://missing-bucket.s3.eu-west-1.amazonaws.com/" in lines[2]
    assert "404" in lines[2]
    assert "False" in lines[2]  # exists
    assert "False" in lines[2]  # public
    assert "Connection reset" in lines[2]

def test_check_bucket_public_403_direct_response(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns("1.2.3.4"))

    class DummyResp:
        def __init__(self):
            self.code = 403
        def getcode(self):
            return self.code
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr("ethscan.s3.urllib.request.urlopen", lambda req, timeout=None: DummyResp())
    result = check_bucket_public("mybucket", "us-east-1", 1.0)
    assert result["status_code"] == 403
    assert result["exists"] is True
    assert result["public"] is False


def test_resolve_s3_endpoint_hostname_falsy_returns_none(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._build_s3_url", lambda *args, **kwargs: "https:///")
    assert _resolve_s3_endpoint("any-bucket", "us-east-1") is None


def test_resolve_s3_endpoint_setdefaulttimeout_none_oserror(monkeypatch) -> None:
    class _FakeSocket:
        gaierror = OSError
        herror = OSError

        def setdefaulttimeout(self, value: float) -> None:
            if value is None:
                raise OSError("setdefaulttimeout(None) failed")

        def getdefaulttimeout(self) -> float | None:
            return None

        def gethostbyname(self, host: str) -> str:
            return "1.2.3.4"

    monkeypatch.setattr("ethscan.s3.socket", _FakeSocket())
    assert _resolve_s3_endpoint("bucket", "us-east-1") == "1.2.3.4"


def test_resolve_s3_endpoint_restores_default_socket_timeout(monkeypatch) -> None:
    """_resolve_s3_endpoint restores the default socket timeout it temporarily set.

    The helper switches the process-wide default timeout for its own lookup and
    must restore it afterwards, so a later test does not inherit a 2s (or
    other) default timeout from this call.
    """

    class _RecordingSocket:
        gaierror = OSError
        herror = OSError

        def __init__(self) -> None:
            self.timeout_values: list[float | None] = []

        def setdefaulttimeout(self, value: float) -> None:
            self.timeout_values.append(value)

        def getdefaulttimeout(self) -> float | None:
            return 42.0

        def gethostbyname(self, host: str) -> str:
            return "1.2.3.4"

    fake = _RecordingSocket()
    monkeypatch.setattr("ethscan.s3.socket", fake)
    assert _resolve_s3_endpoint("bucket", "us-east-1") == "1.2.3.4"
    assert fake.timeout_values == [DEFAULT_TIMEOUT, 42.0]


# ---------------------------------------------------------------------------
# Formatter defensive-branch coverage (non-list / non-dict input)
# ---------------------------------------------------------------------------


def test_format_s3_report_markdown_regions_checked_not_list() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": "us-east-1",
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "**Regions Checked:**" in output


def test_format_s3_report_markdown_public_buckets_not_list() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": [],
        "public_buckets": "not-a-list",
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "No publicly accessible buckets found" in output


def test_format_s3_report_markdown_public_buckets_non_dict_entry() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": [],
        "public_buckets": ["not-a-dict"],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "| Bucket | Region | URL | DNS Resolved |" in output
    assert "| not-a-dict |" not in output


def test_format_s3_report_markdown_results_not_list() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": "not-a-list",
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "No buckets were tested" in output


def test_format_s3_report_markdown_results_non_dict_entry() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": ["not-a-dict"],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_markdown(data)
    assert "| Bucket | Region | Exists | Public | Status | DNS Resolved | Error |" in output
    assert "| not-a-dict |" not in output


def test_format_s3_report_markdown_notes_not_list() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": [],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": "not-a-list",
    }
    output = format_s3_report_markdown(data)
    assert "No buckets were tested" in output


def test_format_s3_report_csv_results_not_list() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": "not-a-list",
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)
    lines = output.strip().split("\n")
    assert lines[0] == "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error"
    assert len(lines) == 1


def test_format_s3_report_csv_results_non_dict_entry() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "region": "us-east-1",
        "timeout": 5.0,
        "workers": 20,
        "wordlist_used": False,
        "candidates_tested": 0,
        "regions_checked": [],
        "results": ["not-a-dict"],
        "public_buckets": [],
        "private_buckets": [],
        "existing_buckets": [],
        "notes": [],
    }
    output = format_s3_report_csv(data)
    lines = output.strip().split("\n")
    assert lines[0] == "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error"
    assert len(lines) == 1
