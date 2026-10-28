"""Tests for the ethscan subdomains module."""


import socket

import pytest

from ethscan.subdomains import (
    DEFAULT_RECURSIVE_DEPTH,
    DEFAULT_SUBDOMAINS,
    _normalize_domain,
    format_subdomains_report_csv,
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


def test_resolve_subdomain_with_a_label_that_holds_a_null_byte() -> None:
    """A label that cannot be resolved is a failed lookup, not a crash.

    ``socket.gethostbyname`` refuses a name that holds a null byte with a
    ``TypeError``, which is not an ``OSError``.
    """
    subdomain, ip = resolve_subdomain("a\x00b", "example.com", timeout=1.0)
    assert subdomain == "a\x00b"
    assert ip is None


def test_resolve_subdomain_restores_default_socket_timeout(monkeypatch) -> None:
    """resolve_subdomain restores the default socket timeout it temporarily set.

    The helper switches the process-wide default timeout for its own lookup and
    must restore it afterwards, so a later test does not inherit a 2s (or
    other) default timeout from this call.
    """

    def blocked(*args, **kwargs):
        raise socket.gaierror("blocked")

    monkeypatch.setattr("ethscan.subdomains.socket.gethostbyname", blocked)
    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(123.0)
    try:
        subdomain, ip = resolve_subdomain("www", "example.invalid", timeout=0.1)
        assert subdomain == "www"
        assert ip is None
        assert socket.getdefaulttimeout() == 123.0
    finally:
        socket.setdefaulttimeout(previous)


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


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_subdomains_report_csv_basic() -> None:
    data = {
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "93.184.216.34"},
            {"subdomain": "api", "hostname": "api.example.com", "ip": "93.184.216.34"},
        ]
    }
    output = format_subdomains_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "subdomain,hostname,ip,resolved"
    assert "www,www.example.com,93.184.216.34,true" in lines
    assert "api,api.example.com,93.184.216.34,true" in lines


def test_format_subdomains_report_csv_empty() -> None:
    data = {"all_results": []}
    output = format_subdomains_report_csv(data)
    assert output == "subdomain,hostname,ip,resolved"


def test_format_subdomains_report_csv_missing_fields() -> None:
    data = {
        "all_results": [
            {"subdomain": "www"},
            {"hostname": "api.example.com"},
        ]
    }
    output = format_subdomains_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "subdomain,hostname,ip,resolved"
    assert "www,,,false" in lines
    assert ",api.example.com,,false" in lines


def test_format_subdomains_report_csv_escaping() -> None:
    data = {
        "all_results": [
            {"subdomain": "weird,name", "hostname": "host,example.com", "ip": "1.2.3.4"},
        ]
    }
    output = format_subdomains_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "subdomain,hostname,ip,resolved"
    assert any(line.startswith('"weird,name"') for line in lines[1:])


# ---------------------------------------------------------------------------
# dnspython availability branches (lines 12-13 and 100-108)
# ---------------------------------------------------------------------------

def test_dns_availability_flag_true(monkeypatch) -> None:
    """DNS_AVAILABLE is True when the dns package imports cleanly (lines 12-13)."""
    import sys
    import types
    from importlib import reload

    dns_pkg = types.ModuleType("dns")
    dns_pkg.__path__ = []
    dns_resolver = types.ModuleType("dns.resolver")
    dns_exception = types.ModuleType("dns.exception")

    class DNSException(Exception):
        pass

    dns_exception.DNSException = DNSException

    class Resolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            return []

    dns_resolver.Resolver = Resolver
    dns_pkg.resolver = dns_resolver
    dns_pkg.exception = dns_exception

    monkeypatch.setitem(sys.modules, "dns", dns_pkg)
    monkeypatch.setitem(sys.modules, "dns.resolver", dns_resolver)
    monkeypatch.setitem(sys.modules, "dns.exception", dns_exception)

    import ethscan.subdomains as sub
    reload(sub)
    try:
        assert sub.DNS_AVAILABLE is True
    finally:
        monkeypatch.delitem(sys.modules, "dns", raising=False)
        monkeypatch.delitem(sys.modules, "dns.resolver", raising=False)
        monkeypatch.delitem(sys.modules, "dns.message", raising=False)
        monkeypatch.delitem(sys.modules, "dns.exception", raising=False)
        reload(sub)


def test_dns_availability_flag_false(monkeypatch) -> None:
    """DNS_AVAILABLE is False when dns is not importable (the except branch)."""
    import sys
    from importlib import reload

    import ethscan.subdomains as sub

    monkeypatch.setitem(sys.modules, "dns", None)  # forces ImportError on import dns
    reload(sub)
    try:
        assert sub.DNS_AVAILABLE is False
    finally:
        monkeypatch.delitem(sys.modules, "dns", raising=False)
        reload(sub)


def test_resolve_subdomain_with_resolver_success(monkeypatch) -> None:
    """resolve_subdomain uses the dnspython resolver path on success (lines 100-106)."""
    import types

    import ethscan.subdomains as sub

    class FakeRdata:
        def __str__(self):
            return "1.2.3.4"

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            assert hostname == "www.example.com"
            assert rdtype == "A"
            assert self.nameservers == ["8.8.8.8"]
            return [FakeRdata()]

    fake_dns = types.ModuleType("dns")
    fake_exc = types.ModuleType("dns.exception")

    class DNSException(Exception):
        pass

    fake_exc.DNSException = DNSException
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = FakeResolver
    fake_dns.exception = fake_exc

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip == "1.2.3.4"


def test_resolve_subdomain_with_resolver_dns_exception(monkeypatch) -> None:
    """resolve_subdomain swallows dns.exception.DNSException (line 107-108)."""
    import types

    import ethscan.subdomains as sub

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            raise sub.dns.exception.DNSException("boom")

    fake_dns = types.ModuleType("dns")
    fake_exc = types.ModuleType("dns.exception")

    class DNSException(Exception):
        pass

    fake_exc.DNSException = DNSException
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = FakeResolver
    fake_dns.exception = fake_exc

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip is None


def test_resolve_subdomain_with_resolver_oserror(monkeypatch) -> None:
    """resolve_subdomain swallows OSError from the dnspython path (line 107-108)."""
    import types

    import ethscan.subdomains as sub

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            raise OSError("network down")

    fake_dns = types.ModuleType("dns")
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = FakeResolver
    fake_dns.exception = types.ModuleType("dns.exception")

    class _DNSException(Exception):
        pass

    fake_dns.exception.DNSException = _DNSException

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip is None


def test_resolve_subdomain_with_resolver_valueerror(monkeypatch) -> None:
    """resolve_subdomain swallows ValueError from the dnspython path (line 107-108)."""
    import types

    import ethscan.subdomains as sub

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            raise ValueError("bad input")

    fake_dns = types.ModuleType("dns")
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = FakeResolver
    fake_dns.exception = types.ModuleType("dns.exception")

    class _DNSException2(Exception):
        pass

    fake_dns.exception.DNSException = _DNSException2

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip is None


def test_resolve_subdomain_with_resolver_empty_answer_set(monkeypatch) -> None:
    """A dnspython answer set that is empty is a failed lookup, not a crash.

    ``str(answers[0])`` on an empty list raises ``IndexError``, which is not a
    ``ValueError`` and is not caught by the guard that lists the exception
    types the resolver raises. A server that answers an A query with no
    records (or that the toolkit's resolver treats as such) must be reported
    the way any other failed lookup is reported.
    """
    import types

    import ethscan.subdomains as sub

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            return []

    fake_dns = types.ModuleType("dns")
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = FakeResolver
    fake_dns.exception = types.ModuleType("dns.exception")

    class _DNSException(Exception):
        pass

    fake_dns.exception.DNSException = _DNSException

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip is None


ESCAPE_TYPES = [
    pytest.param(IndexError, id="indexerror"),
    pytest.param(AttributeError, id="attributeerror"),
    pytest.param(KeyError, id="keyerror"),
]


def _make_raising_resolver(exc):
    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            raise exc("boom")

    return FakeResolver


@pytest.mark.parametrize("exc", ESCAPE_TYPES)
def test_resolve_subdomain_swallows_unlisted_exceptions(monkeypatch, exc):
    """resolve_subdomain returns (subdomain, None) instead of raising unlisted exceptions (line 106)."""
    import types

    import ethscan.subdomains as sub

    fake_dns = types.ModuleType("dns")
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.resolver.Resolver = _make_raising_resolver(exc)
    fake_dns.exception = types.ModuleType("dns.exception")

    class _DNSException(Exception):
        pass

    fake_dns.exception.DNSException = _DNSException

    monkeypatch.setattr(sub, "dns", fake_dns)
    monkeypatch.setattr(sub, "DNS_AVAILABLE", True)

    subdomain, ip = resolve_subdomain(
        "www", "example.com", timeout=1.0, resolver="8.8.8.8"
    )
    assert subdomain == "www"
    assert ip is None


def test_subdomains_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing name lookup is reported as unresolved, not raised."""
    import ethscan.subdomains

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.subdomains.socket.gethostbyname", boom)

    results = ethscan.subdomains.run_subdomains("example.com", subdomains=["www"])

    assert isinstance(results, dict)
    assert results["resolved"] == []
    assert all(entry["ip"] is None for entry in results["all_results"])


# ---------------------------------------------------------------------------
# _enumerate_depth exception branches (lines 180-192)
# ---------------------------------------------------------------------------


def test_enumerate_depth_inner_future_failure_falls_back_to_label(monkeypatch) -> None:
    """When a future's result raises, the inner except records the label with no IP (lines 180-186)."""
    import ethscan.subdomains

    def raising_resolve(subdomain, domain, timeout=2.0, resolver=None):
        raise RuntimeError("worker exploded")

    monkeypatch.setattr("ethscan.subdomains.resolve_subdomain", raising_resolve)

    results = ethscan.subdomains.run_subdomains("example.com", subdomains=["www", "mail"])

    assert results["resolved"] == []
    hostnames = {entry["hostname"] for entry in results["all_results"]}
    assert hostnames == {"www.example.com", "mail.example.com"}
    assert all(entry["ip"] is None for entry in results["all_results"])


class _FailingExecutor:
    """A ThreadPoolExecutor stand-in whose submit always raises."""

    def __init__(self, max_workers=None, thread_name_prefix=""):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        raise RuntimeError("executor broken")


def test_enumerate_depth_outer_executor_failure_falls_back_to_labels(monkeypatch) -> None:
    """When the executor itself fails, the outer except records every label with no IP (lines 187-192)."""
    import ethscan.subdomains

    monkeypatch.setattr("ethscan.subdomains.ThreadPoolExecutor", _FailingExecutor)

    results = ethscan.subdomains.run_subdomains("example.com", subdomains=["www", "mail"])

    assert results["resolved"] == []
    assert results["subdomains_tested"] == 2
    hostnames = {entry["hostname"] for entry in results["all_results"]}
    assert hostnames == {"www.example.com", "mail.example.com"}
    assert all(entry["ip"] is None for entry in results["all_results"])


# ---------------------------------------------------------------------------
# Formatter non-dict entry branches (lines 307, 318, 329, 342, 360)
# ---------------------------------------------------------------------------


def test_format_subdomains_report_markdown_resolved_non_dict_entries() -> None:
    """Non-dict entries in the resolved list are skipped (line 307)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "resolved_count": 1,
        "resolved": [
            "not-a-dict",
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
            42,
        ],
        "all_results": [],
    }
    output = format_subdomains_report_markdown(data)
    assert "www.example.com" in output
    assert "not-a-dict" not in output


def test_format_subdomains_report_markdown_all_results_non_dict_entries() -> None:
    """Non-dict entries in all_results are skipped (line 318)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [
            None,
            {"subdomain": "www", "hostname": "www.example.com", "ip": None},
        ],
    }
    output = format_subdomains_report_markdown(data)
    assert "www.example.com" in output
    assert "None" not in output.split("## All Results", 1)[1]


def test_format_subdomains_report_markdown_per_depth_non_dict_entries() -> None:
    """Non-dict per_depth entries are skipped (line 329)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [],
        "all_results": [],
        "per_depth": [
            "not-a-dict",
            {
                "depth": 1,
                "subdomains_tested": 2,
                "resolved_count": 1,
                "results": [
                    {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
                ],
            },
        ],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_subdomains_report_markdown(data)
    assert "### Depth 1" in output
    assert "dev.www.example.com" in output
    assert "not-a-dict" not in output


def test_format_subdomains_report_markdown_recursive_results_non_dict_entries() -> None:
    """Non-dict entries in a depth's results are skipped (line 342)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [],
        "all_results": [],
        "per_depth": [
            {
                "depth": 1,
                "subdomains_tested": 2,
                "resolved_count": 1,
                "results": [
                    [],
                    {"subdomain": "dev", "hostname": "dev.www.example.com", "ip": "1.2.3.5"},
                ],
            },
        ],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_subdomains_report_markdown(data)
    assert "dev.www.example.com" in output


def test_format_subdomains_report_csv_all_results_non_dict_entries() -> None:
    """Non-dict entries in all_results are skipped by the CSV formatter (line 360)."""
    data = {
        "all_results": [
            "not-a-dict",
            123,
            {"subdomain": "www", "hostname": "www.example.com", "ip": "1.2.3.4"},
        ]
    }
    output = format_subdomains_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "subdomain,hostname,ip,resolved"
    assert "www,www.example.com,1.2.3.4,true" in lines
    assert not any("not-a-dict" in line for line in lines)
    assert not any(",123," in line for line in lines)