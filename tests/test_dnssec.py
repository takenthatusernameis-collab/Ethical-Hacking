"""Tests for the ethscan dnssec module."""

import csv
import io

import pytest

from ethscan.dnssec import (
    DEFAULT_TIMEOUT,
    ALGORITHM_NAMES,
    DIGEST_TYPE_NAMES,
    DNS_AVAILABLE,
    format_dnssec_report_csv,
    format_dnssec_report_json,
    format_dnssec_report_markdown,
    run_dnssec,
)


def test_default_timeout() -> None:
    assert DEFAULT_TIMEOUT == 5.0


def test_algorithm_names() -> None:
    assert ALGORITHM_NAMES[8] == "RSASHA256"
    assert ALGORITHM_NAMES[13] == "ED25519"
    assert 1 in ALGORITHM_NAMES


def test_digest_type_names() -> None:
    assert DIGEST_TYPE_NAMES[1] == "SHA-1"
    assert DIGEST_TYPE_NAMES[2] == "SHA-256"
    assert 4 in DIGEST_TYPE_NAMES


def test_normalize_domain_bare() -> None:
    from ethscan.dnssec import _normalize_domain
    assert _normalize_domain("example.com") == "example.com"
    assert _normalize_domain("EXAMPLE.COM") == "example.com"


def test_normalize_domain_url() -> None:
    from ethscan.dnssec import _normalize_domain
    assert _normalize_domain("https://example.com/path") == "example.com"
    assert _normalize_domain("http://sub.example.com:8080/foo") == "sub.example.com:8080"


def test_get_parent_zone() -> None:
    from ethscan.dnssec import _get_parent_zone
    assert _get_parent_zone("example.com") == "com."
    assert _get_parent_zone("sub.example.com") == "example.com."
    assert _get_parent_zone("com") == "."
    assert _get_parent_zone(".") == "."


def test_format_dnssec_report_json() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": True,
        "dnskey": {"success": True, "keys": [], "error": None},
        "ds": {"success": True, "records": [], "error": None},
        "chain": [],
        "notes": [],
        "dnspython_available": False,
    }
    output = format_dnssec_report_json(data)
    assert "example.com" in output
    assert "validated" in output
    assert "true" in output.lower()


def test_format_dnssec_report_markdown_validated() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": True,
        "dnskey": {
            "success": True,
            "keys": [
                {
                    "name": "example.com.",
                    "flags": 257,
                    "protocol": 3,
                    "algorithm": 8,
                    "algorithm_name": "RSASHA256",
                    "key_tag": 12345,
                    "key_data": "abc123",
                }
            ],
            "error": None,
        },
        "ds": {
            "success": True,
            "records": [
                {
                    "name": "example.com.",
                    "key_tag": 12345,
                    "algorithm": 8,
                    "algorithm_name": "RSASHA256",
                    "digest_type": 2,
                    "digest_type_name": "SHA-256",
                    "digest": "abcdef123456",
                }
            ],
            "error": None,
        },
        "chain": [
            {"zone": "example.com", "dnskey": {"success": True, "keys": [{}], "error": None}},
            {"zone": "com", "ds": {"success": True, "records": [{}], "error": None}},
        ],
        "notes": ["Test note"],
        "dnspython_available": False,
    }
    output = format_dnssec_report_markdown(data)
    assert "# ethscan DNSSEC Validation Report" in output
    assert "example.com" in output
    assert "**Validated:** Yes" in output
    assert "## DNSKEY Records" in output
    assert "RSASHA256" in output
    assert "## DS Records (Parent Zone)" in output
    assert "SHA-256" in output
    assert "## Chain of Trust" in output
    assert "## Notes" in output
    assert "Test note" in output


def test_format_dnssec_report_markdown_unvalidated() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": True, "keys": [], "error": None},
        "ds": {"success": True, "records": [], "error": None},
        "chain": [],
        "notes": ["No DNSKEY records found (unsigned zone)", "No DS records found at parent zone"],
        "dnspython_available": False,
    }
    output = format_dnssec_report_markdown(data)
    assert "**Validated:** No" in output
    assert "*No DNSKEY records found (unsigned zone)*" in output
    assert "*No DS records found at parent zone*" in output


def test_format_dnssec_report_markdown_query_failed() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": False, "keys": [], "error": "no response"},
        "ds": {"success": False, "records": [], "error": "no response"},
        "chain": [],
        "notes": ["DNSKEY query failed: no response", "DS query failed: no response"],
        "dnspython_available": False,
    }
    output = format_dnssec_report_markdown(data)
    assert "*Query failed: no response*" in output


def test_run_dnssec_offline_basic(monkeypatch) -> None:
    def mock_query_dnskey_raw(nameserver, domain, timeout):
        return {"success": True, "keys": [{"name": "example.com.", "flags": 257, "protocol": 3, "algorithm": 8, "algorithm_name": "RSASHA256", "key_tag": 12345, "key_data": "abc123"}], "error": None}

    def mock_query_ds_raw(nameserver, domain, timeout):
        return {"success": True, "records": [{"name": "example.com.", "key_tag": 12345, "algorithm": 8, "algorithm_name": "RSASHA256", "digest_type": 2, "digest_type_name": "SHA-256", "digest": "abcdef123456"}], "error": None}

    def mock_resolve_nameservers(domain, timeout):
        return ["8.8.8.8"]

    monkeypatch.setattr("ethscan.dnssec._query_dnskey_raw", mock_query_dnskey_raw)
    monkeypatch.setattr("ethscan.dnssec._query_ds_raw", mock_query_ds_raw)
    monkeypatch.setattr("ethscan.dnssec._resolve_nameservers", mock_resolve_nameservers)
    monkeypatch.setattr("ethscan.dnssec.DNS_AVAILABLE", False)

    results = run_dnssec("example.com", timeout=1.0)
    assert results["target"] == "example.com"
    assert results["domain"] == "example.com"
    assert results["validated"] is True
    assert results["dnskey"]["success"] is True
    assert len(results["dnskey"]["keys"]) == 1
    assert results["ds"]["success"] is True
    assert len(results["ds"]["records"]) == 1
    assert results["dnspython_available"] is False
    assert len(results["notes"]) > 0


def test_run_dnssec_no_dnspython_no_server(monkeypatch) -> None:
    def mock_resolve_nameservers(domain, timeout):
        return []

    monkeypatch.setattr("ethscan.dnssec._resolve_nameservers", mock_resolve_nameservers)
    monkeypatch.setattr("ethscan.dnssec.DNS_AVAILABLE", False)

    results = run_dnssec("example.com", timeout=1.0)
    assert results["target"] == "example.com"
    assert results["domain"] == "example.com"
    assert results["validated"] is False
    assert not results["dnskey"]["success"]
    assert "no nameservers found" in results["dnskey"]["error"]
    assert results["dnspython_available"] is False


def test_run_dnssec_with_dnspython_mocked(monkeypatch) -> None:
    def mock_query_dnskey_dnspython(domain, server, timeout):
        return {"success": True, "keys": [{"name": "example.com.", "flags": 257, "protocol": 3, "algorithm": 8, "algorithm_name": "RSASHA256", "key_tag": 12345, "key_data": "abc123"}], "error": None}

    def mock_query_ds_dnspython(domain, server, timeout):
        return {"success": True, "records": [{"name": "example.com.", "key_tag": 12345, "algorithm": 8, "algorithm_name": "RSASHA256", "digest_type": 2, "digest_type_name": "SHA-256", "digest": "abcdef123456"}], "error": None}

    monkeypatch.setattr("ethscan.dnssec._query_dnskey_dnspython", mock_query_dnskey_dnspython)
    monkeypatch.setattr("ethscan.dnssec._query_ds_dnspython", mock_query_ds_dnspython)
    monkeypatch.setattr("ethscan.dnssec.DNS_AVAILABLE", True)

    results = run_dnssec("example.com", server="8.8.8.8", timeout=1.0)
    assert results["target"] == "example.com"
    assert results["domain"] == "example.com"
    assert results["validated"] is True
    assert results["dnskey"]["success"] is True
    assert len(results["dnskey"]["keys"]) == 1
    assert results["ds"]["success"] is True
    assert len(results["ds"]["records"]) == 1


def test_run_dnssec_url_target(monkeypatch) -> None:
    def mock_query_dnskey_raw(nameserver, domain, timeout):
        return {"success": True, "keys": [], "error": None}

    def mock_query_ds_raw(nameserver, domain, timeout):
        return {"success": True, "records": [], "error": None}

    def mock_resolve_nameservers(domain, timeout):
        return ["8.8.8.8"]

    monkeypatch.setattr("ethscan.dnssec._query_dnskey_raw", mock_query_dnskey_raw)
    monkeypatch.setattr("ethscan.dnssec._query_ds_raw", mock_query_ds_raw)
    monkeypatch.setattr("ethscan.dnssec._resolve_nameservers", mock_resolve_nameservers)
    monkeypatch.setattr("ethscan.dnssec.DNS_AVAILABLE", False)

    results = run_dnssec("https://example.com/path", timeout=1.0)
    assert results["target"] == "https://example.com/path"
    assert results["domain"] == "example.com"

def test_format_dnssec_report_csv() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": True,
        "dnskey": {"success": True, "keys": [{"key_tag": 12345}]},
        "ds": {"success": True, "records": [{"key_tag": 12345}]},
    }
    output = format_dnssec_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "domain", "validated", "dnskey_success", "dnskey_count", "ds_success", "ds_count"]
    assert reader[1] == ["example.com", "example.com", "true", "true", "1", "true", "1"]


def test_format_dnssec_report_csv_unsigned() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": False, "keys": [], "error": "no response"},
        "ds": {"success": False, "records": [], "error": "no response"},
    }
    output = format_dnssec_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1] == ["example.com", "example.com", "false", "false", "0", "false", "0"]
