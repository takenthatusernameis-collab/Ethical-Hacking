"""Tests for the ethscan whois module."""

import socket

import pytest

from ethscan.whois import (
    DEFAULT_RECURSIVE_DEPTH,
    DEFAULT_WHOIS_SERVER,
    DEFAULT_TIMEOUT,
    extract_referral_server,
    format_whois_report_csv,
    format_whois_report_json,
    format_whois_report_markdown,
    parse_whois,
    query_whois,
    run_whois,
)


def test_default_whois_server() -> None:
    assert DEFAULT_WHOIS_SERVER == "whois.iana.org"
    assert DEFAULT_TIMEOUT == 5.0


def test_parse_whois_registrar() -> None:
    raw = "Registrar: Example Registrar, Inc.\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Example Registrar, Inc."


def test_parse_whois_creation_date() -> None:
    raw = "Creation Date: 2020-01-15T10:30:00Z\n"
    parsed = parse_whois(raw)
    assert parsed["creation_date"] == "2020-01-15T10:30:00Z"


def test_parse_whois_expiration_date() -> None:
    raw = "Expiration Date: 2025-01-15T10:30:00Z\n"
    parsed = parse_whois(raw)
    assert parsed["expiration_date"] == "2025-01-15T10:30:00Z"


def test_parse_whois_nameservers() -> None:
    raw = "Name Server: ns1.example.com\nName Server: ns2.example.com\n"
    parsed = parse_whois(raw)
    assert "ns1.example.com" in parsed["nameservers"]
    assert "ns2.example.com" in parsed["nameservers"]


def test_parse_whois_status_codes() -> None:
    raw = "Status: clientTransferProhibited\nStatus: clientUpdateProhibited\n"
    parsed = parse_whois(raw)
    assert "clientTransferProhibited" in parsed["status_codes"]
    assert "clientUpdateProhibited" in parsed["status_codes"]


def test_parse_whois_registrant_org() -> None:
    raw = "Registrant Organization: Example Corp\n"
    parsed = parse_whois(raw)
    assert parsed["registrant_org"] == "Example Corp"


def test_parse_whois_case_insensitive() -> None:
    raw = "registrar: test registrar\nCREATION DATE: 2020-01-01\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "test registrar"
    assert parsed["creation_date"] == "2020-01-01"


def test_parse_whois_multiple_patterns() -> None:
    raw = "Sponsoring Registrar: Registrar A\nRegistrar Name: Registrar B\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Registrar A"


def test_format_whois_report_json() -> None:
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "test raw",
        "parsed": {
            "registrar": "Test Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": "Test Org",
            "status_codes": ["clientTransferProhibited"],
            "raw": "test raw",
        },
    }
    output = format_whois_report_json(data)
    assert "example.com" in output
    assert "Test Registrar" in output
    assert "clientTransferProhibited" in output


def test_format_whois_report_markdown() -> None:
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "test raw",
        "parsed": {
            "registrar": "Test Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": "Test Org",
            "status_codes": ["clientTransferProhibited"],
            "raw": "test raw",
        },
    }
    output = format_whois_report_markdown(data)
    assert "# ethscan WHOIS Lookup Report" in output
    assert "example.com" in output
    assert "Test Registrar" in output
    assert "## Nameservers" in output
    assert "ns1.example.com" in output
    assert "## Status Codes" in output
    assert "clientTransferProhibited" in output
    assert "## Raw Response" in output


def test_format_whois_report_markdown_empty_fields() -> None:
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "no data",
        "parsed": {
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "nameservers": [],
            "registrant_org": None,
            "status_codes": [],
            "raw": "no data",
        },
    }
    output = format_whois_report_markdown(data)
    assert "N/A" in output
    assert "## Nameservers" not in output
    assert "## Status Codes" not in output


def test_run_whois_offline(monkeypatch) -> None:
    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        return "Registrar: Test Registrar\nCreation Date: 2020-01-01\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", timeout=1.0)
    assert results["target"] == "example.com"
    assert results["server"] == "whois.iana.org"
    assert results["port"] == 43
    assert "Registrar: Test Registrar" in results["raw"]
    assert results["parsed"]["registrar"] == "Test Registrar"
    assert results["parsed"]["creation_date"] == "2020-01-01"


def test_query_whois_invalid_target() -> None:
    with pytest.raises((socket.gaierror, socket.timeout, ConnectionRefusedError, OSError)):
        query_whois("invalid.tld", server="127.0.0.1", port=43, timeout=0.1)


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_whois_report_csv_basic() -> None:
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "parsed": {
            "registrar": "Example Registrar",
            "creation_date": "1995-08-14",
            "expiration_date": "2025-08-13",
            "registrant_org": "Example Org",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
            "status_codes": ["ok"],
        },
    }
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target,example.com" in lines
    assert "server,whois.iana.org" in lines
    assert "port,43" in lines
    assert "registrar,Example Registrar" in lines
    assert "nameservers,ns1.example.com;ns2.example.com" in lines
    assert "status_codes,ok" in lines


def test_format_whois_report_csv_empty() -> None:
    data = {"target": "example.com"}
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target,example.com" in lines
    assert "registrar," in lines


def test_format_whois_report_csv_missing_fields() -> None:
    data = {}
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target," in lines


def test_format_whois_report_csv_recursive_hops() -> None:
    data = {
        "target": "example.com",
        "parsed": {"registrar": "Registrar A"},
        "recursive_hops": [
            {
                "depth": 1,
                "server": "whois.registrar.net",
                "port": 43,
                "parsed": {
                    "registrar": "Registrar B",
                    "nameservers": ["ns1.registrar.net"],
                },
                "referral_server": "whois.registrar.net",
            },
        ],
    }
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert "registrar,Registrar A" in lines
    assert any("recursive_hop_depth" in line for line in lines)
    assert any("1,whois.registrar.net,43,Registrar B" in line for line in lines)


def test_format_whois_report_csv_escaping() -> None:
    data = {
        "target": "example.com",
        "parsed": {
            "registrar": "Registrar, Inc.",
            "registrant_org": 'Org "quoted"',
        },
    }
    output = format_whois_report_csv(data)
    assert '"Registrar, Inc."' in output
    assert '"Org ""quoted"""' in output