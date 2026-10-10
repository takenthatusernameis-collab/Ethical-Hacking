"""Tests for the ethscan subdomains module."""

import pytest

from ethscan.subdomains import (
    DEFAULT_SUBDOMAINS,
    DEFAULT_RECURSIVE_DEPTH,
    DNS_AVAILABLE,
    _normalize_domain,
    format_subdomains_report_json,
    format_subdomains_report_markdown,
    load_subdomain_wordlist,
    resolve_subdomain,
    run_subdomains,
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


def test_load_subdomain_wordlist(tmp_path) -> None:
    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n\n# comment\napi\n")
    subs = load_subdomain_wordlist(str(wordlist_file))
    assert subs == ["www", "mail", "api"]


def test_load_subdomain_wordlist_skips_empty_and_comments(tmp_path) -> None:
    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("\n\n# comment\n# another\n")
    subs = load_subdomain_wordlist(str(wordlist_file))
    assert subs == []


def test_resolve_subdomain_invalid() -> None:
    subdomain, ip = resolve_subdomain("nonexistent", "invalid.domain.tld", timeout=1.0)
    assert subdomain == "nonexistent"
    assert ip is None


def test_resolve_subdomain_with_resolver_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.subdomains.DNS_AVAILABLE", False)
    subdomain, ip = resolve_subdomain(
        "nonexistent", "invalid.domain.tld", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "nonexistent"
    assert ip is None


def test_run_subdomains_offline_target() -> None:
    results = run_subdomains(
        "nonexistent.invalid.domain.tld",
        subdomains=["www", "mail"],
        timeout=1.0,
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["subdomains_tested"] == 2
    assert results["resolved_count"] == 0
    assert "resolved" in results
    assert "all_results" in results
    assert len(results["all_results"]) == 2
    for entry in results["all_results"]:
        assert entry["ip"] is None


def test_run_subdomains_with_resolver(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.subdomains.DNS_AVAILABLE", False)
    results = run_subdomains(
        "nonexistent.invalid.domain.tld",
        subdomains=["www", "mail"],
        timeout=1.0,
        resolver="8.8.8.8",
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["subdomains_tested"] == 2
    assert results["resolved_count"] == 0
    assert results["resolver"] == "8.8.8.8"
    assert results["dnspython_available"] is False


def test_run_subdomains_uses_default_list() -> None:
    results = run_subdomains("nonexistent.invalid.domain.tld", timeout=1.0)
    assert results["subdomains_tested"] == len(DEFAULT_SUBDOMAINS)


def test_run_subdomains_url_target() -> None:
    results = run_subdomains(
        "https://example.com/path", subdomains=["www"], timeout=1.0
    )
    assert results["domain"] == "example.com"
    assert results["all_results"][0]["hostname"] == "www.example.com"


def test_run_subdomains_recursive_disabled_by_default() -> None:
    results = run_subdomains("nonexistent.invalid.domain.tld", subdomains=["www"], timeout=1.0)
    assert results["recursive"] is False
    assert results["max_depth"] == DEFAULT_RECURSIVE_DEPTH
    assert "per_depth" in results
    assert len(results["per_depth"]) == 1  # Only depth 0


def test_run_subdomains_recursive_enabled(monkeypatch) -> None:
    # Mock resolve_subdomain to return IPs for specific subdomains
    call_count = {"count": 0}

    def mock_resolve_subdomain(subdomain, domain, timeout=2.0, resolver=None):
        call_count["count"] += 1
        # Return IP for www.example.com and dev.www.example.com
        hostname = f"{subdomain}.{domain}"
        if hostname in ("www.example.com", "dev.www.example.com"):
            return subdomain, "1.2.3.4"
        return subdomain, None

    monkeypatch.setattr("ethscan.subdomains.resolve_subdomain", mock_resolve_subdomain)

    results = run_subdomains(
        "example.com",
        subdomains=["www", "dev"],
        timeout=1.0,
        recursive=True,
        max_depth=2,
    )
    assert results["recursive"] is True
    assert results["max_depth"] == 2
    assert "per_depth" in results
    # Depth 0: www.example.com resolved
    # Depth 1: dev.www.example.com resolved (www is resolved, so we enumerate dev.www)
    # Depth 2: no resolved subdomains at depth 1
    assert len(results["per_depth"]) == 3  # depths 0, 1, 2
    assert results["per_depth"][0]["depth"] == 0
    assert results["per_depth"][1]["depth"] == 1
    assert results["per_depth"][2]["depth"] == 2
    # Total resolved should include both depths
    assert results["resolved_count"] >= 1


def test_run_subdomains_recursive_respects_max_depth(monkeypatch) -> None:
    def mock_resolve_subdomain(subdomain, domain, timeout=2.0, resolver=None):
        # Always return an IP so recursion continues
        return subdomain, "1.2.3.4"

    monkeypatch.setattr("ethscan.subdomains.resolve_subdomain", mock_resolve_subdomain)

    results = run_subdomains(
        "example.com",
        subdomains=["www", "dev"],
        timeout=1.0,
        recursive=True,
        max_depth=1,
    )
    # Should only have depths 0 and 1 (max_depth=1 means 1 recursive level)
    assert len(results["per_depth"]) == 2  # depths 0, 1


def test_run_subdomains_recursive_stops_early_when_no_resolved(monkeypatch) -> None:
    def mock_resolve_subdomain(subdomain, domain, timeout=2.0, resolver=None):
        # No IPs returned
        return subdomain, None

    monkeypatch.setattr("ethscan.subdomains.resolve_subdomain", mock_resolve_subdomain)

    results = run_subdomains(
        "example.com",
        subdomains=["www", "dev"],
        timeout=1.0,
        recursive=True,
        max_depth=3,
    )
    # Should have depths 0, 1, 2, 3 but depth 1+ should have 0 tested
    assert len(results["per_depth"]) == 4  # depths 0, 1, 2, 3
    assert results["per_depth"][1]["subdomains_tested"] == 0
    assert results["per_depth"][2]["subdomains_tested"] == 0
    assert results["per_depth"][3]["subdomains_tested"] == 0


def test_format_subdomains_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [{"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
    }
    output = format_subdomains_report_json(data)
    assert "example.com" in output
    assert "resolved" in output
    assert "1.2.3.4" in output


def test_format_subdomains_report_json_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [{"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
        "resolver": "8.8.8.8",
        "dnspython_available": True,
    }
    output = format_subdomains_report_json(data)
    assert "example.com" in output
    assert "8.8.8.8" in output


def test_format_subdomains_report_json_recursive() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 4,
        "resolved_count": 2,
        "resolved": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
        ],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
        "per_depth": [
            {"depth": 0, "subdomains_tested": 2, "resolved_count": 1, "results": []},
            {"depth": 1, "subdomains_tested": 2, "resolved_count": 1, "results": []},
        ],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_subdomains_report_json(data)
    assert "example.com" in output
    assert "recursive" in output
    assert "true" in output.lower()
    assert "max_depth" in output


def test_format_subdomains_report_markdown() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [{"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
    }
    output = format_subdomains_report_markdown(data)
    assert "# ethscan Subdomain Enumeration Report" in output
    assert "example.com" in output
    assert "## Resolved Subdomains" in output
    assert "## All Results" in output
    assert "1.2.3.4" in output
    assert "N/A" in output


def test_format_subdomains_report_markdown_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [{"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"}],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
        "resolver": "8.8.8.8",
        "dnspython_available": True,
    }
    output = format_subdomains_report_markdown(data)
    assert "# ethscan Subdomain Enumeration Report" in output
    assert "**Resolver:** 8.8.8.8 (dnspython: Yes)" in output


def test_format_subdomains_report_markdown_no_resolved() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": None},
        ],
    }
    output = format_subdomains_report_markdown(data)
    assert "# ethscan Subdomain Enumeration Report" in output
    assert "**Resolved:** 0" in output
    assert "## All Results" in output


def test_format_subdomains_report_markdown_recursive() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 4,
        "resolved_count": 2,
        "resolved": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
        ],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
            {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
        ],
        "per_depth": [
            {"depth": 0, "subdomains_tested": 2, "resolved_count": 1, "results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4", "depth": 0},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None, "depth": 0},
            ]},
            {"depth": 1, "subdomains_tested": 2, "resolved_count": 1, "results": [
                {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5", "depth": 1},
            ]},
        ],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_subdomains_report_markdown(data)
    assert "# ethscan Subdomain Enumeration Report" in output
    assert "**Recursive:** Yes" in output
    assert "**Max Depth:** 2" in output
    assert "## Recursive Enumeration (Per Depth)" in output
    assert "### Depth 1" in output
    assert "dev.www.example.com" in output


def test_format_subdomains_report_markdown_recursive_no_results_at_depth() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": None},
        ],
        "per_depth": [
            {"depth": 0, "subdomains_tested": 1, "resolved_count": 0, "results": []},
            {"depth": 1, "subdomains_tested": 0, "resolved_count": 0, "results": []},
        ],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_subdomains_report_markdown(data)
    assert "## Recursive Enumeration (Per Depth)" in output
    assert "### Depth 1" in output
    assert "*No subdomains resolved at this depth.*" in output