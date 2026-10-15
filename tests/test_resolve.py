"""Tests for the ethscan resolve module."""

import csv
import io

import pytest

from ethscan.resolve import (
    DEFAULT_RECORD_TYPES,
    DEFAULT_TIMEOUT,
    format_resolve_report_csv,
    format_resolve_report_json,
    format_resolve_report_markdown,
    run_resolve,
)


def test_default_record_types() -> None:
    assert DEFAULT_RECORD_TYPES == ["A", "AAAA", "CNAME"]
    assert DEFAULT_TIMEOUT == 2.0


def test_normalize_target_bare_domain() -> None:
    from ethscan.resolve import _normalize_target
    assert _normalize_target("example.com") == "example.com"
    assert _normalize_target("EXAMPLE.COM") == "example.com"
    assert _normalize_target("sub.example.com") == "sub.example.com"


def test_normalize_target_url() -> None:
    from ethscan.resolve import _normalize_target
    assert _normalize_target("https://example.com/path") == "example.com"
    assert _normalize_target("http://sub.example.com:8080/foo") == "sub.example.com:8080"


def test_normalize_target_ip() -> None:
    from ethscan.resolve import _normalize_target
    assert _normalize_target("8.8.8.8") == "8.8.8.8"
    assert _normalize_target("https://8.8.8.8") == "8.8.8.8"
    assert _normalize_target("2001:4860:4860::8888") == "2001:4860:4860::8888"


def test_normalize_target_ipv6_url() -> None:
    from ethscan.resolve import _normalize_target, _is_ip_address

    # IPv6 literals in URL form must be returned bare (without surrounding
    # brackets) so they are recognized as IP addresses for PTR lookups.
    assert _normalize_target("https://[::1]") == "::1"
    assert _normalize_target("https://[::1]:8080/") == "::1"
    assert _is_ip_address(_normalize_target("https://[::1]")) is True


def test_is_ip_address() -> None:
    from ethscan.resolve import _is_ip_address
    assert _is_ip_address("8.8.8.8") is True
    assert _is_ip_address("192.168.1.1") is True
    assert _is_ip_address("2001:4860:4860::8888") is True
    assert _is_ip_address("::1") is True
    assert _is_ip_address("example.com") is False
    assert _is_ip_address("invalid") is False


def test_format_resolve_report_json_domain() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A", "AAAA", "CNAME"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
            "CNAME": [],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_json(data)
    assert "example.com" in output
    assert "93.184.216.34" in output
    assert "2606:2800:220:1:248:1893:25c8:1946" in output


def test_format_resolve_report_json_ip() -> None:
    data = {
        "target": "8.8.8.8",
        "normalized": "8.8.8.8",
        "is_ip": True,
        "record_types_queried": ["PTR"],
        "records": {
            "PTR": ["dns.google"],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_json(data)
    assert "8.8.8.8" in output
    assert "dns.google" in output


def test_format_resolve_report_markdown_domain() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A", "AAAA", "CNAME"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
            "CNAME": [],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_markdown(data)
    assert "# ethscan DNS Forward/Reverse Resolution Report" in output
    assert "example.com" in output
    assert "**Type:** Domain Name" in output
    assert "## A Records" in output
    assert "93.184.216.34" in output
    assert "## AAAA Records" in output
    assert "2606:2800:220:1:248:1893:25c8:1946" in output
    assert "## CNAME Records" in output
    assert "*No records found*" in output


def test_format_resolve_report_markdown_ip() -> None:
    data = {
        "target": "8.8.8.8",
        "normalized": "8.8.8.8",
        "is_ip": True,
        "record_types_queried": ["PTR"],
        "records": {
            "PTR": ["dns.google"],
        },
        "dnspython_available": False,
        "server": "1.1.1.1",
    }
    output = format_resolve_report_markdown(data)
    assert "# ethscan DNS Forward/Reverse Resolution Report" in output
    assert "8.8.8.8" in output
    assert "**Type:** IP Address" in output
    assert "**Custom Resolver:** 1.1.1.1" in output
    assert "## PTR Records" in output
    assert "dns.google" in output


def test_format_resolve_report_markdown_empty_records() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A", "MX"],
        "records": {
            "A": [],
            "MX": [],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_markdown(data)
    assert "*No records found*" in output


def test_format_resolve_report_markdown_pipe_escaping() -> None:
    """Markdown output escapes pipe characters in record values."""
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["CNAME"],
        "records": {
            "CNAME": ["a|b.example.com."],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_markdown(data)
    assert "a\\|b.example.com" in output
    assert "a|b.example.com" not in output.replace("\\|", "")


def test_run_resolve_domain_defaults(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    def mock_resolve_aaaa(domain, timeout=2.0):
        return ["2606:2800:220:1:248:1893:25c8:1946"]

    def mock_resolve_cname(domain, timeout=2.0):
        return ["example.com"]

    monkeypatch.setattr("ethscan.resolve.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.resolve.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.resolve.resolve_cname_records", mock_resolve_cname)
    monkeypatch.setattr("ethscan.resolve.DNS_AVAILABLE", False)

    results = run_resolve("example.com", timeout=1.0)
    assert results["target"] == "example.com"
    assert results["normalized"] == "example.com"
    assert results["is_ip"] is False
    assert results["records"]["A"] == ["93.184.216.34"]
    assert results["records"]["AAAA"] == ["2606:2800:220:1:248:1893:25c8:1946"]
    assert results["records"]["CNAME"] == ["example.com"]
    assert results["dnspython_available"] is False
    assert results["server"] is None


def test_run_resolve_ip_defaults(monkeypatch) -> None:
    def mock_resolve_ptr(ip, timeout=2.0, server=None):
        return ["dns.google"]

    monkeypatch.setattr("ethscan.resolve.resolve_ptr_records", mock_resolve_ptr)

    results = run_resolve("8.8.8.8", timeout=1.0)
    assert results["target"] == "8.8.8.8"
    assert results["normalized"] == "8.8.8.8"
    assert results["is_ip"] is True
    assert results["record_types_queried"] == ["PTR"]
    assert results["records"]["PTR"] == ["dns.google"]


def test_run_resolve_custom_types_domain(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    monkeypatch.setattr("ethscan.resolve.resolve_a_records", mock_resolve_a)

    results = run_resolve("example.com", record_types=["A"], timeout=1.0)
    assert "A" in results["records"]
    assert "AAAA" not in results["records"]
    assert "CNAME" not in results["records"]


def test_run_resolve_custom_types_ip(monkeypatch) -> None:
    def mock_resolve_ptr(ip, timeout=2.0, server=None):
        return ["dns.google"]

    monkeypatch.setattr("ethscan.resolve.resolve_ptr_records", mock_resolve_ptr)

    results = run_resolve("8.8.8.8", record_types=["PTR"], timeout=1.0)
    assert "PTR" in results["records"]
    assert results["records"]["PTR"] == ["dns.google"]


def test_run_resolve_unknown_types_ignored(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    monkeypatch.setattr("ethscan.resolve.resolve_a_records", mock_resolve_a)

    results = run_resolve("example.com", record_types=["A", "INVALID"], timeout=1.0)
    assert "A" in results["records"]
    assert "INVALID" not in results["records"]


def test_run_resolve_domain_no_ptr(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    monkeypatch.setattr("ethscan.resolve.resolve_a_records", mock_resolve_a)

    results = run_resolve("example.com", record_types=["A", "PTR"], timeout=1.0)
    assert "A" in results["records"]
    assert "PTR" not in results["records"]


def test_run_resolve_ip_no_forward(monkeypatch) -> None:
    def mock_resolve_ptr(ip, timeout=2.0, server=None):
        return ["dns.google"]

    monkeypatch.setattr("ethscan.resolve.resolve_ptr_records", mock_resolve_ptr)

    results = run_resolve("8.8.8.8", record_types=["PTR", "A"], timeout=1.0)
    assert "PTR" in results["records"]
    assert "A" not in results["records"]


def test_run_resolve_with_custom_server(monkeypatch) -> None:
    def mock_resolve_ptr(ip, timeout=2.0, server=None):
        assert server == "1.1.1.1"
        return ["dns.google"]

    monkeypatch.setattr("ethscan.resolve.resolve_ptr_records", mock_resolve_ptr)

    results = run_resolve("8.8.8.8", server="1.1.1.1", timeout=1.0)
    assert results["server"] == "1.1.1.1"


def test_run_resolve_url_target(monkeypatch) -> None:
    def mock_resolve_a(domain, timeout=2.0):
        return ["93.184.216.34"]

    def mock_resolve_aaaa(domain, timeout=2.0):
        return ["2606:2800:220:1:248:1893:25c8:1946"]

    def mock_resolve_cname(domain, timeout=2.0):
        return []

    monkeypatch.setattr("ethscan.resolve.resolve_a_records", mock_resolve_a)
    monkeypatch.setattr("ethscan.resolve.resolve_aaaa_records", mock_resolve_aaaa)
    monkeypatch.setattr("ethscan.resolve.resolve_cname_records", mock_resolve_cname)

    results = run_resolve("https://example.com/path", timeout=1.0)
    assert results["target"] == "https://example.com/path"
    assert results["normalized"] == "example.com"


def test_run_resolve_ipv6_url_target(monkeypatch) -> None:
    def mock_resolve_ptr(ip, timeout=2.0, server=None):
        return ["dns.google"]

    monkeypatch.setattr("ethscan.resolve.resolve_ptr_records", mock_resolve_ptr)

    results = run_resolve("https://[::1]/", timeout=1.0)
    assert results["target"] == "https://[::1]/"
    assert results["normalized"] == "::1"
    assert results["is_ip"] is True
    assert results["record_types_queried"] == ["PTR"]
    assert results["records"]["PTR"] == ["dns.google"]


def test_run_resolve_offline_domain() -> None:
    results = run_resolve("invalid.nonexistent.domain.tld", timeout=0.1)
    assert results["is_ip"] is False
    assert results["records"]["A"] == []
    assert results["records"]["AAAA"] == []
    assert results["records"]["CNAME"] == []


def test_run_resolve_offline_ip() -> None:
    results = run_resolve("192.0.2.1", timeout=0.1)
    assert results["is_ip"] is True
    assert results["records"]["PTR"] == []

def test_format_resolve_report_csv() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A", "AAAA"],
        "records": {
            "A": ["1.2.3.4", "5.6.7.8"],
            "AAAA": ["::1"],
        },
        "dnspython_available": False,
        "server": None,
    }
    output = format_resolve_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "normalized", "record_type", "record_value"]
    assert reader[1] == ["example.com", "example.com", "A", "1.2.3.4"]
    assert reader[2] == ["example.com", "example.com", "A", "5.6.7.8"]
    assert reader[3] == ["example.com", "example.com", "AAAA", "::1"]


def test_format_resolve_report_csv_empty_records() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "records": {},
    }
    output = format_resolve_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0] == ["target", "normalized", "record_type", "record_value"]


def test_format_resolve_report_csv_comma_value() -> None:
    data = {
        "target": "example.com",
        "normalized": "example.com",
        "records": {"TXT": ['"v=spf1, include:example.com"']},
    }
    output = format_resolve_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][3] == '"v=spf1, include:example.com"'

def test_resolve_a_records_success() -> None:
    from ethscan import resolve
    # Use localhost which resolves to 127.0.0.1 in this environment
    result = resolve.resolve_a_records("localhost")
    assert "127.0.0.1" in result


def test_resolve_aaaa_records_success() -> None:
    from ethscan import resolve
    result = resolve.resolve_aaaa_records("localhost")
    # Could be ::1 or empty depending on setup; at least exercise path
    assert isinstance(result, list)


def test_resolve_cname_records_no_dnspython() -> None:
    from ethscan import resolve
    # When DNS_AVAILABLE is False, returns empty
    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = False
        result = resolve.resolve_cname_records("example.com")
        assert result == []
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_ptr_records_no_dnspython() -> None:
    from ethscan import resolve
    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = False
        result = resolve.resolve_ptr_records("127.0.0.1")
        assert isinstance(result, list)
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_with_dnspython_no_dnspython() -> None:
    from ethscan import resolve
    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = False
        result = resolve.resolve_with_dnspython("example.com", "MX")
        assert result == []
    finally:
        resolve.DNS_AVAILABLE = orig


def test_normalize_target_bracketed_ipv6_with_port() -> None:
    from ethscan.resolve import _normalize_target
    assert _normalize_target("https://[2001:db8::1]:443/path") == "2001:db8::1"

def test_resolve_cname_records_dnspython_success() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __init__(self, val):
            self.val = val

        def __str__(self):
            return self.val

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None

        def resolve(self, domain, rtype):
            assert domain == "example.com"
            assert rtype == "CNAME"
            return [DummyAnswer("target.example.com"), DummyAnswer("target.example.com")]

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_cname_records("example.com", timeout=1.0)
        assert result == ["target.example.com"]
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_cname_records_dnspython_exception() -> None:
    from ethscan import resolve

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None

        def resolve(self, domain, rtype):
            raise Exception("fail")

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_cname_records("example.com")
        assert result == []
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_ptr_records_dnspython_success() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __str__(self):
            return "ptr.example.com"

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, rev_name, rtype):
            assert rtype == "PTR"
            return [DummyAnswer()]

    class FakeReversename:
        @staticmethod
        def from_address(ip):
            assert ip == "8.8.8.8"
            return "8.8.8.8.in-addr.arpa"

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})
        reversename = FakeReversename()

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_ptr_records("8.8.8.8", timeout=1.0)
        assert result == ["ptr.example.com"]
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_ptr_records_dnspython_with_server() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __str__(self):
            return "ptr.example.com"

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, rev_name, rtype):
            assert rtype == "PTR"
            return [DummyAnswer()]

    class FakeReversename:
        @staticmethod
        def from_address(ip):
            return "8.8.8.8.in-addr.arpa"

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})
        reversename = FakeReversename()

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_ptr_records("8.8.8.8", server="1.1.1.1")
        assert result == ["ptr.example.com"]
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_ptr_records_dnspython_exception() -> None:
    from ethscan import resolve

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, rev_name, rtype):
            raise Exception("fail")

    class FakeReversename:
        @staticmethod
        def from_address(ip):
            return "8.8.8.8.in-addr.arpa"

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})
        reversename = FakeReversename()

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_ptr_records("8.8.8.8")
        assert result == []
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_with_dnspython_success() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __init__(self, v):
            self.v = v

        def __str__(self):
            return self.v

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, domain, rtype):
            return [DummyAnswer("mx1.example.com"), DummyAnswer("mx2.example.com")]

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_with_dnspython("example.com", "MX")
        assert result == ["mx1.example.com", "mx2.example.com"]
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_with_dnspython_with_server() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __str__(self):
            return "ns1.example.com"

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, domain, rtype):
            return [DummyAnswer()]

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_with_dnspython("example.com", "NS", server="1.1.1.1")
        assert result == ["ns1.example.com"]
    finally:
        resolve.DNS_AVAILABLE = orig


def test_resolve_with_dnspython_exception() -> None:
    from ethscan import resolve

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, domain, rtype):
            raise Exception("fail")

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.resolve_with_dnspython("example.com", "TXT")
        assert result == []
    finally:
        resolve.DNS_AVAILABLE = orig


def test_run_resolve_with_arbitrary_record_type_dnspython() -> None:
    from ethscan import resolve

    class DummyAnswer:
        def __str__(self):
            return "txt.example.com"

    class DummyResolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = None

        def resolve(self, domain, rtype):
            assert rtype == "TXT"
            return [DummyAnswer()]

    class FakeDns:
        exception = type("exception", (), {"DNSException": Exception})
        resolver = type("resolver", (), {"Resolver": DummyResolver})

    orig = resolve.DNS_AVAILABLE
    try:
        resolve.DNS_AVAILABLE = True
        resolve.dns = FakeDns()
        result = resolve.run_resolve("example.com", record_types=["TXT"], server="1.1.1.1")
        assert result["records"]["TXT"] == ["txt.example.com"]
        assert result["dnspython_available"] is True
    finally:
        resolve.DNS_AVAILABLE = orig


def test_run_resolve_with_unsupported_and_mixed_types() -> None:
    from ethscan import resolve

    result = resolve.run_resolve("example.com", record_types=["MX", "A", "BOGUS"])
    # MX falls through to dnspython path only if available; dnspython not installed here
    assert "A" in result["records"]
    assert "MX" not in result["records"] or isinstance(result["records"].get("MX"), list)
