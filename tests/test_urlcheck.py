"""Tests for the ethscan urlcheck module."""

import csv
import io

from ethscan.urlcheck import (
    format_urlcheck_report_csv,
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

def test_format_urlcheck_report_csv() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {
            "total_findings": 1,
            "web_checks_run": ["headers"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
        "web": {
            "security_headers": {"present": ["X-Frame-Options"], "missing": ["CSP"]},
            "information_disclosure": [],
        },
        "fuzz": None,
        "ssl": None,
    }
    output = format_urlcheck_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["section", "key", "value"]
    assert ["summary", "target", "https://example.com"] in reader
    assert ["summary", "total_findings", "1"] in reader
    assert ["web", "header_present", "X-Frame-Options"] in reader
    assert ["web", "header_missing", "CSP"] in reader


def test_format_urlcheck_report_csv_fuzz_ssl() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {
            "total_findings": 0,
            "web_checks_run": ["headers"],
            "fuzz_enabled": True,
            "ssl_checked": True,
        },
        "web": {"security_headers": {"present": [], "missing": []}},
        "fuzz": {
            "findings": [{"path": "/admin", "status_code": 200}],
        },
        "ssl": {
            "valid": True,
            "cert": {
                "subject": "example.com",
                "issuer": "Let's Encrypt",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
        },
    }
    output = format_urlcheck_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert ["summary", "fuzz_enabled", "true"] in reader
    assert ["summary", "ssl_checked", "true"] in reader
    assert ["fuzz", "finding", "/admin (200)"] in reader
    assert ["ssl", "valid", "true"] in reader
    assert ["ssl", "subject", "example.com"] in reader
    assert ["ssl", "issuer", "Let's Encrypt"] in reader
    assert ["ssl", "key_size", "2048"] in reader


def test_format_urlcheck_report_csv_empty() -> None:
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {"total_findings": 0, "web_checks_run": [], "fuzz_enabled": False, "ssl_checked": False},
    }
    output = format_urlcheck_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["section", "key", "value"]
    assert ["summary", "total_findings", "0"] in reader


def test_run_urlcheck_with_weak_ssl(monkeypatch) -> None:
    """run_urlcheck counts weak-SSL cert findings in the summary.

    The dependency names are imported at module level in urlcheck.py, so the
    mocks must be installed on the urlcheck namespace (not on the source
    modules), otherwise run_urlcheck would invoke the real implementations.
    """
    import ethscan.urlcheck as urlcheck_module

    def mock_run_web_checks(target, checks, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "checks": checks,
            "secure": False,
            "security_headers": {
                "present": [],
                "missing": ["Strict-Transport-Security"],
                "missing_count": 1,
            },
            "information_disclosure": ["Server: Apache/2.2.3"],
        }

    def mock_run_ssl(host, port=443, timeout=5.0):
        return {
            "host": host,
            "port": port,
            "valid": False,
            "error": "Certificate expired",
            "cert": {
                "subject": "example.com",
                "issuer": "Test CA",
                "signature_algorithm": "sha1WithRSAEncryption",
                "key_size": 1024,
                "not_before": "2020-01-01",
                "not_after": "2021-01-01",
            },
        }

    monkeypatch.setattr(urlcheck_module, "run_web_checks", mock_run_web_checks)
    monkeypatch.setattr(urlcheck_module, "run_ssl", mock_run_ssl)

    results = run_urlcheck(
        "https://example.com",
        ["headers", "info_disclosure", "ssl"],
        wordlist=["/admin"],
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=5,
    )
    assert results["summary"]["total_findings"] > 0
    assert results["summary"]["ssl_checked"] is True
    # Weak cert contributes: small key + sha1 signature + invalid cert.
    assert results["ssl"]["cert"]["key_size"] == 1024
    assert results["ssl"]["cert"]["signature_algorithm"] == "sha1WithRSAEncryption"


def test_urlcheck_normalize_url_trims() -> None:
    from ethscan.urlcheck import _normalize_url

    assert _normalize_url("  example.com  ") == "https://example.com"


def test_run_urlcheck_fuzz_findings_counted(monkeypatch) -> None:
    """Fuzz findings are folded into the summary total_findings count."""
    import ethscan.urlcheck as urlcheck_module

    monkeypatch.setattr(
        urlcheck_module,
        "run_web_checks",
        lambda target, checks, timeout=5.0: {
            "target": target,
            "host": "example.com",
            "secure": True,
            "security_headers": {
                "present": [],
                "missing": [],
                "total": 7,
                "present_count": 7,
                "missing_count": 0,
            },
            "information_disclosure": [],
        },
    )
    monkeypatch.setattr(
        urlcheck_module,
        "run_fuzz",
        lambda target, wordlist=None, timeout=5.0: {
            "target": target,
            "base_url": target,
            "paths_tested": 2,
            "findings": [
                {"path": "/admin", "status_code": 200, "error": None},
                {"path": "/config", "status_code": 200, "error": None},
            ],
            "all_results": [],
        },
    )

    results = run_urlcheck(
        "https://example.com",
        ["headers"],
        wordlist=["/admin", "/config"],
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=5,
    )
    assert results["summary"]["total_findings"] == 2
    assert results["fuzz"]["findings"][0]["path"] == "/admin"


def test_format_urlcheck_report_markdown_web_ssl_error() -> None:
    """Markdown renderer emits the web-check SSL error branch."""
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
            "ssl": {"error": "TLS handshake failed", "valid": False},
        },
        "fuzz": None,
        "ssl": None,
        "summary": {
            "total_findings": 0,
            "web_checks_run": ["ssl"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "### SSL Configuration (from web check)" in output
    assert "TLS handshake failed" in output
    assert "**Valid:**" not in output


def test_format_urlcheck_report_csv_info_disclosure() -> None:
    """CSV renderer emits a row per information-disclosure finding."""
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {
            "total_findings": 1,
            "web_checks_run": ["headers", "info_disclosure"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
        "web": {
            "security_headers": {"present": [], "missing": []},
            "information_disclosure": [
                {"header": "Server", "value": "Apache/2.4.1", "description": "Reveals server software version."},
            ],
        },
        "fuzz": None,
        "ssl": None,
    }
    output = format_urlcheck_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert ["web", "information_disclosure", "Server"] in reader


def test_format_urlcheck_report_markdown_info_disclosure_table() -> None:
    """Markdown renderer emits the info-disclosure table when findings exist."""
    data = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "checks_requested": ["headers", "info_disclosure"],
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
                "present": [],
                "missing": ["Strict-Transport-Security"],
                "total": 7,
                "present_count": 0,
                "missing_count": 7,
            },
            "information_disclosure": [
                {"header": "Server", "value": "Apache/2.2.3", "description": "Reveals server software version."},
                {"header": "X-Powered-By", "value": "PHP/7.4.0", "description": "Reveals technology stack."},
            ],
        },
        "fuzz": None,
        "ssl": None,
        "summary": {
            "total_findings": 2,
            "web_checks_run": ["headers", "info_disclosure"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
    }
    output = format_urlcheck_report_markdown(data)
    assert "### Information Disclosure" in output
    assert "| Header | Value | Description |" in output
    assert "| Server | Apache/2.2.3 | Reveals server software version. |" in output
    assert "| X-Powered-By | PHP/7.4.0 | Reveals technology stack. |" in output
    assert "No information disclosure headers detected." not in output
