"""Tests for the ethscan s3 module."""

import json
import socket
import urllib.error
from typing import Optional

import pytest

from ethscan.s3 import (
    DEFAULT_BUCKET_NAMES,
    DEFAULT_REGION,
    S3_REGIONS,
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

    def read(self, n: Optional[int] = -1) -> bytes:
        if n is None or n < 0:
            return self._body
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _mock_dns(resolved: Optional[str] = "1.2.3.4"):
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


def test_check_bucket_public_url_and_region_fields(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.s3._resolve_s3_endpoint", _mock_dns(None))
    monkeypatch.setattr(
        "ethscan.s3.urllib.request.urlopen",
        lambda req, timeout=None: _FakeResponse(200),
    )
    result = check_bucket_public("mybucket", "eu-west-1", 1.0)
    assert result["url"] == "https://mybucket.s3.eu-west-1.amazonaws.com/"
    assert result["region"] == "eu-west-1"


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

    lines = output.strip().split("\n")
    assert lines[0] == "target,domain,bucket,region,status_code,exists,public,error"
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

    assert output.strip() == "target,domain,bucket,region,status_code,exists,public,error"


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
    assert ",,," in lines[1]  # empty optional fields


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

    assert '"weird|bucket"' in output
    assert '"pipe|error|msg"' in output
