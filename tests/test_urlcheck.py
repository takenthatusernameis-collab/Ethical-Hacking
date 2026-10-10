"""Tests for the ethscan urlcheck module."""

import pytest

from ethscan.urlcheck import (
    format_urlcheck_report_json,
    format_urlcheck_report_markdown,
    run_urlcheck,
)


def test_normalize_url_https() -> None:
    from ethscan.urlcheck import _normalize_url

    assert _normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_http() -> None:
    from ethscan.urlcheck import _normalize_url

    assert _normalize_url("http://example.com") == "http://example.com"


def test_normalize_url_with_port() -> None:
    from ethscan.urlcheck import _normalize_url

    assert _normalize_url("https://example.com:8443") == "https://example.com:8443"


def test_normalize_url_bare_host() -> None:
    from ethscan.urlcheck import _normalize_url

    assert _normalize_url("example.com") == "https://example.com"


def test_run_urlcheck_offline_target() -> None:
    results = run_urlcheck(
        "http://nonexistent.invalid.domain.tld",
        ["headers", "info_disclosure"],
        wordlist=["/admin", "/login"],
        fuzz_paths=True,
        port=443,
        timeout=1.0,
        workers=5,
    )
    assert results["target"] == "http://nonexistent.invalid.domain.tld"
    assert results["normalized_target"].startswith("http://")
    assert "web" in results
    assert "fuzz" in results
    assert "ssl" in results
    assert "summary" in results
    assert results["web"]["secure"] is False
    assert results["fuzz"]["paths_tested"] == 2
    assert len(results["fuzz"]["all_results"]) == 2


def test_run_urlcheck_fuzz_disabled() -> None:
    results = run_urlcheck(
        "http://nonexistent.invalid.domain.tld",
        ["headers", "info_disclosure"],
        wordlist=["/admin"],
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=5,
    )
    assert results["fuzz"] is None
    assert results["summary"]["fuzz_enabled"] is False


def test_run_urlcheck_ssl_not_requested() -> None:
    results = run_urlcheck(
        "http://nonexistent.invalid.domain.tld",
        ["headers"],
        wordlist=None,
        fuzz_paths=False,
        port=443,
        timeout=1.0,
        workers=5,
    )
    assert "ssl" in results
    assert results["summary"]["ssl_checked"] is False


def test_format_urlcheck_report_json() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["headers", "ssl"],
        "fuzz_enabled": True,
        "port": 443,
        "timeout": 5.0,
        "workers": 10,
        "web": {
            "target": "https://example.com",
            "host": "example.com",
            "port": 443,
            "secure": True,
            "security_headers": {
                "present": ["Content-Security-Policy"],
                "missing": ["X-Frame-Options"],
                "total": 7,
                "present_count": 1,
                "missing_count": 6,
            },
            "information_disclosure": [],
            "ssl": {"valid": True, "subject": "example.com", "issuer": "Let's Encrypt", "not_after": "Jan  1 00:00:00 2027 GMT", "days_remaining": 100},
        },
        "fuzz": {
            "target": "https://example.com",
            "base_url": "https://example.com",
            "paths_tested": 2,
            "findings": [{"path": "/admin", "status_code": 200, "error": None}],
            "all_results": [
                {"path": "/admin", "status_code": 200, "error": None},
                {"path": "/login", "status_code": 404, "error": None},
            ],
        },
        "ssl": {
            "target": "example.com",
            "host": "example.com",
            "port": 443,
            "timeout": 5.0,
            "error": None,
            "chain_length": 2,
            "cert": {
                "subject": "example.com",
                "issuer": "Let's Encrypt",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2027 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        },
        "summary": {
            "total_findings": 7,
            "web_checks_run": ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": True,
            "ssl_checked": True,
        },
    }
    output = format_urlcheck_report_json(data)
    assert "example.com" in output
    assert "security_headers" in output
    assert "findings" in output
    assert "admin" in output


def test_format_urlcheck_report_markdown() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["headers", "ssl"],
        "fuzz_enabled": True,
        "port": 443,
        "timeout": 5.0,
        "workers": 10,
        "web": {
            "target": "https://example.com",
            "host": "example.com",
            "port": 443,
            "secure": True,
            "security_headers": {
                "present": ["Content-Security-Policy"],
                "missing": ["X-Frame-Options"],
                "total": 7,
                "present_count": 1,
                "missing_count": 6,
            },
            "information_disclosure": [],
            "ssl": {"valid": True, "subject": "example.com", "issuer": "Let's Encrypt", "not_after": "Jan  1 00:00:00 2027 GMT", "days_remaining": 100},
        },
        "fuzz": {
            "target": "https://example.com",
            "base_url": "https://example.com",
            "paths_tested": 2,
            "findings": [{"path": "/admin", "status_code": 200, "error": None}],
            "all_results": [
                {"path": "/admin", "status_code": 200, "error": None},
                {"path": "/login", "status_code": 404, "error": None},
            ],
        },
        "ssl": {
            "target": "example.com",
            "host": "example.com",
            "port": 443,
            "timeout": 5.0,
            "error": None,
            "chain_length": 2,
            "cert": {
                "subject": "example.com",
                "issuer": "Let's Encrypt",
                "sans": ["example.com", "www.example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2027 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        },
        "summary": {
            "total_findings": 7,
            "web_checks_run": ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": True,
            "ssl_checked": True,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "# ethscan Consolidated Web Assessment Report" in output
    assert "example.com" in output
    assert "## Summary" in output
    assert "## Web Security Checks" in output
    assert "### Security Headers" in output
    assert "### Information Disclosure" in output
    assert "### SSL Configuration (from web check)" in output
    assert "## HTTP Fuzzing / Path Discovery" in output
    assert "### Findings" in output
    assert "### All Results" in output
    assert "## SSL/TLS Certificate Inspection" in output
    assert "### Certificate" in output
    assert "Let's Encrypt" in output
    assert "sha256WithRSAEncryption" in output
    assert "2048 bits" in output
    assert "www.example.com" in output


def test_format_urlcheck_report_markdown_no_fuzz() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["headers"],
        "fuzz_enabled": False,
        "port": 443,
        "timeout": 5.0,
        "workers": 10,
        "web": {
            "target": "https://example.com",
            "host": "example.com",
            "port": 443,
            "secure": True,
            "security_headers": {
                "present": ["Content-Security-Policy"],
                "missing": ["X-Frame-Options"],
                "total": 7,
                "present_count": 1,
                "missing_count": 6,
            },
            "information_disclosure": [],
        },
        "fuzz": None,
        "ssl": None,
        "summary": {
            "total_findings": 6,
            "web_checks_run": ["headers"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "# ethscan Consolidated Web Assessment Report" in output
    assert "## HTTP Fuzzing / Path Discovery" not in output
    assert "## SSL/TLS Certificate Inspection" not in output


def test_format_urlcheck_report_markdown_ssl_error() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["ssl"],
        "fuzz_enabled": False,
        "port": 443,
        "timeout": 5.0,
        "workers": 10,
        "web": {
            "target": "https://example.com",
            "host": "example.com",
            "port": 443,
            "secure": True,
        },
        "fuzz": None,
        "ssl": {
            "target": "example.com",
            "host": "example.com",
            "port": 443,
            "timeout": 5.0,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        },
        "summary": {
            "total_findings": 1,
            "web_checks_run": ["ssl"],
            "fuzz_enabled": False,
            "ssl_checked": True,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "connection refused" in output
    assert "### Certificate" not in output


def test_format_urlcheck_report_markdown_ssl_verification_error_with_cert() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["ssl"],
        "fuzz_enabled": False,
        "port": 443,
        "timeout": 5.0,
        "workers": 10,
        "web": {
            "target": "https://example.com",
            "host": "example.com",
            "port": 443,
            "secure": True,
        },
        "fuzz": None,
        "ssl": {
            "target": "example.com",
            "host": "example.com",
            "port": 443,
            "timeout": 5.0,
            "error": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
            "chain_length": 0,
            "cert": {
                "subject": "example.com",
                "issuer": "Test CA",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2027 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": False,
            "days_remaining": None,
        },
        "summary": {
            "total_findings": 2,
            "web_checks_run": ["ssl"],
            "fuzz_enabled": False,
            "ssl_checked": True,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "certificate verify failed" in output
    assert "### Certificate" in output
    assert "example.com" in output
    assert "Test CA" in output
    assert "sha256WithRSAEncryption" in output
    assert "2048 bits" in output