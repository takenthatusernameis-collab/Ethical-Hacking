"""Tests for the ethscan web security module."""

import pytest

from ethscan.web import (
    check_information_disclosure,
    check_security_headers,
    check_ssl_configuration,
    fetch_headers,
    format_web_report_json,
    format_web_report_markdown,
    run_web_checks,
)


def test_parse_url_https() -> None:
    from ethscan.web import _parse_url

    host, port, secure = _parse_url("https://example.com")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_parse_url_http_with_port() -> None:
    from ethscan.web import _parse_url

    host, port, secure = _parse_url("http://example.com:8080")
    assert host == "example.com"
    assert port == 8080
    assert secure is False


def test_parse_url_bare_host() -> None:
    from ethscan.web import _parse_url

    host, port, secure = _parse_url("example.com")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_check_security_headers_all_missing() -> None:
    result = check_security_headers({})
    assert result["present_count"] == 0
    assert result["missing_count"] == result["total"]
    assert len(result["present"]) == 0
    assert len(result["missing"]) == result["total"]


def test_check_security_headers_all_present() -> None:
    from ethscan.web import SECURITY_HEADERS

    headers = {h.lower(): "value" for h in SECURITY_HEADERS}
    result = check_security_headers(headers)
    assert result["present_count"] == result["total"]
    assert result["missing_count"] == 0


def test_check_information_disclosure_detects_server() -> None:
    headers = {"server": "Apache/2.4.1", "content-type": "text/html"}
    findings = check_information_disclosure(headers)
    assert len(findings) == 1
    assert findings[0]["header"] == "Server"
    assert findings[0]["value"] == "Apache/2.4.1"


def test_check_information_disclosure_no_findings() -> None:
    headers = {"content-type": "text/html"}
    findings = check_information_disclosure(headers)
    assert findings == []


def test_check_ssl_configuration_invalid_host() -> None:
    result = check_ssl_configuration("nonexistent.invalid.domain.tld", timeout=2.0)
    assert result["valid"] is False
    assert result["error"] is not None


def test_run_web_checks_offline_target() -> None:
    # Should not raise; returns structured results even on failure.
    results = run_web_checks("http://nonexistent.invalid.domain.tld", ["headers", "info_disclosure"], timeout=2.0)
    assert results["target"].startswith("http://")
    assert results["secure"] is False
    assert "headers" in results
    assert "security_headers" in results
    assert "information_disclosure" in results


def test_format_web_report_json() -> None:
    data = {
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
    }
    output = format_web_report_json(data)
    assert "example.com" in output
    assert "security_headers" in output


def test_format_web_report_markdown() -> None:
    data = {
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
    }
    output = format_web_report_markdown(data)
    assert "# ethscan Web Security Report" in output
    assert "example.com" in output
    assert "## Security Headers" in output
    assert "## Information Disclosure" in output
    assert "## SSL/TLS" in output


def test_fetch_headers_offline() -> None:
    headers = fetch_headers("http://nonexistent.invalid.domain.tld", timeout=1.0)
    assert headers == {}