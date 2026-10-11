"""Tests for the ethscan subtake module."""

import pytest

from ethscan.subtake import (
    DEFAULT_SUBDOMAINS,
    TAKEOVER_SIGNATURES,
    _normalize_domain,
    check_takeover_signature,
    format_subtake_report_json,
    format_subtake_report_markdown,
    run_subtake,
)


def test_normalize_domain_bare() -> None:
    assert _normalize_domain("example.com") == "example.com"


def test_normalize_domain_uppercase() -> None:
    assert _normalize_domain("Example.COM") == "example.com"


def test_normalize_domain_https_url() -> None:
    assert _normalize_domain("https://example.com/path") == "example.com"


def test_normalize_domain_http_url_with_port() -> None:
    assert _normalize_domain("http://example.com:8080") == "example.com:8080"


def test_normalize_domain_strips_whitespace() -> None:
    assert _normalize_domain("  example.com  ") == "example.com"


def test_default_subdomains_not_empty() -> None:
    assert len(DEFAULT_SUBDOMAINS) > 0
    assert "www" in DEFAULT_SUBDOMAINS
    assert "mail" in DEFAULT_SUBDOMAINS
    assert "api" in DEFAULT_SUBDOMAINS
    assert "admin" in DEFAULT_SUBDOMAINS


def test_takeover_signatures_not_empty() -> None:
    assert len(TAKEOVER_SIGNATURES) > 0
    # Check some key services are present
    services = {sig["service"] for sig in TAKEOVER_SIGNATURES}
    assert "AWS S3" in services
    assert "GitHub Pages" in services
    assert "Heroku" in services
    assert "Azure" in services
    assert "Shopify" in services


def test_check_takeover_signature_s3() -> None:
    result = check_takeover_signature("mybucket.s3.amazonaws.com")
    assert result is not None
    assert result["service"] == "AWS S3"
    assert result["fingerprint"] == "NoSuchBucket"


def test_check_takeover_signature_github_pages() -> None:
    result = check_takeover_signature("username.github.io")
    assert result is not None
    assert result["service"] == "GitHub Pages"
    assert result["fingerprint"] == "There isn't a GitHub Pages site here"


def test_check_takeover_signature_heroku() -> None:
    result = check_takeover_signature("myapp.herokuapp.com")
    assert result is not None
    assert result["service"] == "Heroku"
    assert result["fingerprint"] == "No such app"


def test_check_takeover_signature_azure() -> None:
    result = check_takeover_signature("myapp.azurewebsites.net")
    assert result is not None
    assert result["service"] == "Azure"
    assert result["fingerprint"] == "404 Web Site not found"


def test_check_takeover_signature_shopify() -> None:
    result = check_takeover_signature("myshop.myshopify.com")
    assert result is not None
    assert result["service"] == "Shopify"
    assert result["fingerprint"] == "Sorry, this shop is currently unavailable"


def test_check_takeover_signature_unknown() -> None:
    result = check_takeover_signature("unknown.example.com")
    assert result is None


def test_check_takeover_signature_case_insensitive() -> None:
    result = check_takeover_signature("MYBUCKET.S3.AMAZONAWS.COM")
    assert result is not None
    assert result["service"] == "AWS S3"


def test_run_subtake_offline_target() -> None:
    results = run_subtake(
        "nonexistent.invalid.domain.tld",
        subdomains=["www", "mail"],
        timeout=1.0,
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["subdomains_tested"] == 2
    assert results["vulnerable_count"] == 0
    assert "vulnerable" in results
    assert "all_results" in results
    assert len(results["all_results"]) == 2
    for entry in results["all_results"]:
        assert entry["vulnerable"] is False
        assert entry["takeover"] is None


def test_run_subtake_with_resolver(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.subtake.DNS_AVAILABLE", False)
    results = run_subtake(
        "nonexistent.invalid.domain.tld",
        subdomains=["www", "mail"],
        timeout=1.0,
        resolver="8.8.8.8",
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["subdomains_tested"] == 2
    assert results["vulnerable_count"] == 0
    assert results["resolver"] == "8.8.8.8"
    assert results["dnspython_available"] is False


def test_run_subtake_uses_default_list() -> None:
    results = run_subtake("nonexistent.invalid.domain.tld", timeout=1.0)
    assert results["subdomains_tested"] == len(DEFAULT_SUBDOMAINS)


def test_run_subtake_url_target() -> None:
    results = run_subtake(
        "https://example.com/path", subdomains=["www"], timeout=1.0
    )
    assert results["domain"] == "example.com"
    assert results["all_results"][0]["hostname"] == "www.example.com"


def test_run_subtake_vulnerable_s3(monkeypatch) -> None:
    def mock_resolve_cname(hostname, timeout=2.0, resolver=None):
        if hostname == "www.example.com":
            return "mybucket.s3.amazonaws.com"
        return None

    def mock_resolve_a(hostname, timeout=2.0, resolver=None):
        return []

    def mock_resolve_aaaa(hostname, timeout=2.0, resolver=None):
        return []

    def mock_check_http(hostname, timeout=5.0):
        return "NoSuchBucket"

    monkeypatch.setattr("ethscan.subtake.resolve_cname", mock_resolve_cname)
    monkeypatch.setattr("ethscan.subtake.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.subtake.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.subtake.check_http_fingerprint", mock_check_http)

    results = run_subtake(
        "example.com",
        subdomains=["www"],
        timeout=1.0,
    )
    assert results["vulnerable_count"] == 1
    vuln = results["vulnerable"][0]
    assert vuln["hostname"] == "www.example.com"
    assert vuln["vulnerable"] is True
    takeover = vuln["takeover"]
    assert takeover["service"] == "AWS S3"
    assert takeover["cname"] == "mybucket.s3.amazonaws.com"
    assert takeover["http_confirmed"] is True
    assert "NoSuchBucket" in takeover["evidence"]


def test_run_subtake_vulnerable_github_pages(monkeypatch) -> None:
    def mock_resolve_cname(hostname, timeout=2.0, resolver=None):
        if hostname == "blog.example.com":
            return "user.github.io"
        return None

    def mock_resolve_a(hostname, timeout=2.0, resolver=None):
        return []

    def mock_resolve_aaaa(hostname, timeout=2.0, resolver=None):
        return []

    def mock_check_http(hostname, timeout=5.0):
        return "There isn't a GitHub Pages site here"

    monkeypatch.setattr("ethscan.subtake.resolve_cname", mock_resolve_cname)
    monkeypatch.setattr("ethscan.subtake.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.subtake.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.subtake.check_http_fingerprint", mock_check_http)

    results = run_subtake(
        "example.com",
        subdomains=["blog"],
        timeout=1.0,
    )
    assert results["vulnerable_count"] == 1
    vuln = results["vulnerable"][0]
    assert vuln["hostname"] == "blog.example.com"
    takeover = vuln["takeover"]
    assert takeover["service"] == "GitHub Pages"
    assert takeover["http_confirmed"] is True


def test_run_subtake_vulnerable_heroku(monkeypatch) -> None:
    def mock_resolve_cname(hostname, timeout=2.0, resolver=None):
        if hostname == "app.example.com":
            return "myapp.herokuapp.com"
        return None

    def mock_resolve_a(hostname, timeout=2.0, resolver=None):
        return []

    def mock_resolve_aaaa(hostname, timeout=2.0, resolver=None):
        return []

    def mock_check_http(hostname, timeout=5.0):
        return "No such app"

    monkeypatch.setattr("ethscan.subtake.resolve_cname", mock_resolve_cname)
    monkeypatch.setattr("ethscan.subtake.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.subtake.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.subtake.check_http_fingerprint", mock_check_http)

    results = run_subtake(
        "example.com",
        subdomains=["app"],
        timeout=1.0,
    )
    assert results["vulnerable_count"] == 1
    vuln = results["vulnerable"][0]
    assert vuln["hostname"] == "app.example.com"
    takeover = vuln["takeover"]
    assert takeover["service"] == "Heroku"
    assert takeover["http_confirmed"] is True


def test_run_subtake_no_http_confirmation(monkeypatch) -> None:
    def mock_resolve_cname(hostname, timeout=2.0, resolver=None):
        if hostname == "www.example.com":
            return "mybucket.s3.amazonaws.com"
        return None

    def mock_resolve_a(hostname, timeout=2.0, resolver=None):
        return []

    def mock_resolve_aaaa(hostname, timeout=2.0, resolver=None):
        return []

    def mock_check_http(hostname, timeout=5.0):
        return "Some other content"

    monkeypatch.setattr("ethscan.subtake.resolve_cname", mock_resolve_cname)
    monkeypatch.setattr("ethscan.subtake.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.subtake.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.subtake.check_http_fingerprint", mock_check_http)

    results = run_subtake(
        "example.com",
        subdomains=["www"],
        timeout=1.0,
    )
    assert results["vulnerable_count"] == 1
    vuln = results["vulnerable"][0]
    takeover = vuln["takeover"]
    assert takeover["http_confirmed"] is False
    assert "CNAME points to vulnerable service" in takeover["evidence"]


def test_format_subtake_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "vulnerable_count": 1,
        "vulnerable": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "mybucket.s3.amazonaws.com",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "AWS S3",
                    "cname": "mybucket.s3.amazonaws.com",
                    "fingerprint": "NoSuchBucket",
                    "description": "S3 bucket does not exist",
                    "http_confirmed": True,
                    "evidence": "NoSuchBucket",
                },
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "mybucket.s3.amazonaws.com",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "AWS S3",
                    "cname": "mybucket.s3.amazonaws.com",
                    "fingerprint": "NoSuchBucket",
                    "description": "S3 bucket does not exist",
                    "http_confirmed": True,
                    "evidence": "NoSuchBucket",
                },
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            },
        ],
    }
    output = format_subtake_report_json(data)
    assert "example.com" in output
    assert "vulnerable_count" in output
    assert "1" in output
    assert "AWS S3" in output
    assert "NoSuchBucket" in output


def test_format_subtake_report_json_no_vulnerable() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": [],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            }
        ],
    }
    output = format_subtake_report_json(data)
    assert "example.com" in output
    assert "vulnerable_count" in output
    assert "0" in output


def test_format_subtake_report_markdown() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "vulnerable_count": 1,
        "vulnerable": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "mybucket.s3.amazonaws.com",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "AWS S3",
                    "cname": "mybucket.s3.amazonaws.com",
                    "fingerprint": "NoSuchBucket",
                    "description": "S3 bucket does not exist",
                    "http_confirmed": True,
                    "evidence": "NoSuchBucket",
                },
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "mybucket.s3.amazonaws.com",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "AWS S3",
                    "cname": "mybucket.s3.amazonaws.com",
                    "fingerprint": "NoSuchBucket",
                    "description": "S3 bucket does not exist",
                    "http_confirmed": True,
                    "evidence": "NoSuchBucket",
                },
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            },
        ],
    }
    output = format_subtake_report_markdown(data)
    assert "# ethscan Subdomain Takeover Report" in output
    assert "example.com" in output
    assert "## Vulnerable Subdomains (Potential Takeover)" in output
    assert "AWS S3" in output
    assert "NoSuchBucket" in output
    assert "## All Results" in output
    assert "www.example.com" in output
    assert "mail.example.com" in output
    assert "1.2.3.4" in output


def test_format_subtake_report_markdown_no_vulnerable() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": [],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            }
        ],
    }
    output = format_subtake_report_markdown(data)
    assert "# ethscan Subdomain Takeover Report" in output
    assert "**Vulnerable:** 0" in output
    assert "## Vulnerable Subdomains (Potential Takeover)" in output
    assert "*No vulnerable subdomains detected.*" in output


def test_format_subtake_report_markdown_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": [],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            }
        ],
        "resolver": "8.8.8.8",
        "dnspython_available": True,
    }
    output = format_subtake_report_markdown(data)
    assert "# ethscan Subdomain Takeover Report" in output
    assert "**Resolver:** 8.8.8.8 (dnspython: Yes)" in output


def test_format_subtake_report_markdown_pipe_escape() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "vulnerable_count": 1,
        "vulnerable": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "test|value",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "Test|Service",
                    "cname": "test|value",
                    "fingerprint": "finger|print",
                    "description": "desc",
                    "http_confirmed": True,
                    "evidence": "evidence",
                },
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "test|value",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "Test|Service",
                    "cname": "test|value",
                    "fingerprint": "finger|print",
                    "description": "desc",
                    "http_confirmed": True,
                    "evidence": "evidence",
                },
            }
        ],
    }
    output = format_subtake_report_markdown(data)
    assert "test\\|value" in output
    assert "Test\\|Service" in output
    assert "finger\\|print" in output