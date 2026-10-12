"""Tests for the ethscan dns module."""

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