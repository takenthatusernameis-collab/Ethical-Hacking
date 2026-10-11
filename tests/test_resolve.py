"""Tests for the ethscan resolve module."""

import pytest

from ethscan.resolve import (
    DEFAULT_RECORD_TYPES,
    DEFAULT_TIMEOUT,
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