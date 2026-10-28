"""Tests for the ethscan dns module."""

import socket
import threading

import pytest

from ethscan.dns import (
    DEFAULT_DNS_TYPES,
    DEFAULT_TIMEOUT,
    format_dns_report_csv,
    format_dns_report_json,
    format_dns_report_markdown,
    resolve_a_records,
    resolve_aaaa_records,
    run_dns,
)


def test_default_dns_types() -> None:
    assert DEFAULT_DNS_TYPES == ["A", "AAAA"]
    assert DEFAULT_TIMEOUT == 2.0


def test_normalize_domain_bare() -> None:
    from ethscan.dns import _normalize_domain
    assert _normalize_domain("example.com") == "example.com"
    assert _normalize_domain("EXAMPLE.COM") == "example.com"


def test_normalize_domain_url() -> None:
    from ethscan.dns import _normalize_domain
    assert _normalize_domain("https://example.com/path") == "example.com"
    assert _normalize_domain("http://sub.example.com:8080/foo") == "sub.example.com:8080"


def test_normalize_domain_ipv6_url() -> None:
    """IPv6 literals in URL form are returned bare (bracket stripping, line 41)."""
    from ethscan.dns import _normalize_domain
    assert _normalize_domain("https://[::1]/") == "::1"
    assert _normalize_domain("https://[2001:db8::1]:8080/path") == "2001:db8::1"


def test_format_dns_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "AAAA"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_json(data)
    assert "example.com" in output
    assert "93.184.216.34" in output
    assert "2606:2800:220:1:248:1893:25c8:1946" in output


def test_format_dns_report_markdown() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "AAAA"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_markdown(data)
    assert "# ethscan DNS Record Enumeration Report" in output
    assert "example.com" in output
    assert "## A Records" in output
    assert "93.184.216.34" in output
    assert "## AAAA Records" in output
    assert "2606:2800:220:1:248:1893:25c8:1946" in output


def test_format_dns_report_markdown_empty_records() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "MX"],
        "records": {
            "A": [],
            "MX": [],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_markdown(data)
    assert "*No records found*" in output


def test_run_dns_offline_basic(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    def mock_resolve_aaaa(domain, timeout=2.0):
        return ["2606:2800:220:1:248:1893:25c8:1946"]

    monkeypatch.setattr("ethscan.dns.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.dns.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.dns.DNS_AVAILABLE", False)

    results = run_dns("example.com", record_types=["A", "AAAA"], timeout=1.0)
    assert results["target"] == "example.com"
    assert results["domain"] == "example.com"
    assert results["records"]["A"] == ["93.184.216.34"]
    assert results["records"]["AAAA"] == ["2606:2800:220:1:248:1893:25c8:1946"]
    assert results["dnspython_available"] is False


def test_run_dns_unknown_types_ignored(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    monkeypatch.setattr("ethscan.dns.resolve_a_records", mock_resolve_a)

    results = run_dns("example.com", record_types=["A", "INVALID"], timeout=1.0)
    assert "A" in results["records"]
    assert "INVALID" not in results["records"]


def test_resolve_a_records_offline() -> None:
    results = resolve_a_records("invalid.nonexistent.domain.tld", timeout=0.1)
    assert results == []


def test_resolve_aaaa_records_offline() -> None:
    results = resolve_aaaa_records("invalid.nonexistent.domain.tld", timeout=0.1)
    assert results == []


def test_resolve_a_records_restores_default_socket_timeout(monkeypatch) -> None:
    """resolve_a_records restores the default socket timeout it temporarily set.

    The helper switches the process-wide default timeout for its own lookup and
    must restore it afterwards, so a later test does not inherit a 2s (or
    other) default timeout from this call.
    """

    def blocked(*args, **kwargs):
        raise socket.gaierror("blocked")

    monkeypatch.setattr("ethscan.dns.socket.getaddrinfo", blocked)
    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(123.0)
    try:
        assert resolve_a_records("example.invalid", timeout=0.1) == []
        assert socket.getdefaulttimeout() == 123.0
    finally:
        socket.setdefaulttimeout(previous)


def test_format_dns_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "AAAA"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert "example.com,example.com,A,93.184.216.34" in lines
    assert "example.com,example.com,AAAA,2606:2800:220:1:248:1893:25c8:1946" in lines


def test_format_dns_report_csv_empty() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "AAAA"],
        "records": {
            "A": [],
            "AAAA": [],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_csv(data)
    assert output == "target,domain,record_type,record_value"


def test_format_dns_report_csv_missing_fields() -> None:
    data = {
        "records": {},
    }
    output = format_dns_report_csv(data)
    assert output == "target,domain,record_type,record_value"


def test_format_dns_report_csv_pipe_escaping() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["CNAME"],
        "records": {
            "CNAME": ["alias.example.com", "weird,record.example.com"],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert "example.com,example.com,CNAME,alias.example.com" in lines
    # The value containing a comma must be CSV-quoted.
    assert any(line.endswith('"weird,record.example.com"') for line in lines)


def test_format_dns_report_csv_multiple_types() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": ["A", "MX", "NS"],
        "records": {
            "A": ["93.184.216.34", "93.184.216.35"],
            "MX": ["mail.example.com"],
            "NS": ["ns1.example.com", "ns2.example.com"],
        },
        "dnspython_available": False,
    }
    output = format_dns_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert len(lines) == 1 + 2 + 1 + 2
    assert "example.com,example.com,A,93.184.216.34" in lines
    assert "example.com,example.com,A,93.184.216.35" in lines
    assert "example.com,example.com,MX,mail.example.com" in lines
    assert "example.com,example.com,NS,ns1.example.com" in lines
    assert "example.com,example.com,NS,ns2.example.com" in lines


def test_run_dns_workers_sequential(monkeypatch) -> None:
    """Test that workers=1 runs sequentially (order preserved)."""
    call_order = []

    def mock_resolve_a(domain, timeout=2.0):
        call_order.append(("A", timeout))
        return ["1.2.3.4"]

    def mock_resolve_aaaa(domain, timeout=2.0):
        call_order.append(("AAAA", timeout))
        return ["2001:db8::1"]

    def mock_resolve_with_dnspython(domain, record_type, timeout=2.0):
        call_order.append((record_type, timeout))
        return [f"mocked-{record_type}"]

    monkeypatch.setattr("ethscan.dns.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.dns.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.dns.resolve_with_dnspython", mock_resolve_with_dnspython)

    # Test with multiple record types
    results = run_dns(
        "example.com",
        record_types=["A", "AAAA", "MX"],
        timeout=1.0,
        workers=1,
    )

    # Check that the functions were called in the order of the input list
    expected_order = [("A", 1.0), ("AAAA", 1.0), ("MX", 1.0)]
    assert call_order == expected_order

    # Check results
    assert results["records"]["A"] == ["1.2.3.4"]
    assert results["records"]["AAAA"] == ["2001:db8::1"]
    assert results["records"]["MX"] == ["mocked-MX"]

    # Also check that the records dictionary keys are in the input order
    assert list(results["records"].keys()) == ["A", "AAAA", "MX"]


def test_run_dns_workers_parallel(monkeypatch) -> None:
    """Test that workers>1 runs in parallel (all record types processed)."""
    call_order = []
    call_lock = threading.Lock()

    def mock_resolve_a(domain, timeout=2.0):
        with call_lock:
            call_order.append(("A", timeout))
        return ["1.2.3.4"]

    def mock_resolve_aaaa(domain, timeout=2.0):
        with call_lock:
            call_order.append(("AAAA", timeout))
        return ["2001:db8::1"]

    def mock_resolve_with_dnspython(domain, record_type, timeout=2.0):
        with call_lock:
            call_order.append((record_type, timeout))
        return [f"mocked-{record_type}"]

    monkeypatch.setattr("ethscan.dns.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.dns.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.dns.resolve_with_dnspython", mock_resolve_with_dnspython)

    # Test with multiple record types and workers=2
    results = run_dns(
        "example.com",
        record_types=["A", "AAAA", "MX"],
        timeout=1.0,
        workers=2,
    )

    # All three functions should have been called
    assert len(call_order) == 3
    # The order of calls may vary due to concurrency, but each should be called once with the correct timeout
    for call in call_order:
        assert call[1] == 1.0  # timeout
    # We can also check that the set of record types called is correct
    called_types = {call[0] for call in call_order}
    assert called_types == {"A", "AAAA", "MX"}

    # Check results
    assert results["records"]["A"] == ["1.2.3.4"]
    assert results["records"]["AAAA"] == ["2001:db8::1"]
    assert results["records"]["MX"] == ["mocked-MX"]

    # Additionally, we can check that the records dictionary keys are in the input order
    # (insertion order preserved)
    assert list(results["records"].keys()) == ["A", "AAAA", "MX"]


def test_resolve_a_records_localhost() -> None:
    """resolve_a_records success path returns sorted unique IPv4 (lines 58-59)."""
    results = resolve_a_records("localhost", timeout=2.0)
    assert "127.0.0.1" in results
    assert results == sorted(set(results))


def test_resolve_aaaa_records_offline_ipv6() -> None:
    """resolve_aaaa_records returns [] for an unresolvable name (socket.gaierror path)."""
    results = resolve_aaaa_records("invalid.nonexistent.domain.tld", timeout=0.1)
    assert results == []


def test_resolve_aaaa_records_localhost() -> None:
    """resolve_aaaa_records success path returns sorted unique IPv6 (lines 77-78)."""
    results = resolve_aaaa_records("localhost", timeout=2.0)
    assert "::1" in results
    assert results == sorted(set(results))


def test_resolve_with_dnspython_unavailable() -> None:
    """resolve_with_dnspython returns [] when DNS_AVAILABLE is False (line 96-97)."""
    import ethscan.dns as dns_mod

    original = dns_mod.DNS_AVAILABLE
    dns_mod.DNS_AVAILABLE = False
    try:
        assert dns_mod.resolve_with_dnspython("example.com", "MX", 0.1) == []
    finally:
        dns_mod.DNS_AVAILABLE = original


def _install_fake_dns(monkeypatch, resolver_resolve, dns_exception=None):
    """Inject a fake dns package into ethscan.dns so dnspython paths are testable."""
    import types

    import ethscan.dns as dns_mod

    fake_dns = types.ModuleType("dns")
    fake_dns.resolver = types.ModuleType("dns.resolver")
    fake_dns.exception = types.ModuleType("dns.exception")

    class DNSException(Exception):
        pass

    fake_dns.exception.DNSException = dns_exception or DNSException

    class FakeResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, domain, rdtype):
            return resolver_resolve(domain, rdtype, self)

    fake_dns.resolver.Resolver = FakeResolver
    monkeypatch.setattr(dns_mod, "dns", fake_dns, raising=False)
    monkeypatch.setattr(dns_mod, "DNS_AVAILABLE", True)


def test_resolve_with_dnspython_success(monkeypatch) -> None:
    """resolve_with_dnspython returns sorted unique rdata strings (lines 100-105)."""
    def fake_resolve(domain, rdtype, self):
        assert domain == "example.com"
        assert rdtype == "MX"
        assert self.timeout == 1.0
        assert self.lifetime == 1.0

        class Rdata:
            def __str__(self_):
                return self_.value

            def __init__(self_, value):
                self_.value = value

        return [Rdata("mail.example.com"), Rdata("mail.example.com"), Rdata("mail2.example.com")]

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    result = dns_mod.resolve_with_dnspython("example.com", "MX", timeout=1.0)
    assert result == ["mail.example.com", "mail2.example.com"]


def test_resolve_with_dnspython_dns_exception(monkeypatch) -> None:
    """resolve_with_dnspython swallows dns.exception.DNSException (line 106-107)."""
    class MyDNSException(Exception):
        pass

    def fake_resolve(domain, rdtype, self):
        raise MyDNSException("boom")

    _install_fake_dns(monkeypatch, fake_resolve, dns_exception=MyDNSException)

    import ethscan.dns as dns_mod
    assert dns_mod.resolve_with_dnspython("example.com", "MX", 0.1) == []


def test_resolve_with_dnspython_oserror(monkeypatch) -> None:
    """resolve_with_dnspython swallows OSError (line 106-107)."""
    def fake_resolve(domain, rdtype, self):
        raise OSError("network down")

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    assert dns_mod.resolve_with_dnspython("example.com", "MX", 0.1) == []


def test_resolve_with_dnspython_valueerror(monkeypatch) -> None:
    """resolve_with_dnspython swallows ValueError (line 106-107)."""
    def fake_resolve(domain, rdtype, self):
        raise ValueError("bad input")

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    assert dns_mod.resolve_with_dnspython("example.com", "MX", 0.1) == []


def test_run_dns_custom_server_success(monkeypatch) -> None:
    """run_dns uses the custom-server dnspython path (lines 145-152)."""
    seen = {}

    def fake_resolve(domain, rdtype, self):
        seen["domain"] = domain
        seen["rdtype"] = rdtype
        seen["nameservers"] = self.nameservers
        seen["timeout"] = self.timeout

        class Rdata:
            def __str__(self_):
                return "mocked.example.com"

        return [Rdata()]

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX"], server="1.1.1.1", timeout=1.0)
    assert seen["nameservers"] == ["1.1.1.1"]
    assert seen["timeout"] == 1.0
    assert results["records"]["MX"] == ["mocked.example.com"]
    assert results["dnspython_available"] is True


def test_run_dns_custom_server_dns_exception(monkeypatch) -> None:
    """run_dns custom-server path swallows DNSException (lines 153-154)."""
    class MyDNSException(Exception):
        pass

    def fake_resolve(domain, rdtype, self):
        raise MyDNSException("boom")

    _install_fake_dns(monkeypatch, fake_resolve, dns_exception=MyDNSException)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX"], server="1.1.1.1", timeout=1.0)
    assert results["records"]["MX"] == []


def test_run_dns_custom_server_oserror(monkeypatch) -> None:
    """run_dns custom-server path swallows OSError (lines 153-154)."""
    def fake_resolve(domain, rdtype, self):
        raise OSError("network down")

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX"], server="1.1.1.1", timeout=1.0)
    assert results["records"]["MX"] == []


def test_run_dns_custom_server_valueerror(monkeypatch) -> None:
    """run_dns custom-server path swallows ValueError (lines 153-154)."""
    def fake_resolve(domain, rdtype, self):
        raise ValueError("bad input")

    _install_fake_dns(monkeypatch, fake_resolve)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX"], server="1.1.1.1", timeout=1.0)
    assert results["records"]["MX"] == []


def test_run_dns_dnspython_unavailable_returns_empty(monkeypatch) -> None:
    """run_dns returns [] for non-A/AAAA types when DNS_AVAILABLE is False (lines 157-158)."""
    monkeypatch.setattr("ethscan.dns.DNS_AVAILABLE", False)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX"], timeout=1.0)
    assert results["records"]["MX"] == []
    assert results["dnspython_available"] is False


def test_run_dns_dnspython_path_without_server(monkeypatch) -> None:
    """run_dns delegates to resolve_with_dnspython when DNS_AVAILABLE and no server (line 156)."""
    calls = []

    def fake_resolve_with_dnspython(domain, record_type, timeout=2.0):
        calls.append((domain, record_type, timeout))
        return [f"r:{record_type}"]

    monkeypatch.setattr("ethscan.dns.resolve_with_dnspython", fake_resolve_with_dnspython)
    monkeypatch.setattr("ethscan.dns.DNS_AVAILABLE", True)

    import ethscan.dns as dns_mod
    results = dns_mod.run_dns("example.com", record_types=["MX", "NS"], timeout=1.0)
    assert calls == [("example.com", "MX", 1.0), ("example.com", "NS", 1.0)]
    assert results["records"]["MX"] == ["r:MX"]
    assert results["records"]["NS"] == ["r:NS"]
    assert results["dnspython_available"] is True


def test_dns_availability_flag_true(monkeypatch) -> None:
    """DNS_AVAILABLE is True when the dns package imports cleanly (lines 11-12)."""
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
            pass

        def resolve(self, domain, rdtype):
            return []

    dns_resolver.Resolver = Resolver
    dns_pkg.resolver = dns_resolver
    dns_pkg.exception = dns_exception

    monkeypatch.setitem(sys.modules, "dns", dns_pkg)
    monkeypatch.setitem(sys.modules, "dns.resolver", dns_resolver)
    monkeypatch.setitem(sys.modules, "dns.exception", dns_exception)

    import ethscan.dns as dns_mod
    reload(dns_mod)
    try:
        assert dns_mod.DNS_AVAILABLE is True
    finally:
        monkeypatch.delitem(sys.modules, "dns", raising=False)
        monkeypatch.delitem(sys.modules, "dns.resolver", raising=False)
        monkeypatch.delitem(sys.modules, "dns.message", raising=False)
        monkeypatch.delitem(sys.modules, "dns.exception", raising=False)
        reload(dns_mod)


ESCAPE_TYPES = [
    pytest.param(IndexError, id="indexerror"),
    pytest.param(AttributeError, id="attributeerror"),
    pytest.param(KeyError, id="keyerror"),
]


def _make_raise_resolve(exc):
    def fake_resolve(domain, rdtype, self):
        raise exc("boom")

    return fake_resolve


@pytest.mark.parametrize("exc", ESCAPE_TYPES)
def test_resolve_with_dnspython_swallows_unlisted_exceptions(monkeypatch, exc):
    """resolve_with_dnspython returns [] instead of raising IndexError/AttributeError/KeyError (line 107)."""
    _install_fake_dns(monkeypatch, _make_raise_resolve(exc))
    import ethscan.dns as dns_mod

    assert dns_mod.resolve_with_dnspython("example.com", "MX", 0.1) == []


@pytest.mark.parametrize("exc", ESCAPE_TYPES)
def test_run_dns_mx_swallows_unlisted_exceptions(monkeypatch, exc):
    """run_dns dnspython path (no server) returns [] for MX on unlisted exceptions (line 156)."""
    _install_fake_dns(monkeypatch, _make_raise_resolve(exc))
    import ethscan.dns as dns_mod

    results = dns_mod.run_dns("example.com", record_types=["MX"], timeout=0.1)
    assert results["records"]["MX"] == []


@pytest.mark.parametrize("exc", ESCAPE_TYPES)
def test_run_dns_custom_server_swallows_unlisted_exceptions(monkeypatch, exc):
    """run_dns custom-server dnspython path returns [] for MX on unlisted exceptions (line 154)."""
    _install_fake_dns(monkeypatch, _make_raise_resolve(exc))
    import ethscan.dns as dns_mod

    results = dns_mod.run_dns(
        "example.com", record_types=["MX"], server="1.1.1.1", timeout=0.1
    )
    assert results["records"]["MX"] == []


def test_dns_availability_flag_false(monkeypatch) -> None:
    """DNS_AVAILABLE is False when dns is not importable (the except branch)."""
    import sys
    from importlib import reload

    monkeypatch.setitem(sys.modules, "dns", None)  # forces ImportError on import dns
    import ethscan.dns as dns_mod
    reload(dns_mod)
    try:
        assert dns_mod.DNS_AVAILABLE is False
    finally:
        monkeypatch.delitem(sys.modules, "dns", raising=False)
        reload(dns_mod)


def test_dns_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A failing stdlib resolution is reported as empty records, not raised."""
    import ethscan.dns

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.dns.socket.getaddrinfo", boom)

    results = ethscan.dns.run_dns("example.com")

    assert isinstance(results, dict)
    assert results["records"]["A"] == []

def test_run_dns_server_without_dnspython_returns_empty(monkeypatch) -> None:
    import ethscan.dns as dns_mod
    monkeypatch.setattr(dns_mod, "DNS_AVAILABLE", False)
    data = dns_mod.run_dns("example.com", record_types=["MX"], server="8.8.8.8")
    assert data["records"]["MX"] == []


def test_run_dns_resolver_unexpected_exception_is_swallowed(monkeypatch) -> None:
    """run_dns swallows an unexpected exception raised inside resolve_type (lines 172-173)."""

    def raising_resolve_a(domain, timeout=2.0):
        raise RuntimeError("unexpected resolver failure")

    monkeypatch.setattr("ethscan.dns.resolve_a_records", raising_resolve_a)

    results = run_dns("example.com", record_types=["A"], timeout=1.0, workers=1)
    assert results["records"]["A"] == []


def test_format_dns_report_markdown_records_not_dict() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "record_types_queried": "A",
        "records": "not-a-dict",
        "dnspython_available": False,
    }
    out = format_dns_report_markdown(data)
    assert "Record Types Queried:** A" in out
    assert "example.com" in out


def test_format_dns_report_csv_non_list_values() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "records": {"TXT": "single-value"},
    }
    out = format_dns_report_csv(data)
    assert "single-value" in out


class _RaisingFuture:
    def result(self):
        raise RuntimeError("boom")


class _RaisingExecutor:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, *a, **k):
        return _RaisingFuture()


def test_run_dns_parallel_future_result_raises(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dns.ThreadPoolExecutor", _RaisingExecutor)
    results = run_dns("example.com", record_types=["A", "MX"], timeout=1.0, workers=2)
    assert results["records"]["A"] == []
    assert results["records"]["MX"] == []


class _ExplodingExecutor:
    def __init__(self, *a, **k):
        raise RuntimeError("boom")


def test_run_dns_parallel_executor_raises(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dns.ThreadPoolExecutor", _ExplodingExecutor)
    results = run_dns("example.com", record_types=["A", "MX"], timeout=1.0, workers=2)
    assert results["records"]["A"] == []
    assert results["records"]["MX"] == []
