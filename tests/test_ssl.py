"""Tests for the ethscan ssl module."""

import pytest

from ethscan.ssl import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    _normalize_host,
    _parse_cert,
    _rdn_to_str,
    format_ssl_report_json,
    format_ssl_report_markdown,
    inspect_certificate,
    run_ssl,
)


def test_defaults() -> None:
    assert DEFAULT_PORT == 443
    assert DEFAULT_TIMEOUT == 5.0


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"
    assert _normalize_host("EXAMPLE.COM") == "example.com"


def test_normalize_host_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"
    assert _normalize_host("http://sub.example.com:8080/foo") == "sub.example.com"


def test_rdn_to_str() -> None:
    assert _rdn_to_str({"commonName": "example.com", "organization": "Test"}) == "commonName=example.com, organization=Test"


def test_parse_cert_basic() -> None:
    cert = {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("commonName", "Let's Encrypt"),),),
        "subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com")),
        "notBefore": "Jan  1 00:00:00 2020 GMT",
        "notAfter": "Jan  1 00:00:00 2030 GMT",
        "signatureAlgorithm": ("sha256WithRSAEncryption",),
        "publicKeyInfo": {"bits": 2048, "size": 256},
    }
    parsed = _parse_cert(cert)
    assert parsed["subject"] == "example.com"
    assert parsed["issuer"] == "Let's Encrypt"
    assert parsed["sans"] == ["example.com", "www.example.com"]
    assert parsed["not_before"] == "Jan  1 00:00:00 2020 GMT"
    assert parsed["not_after"] == "Jan  1 00:00:00 2030 GMT"
    assert parsed["signature_algorithm"] == "sha256WithRSAEncryption"
    assert parsed["key_size"] == 2048


def test_parse_cert_empty() -> None:
    parsed = _parse_cert({})
    assert parsed["subject"] is None
    assert parsed["issuer"] is None
    assert parsed["sans"] == []
    assert parsed["not_before"] is None
    assert parsed["not_after"] is None
    assert parsed["signature_algorithm"] is None
    assert parsed["key_size"] is None


def test_format_ssl_report_json() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": None,
        "cert": {
            "subject": "example.com",
            "issuer": "Let's Encrypt",
            "sans": ["example.com"],
            "not_before": "Jan  1 00:00:00 2020 GMT",
            "not_after": "Jan  1 00:00:00 2030 GMT",
            "signature_algorithm": "sha256WithRSAEncryption",
            "key_size": 2048,
        },
        "valid": True,
        "days_remaining": 3650,
        "chain_length": 2,
    }
    output = format_ssl_report_json(data)
    assert "example.com" in output
    assert "Let's Encrypt" in output
    assert "sha256WithRSAEncryption" in output
    assert "2048" in output


def test_format_ssl_report_json_error() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": "connection refused",
        "cert": None,
        "valid": False,
        "days_remaining": None,
        "chain_length": 0,
    }
    output = format_ssl_report_json(data)
    assert "connection refused" in output


def test_format_ssl_report_markdown() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": None,
        "cert": {
            "subject": "example.com",
            "issuer": "Let's Encrypt",
            "sans": ["example.com", "www.example.com"],
            "not_before": "Jan  1 00:00:00 2020 GMT",
            "not_after": "Jan  1 00:00:00 2030 GMT",
            "signature_algorithm": "sha256WithRSAEncryption",
            "key_size": 2048,
        },
        "valid": True,
        "days_remaining": 3650,
        "chain_length": 2,
    }
    output = format_ssl_report_markdown(data)
    assert "# ethscan SSL/TLS Certificate Report" in output
    assert "example.com" in output
    assert "Let's Encrypt" in output
    assert "sha256WithRSAEncryption" in output
    assert "2048 bits" in output
    assert "www.example.com" in output


def test_format_ssl_report_markdown_error() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": "connection refused",
        "cert": None,
        "valid": False,
        "days_remaining": None,
        "chain_length": 0,
    }
    output = format_ssl_report_markdown(data)
    assert "connection refused" in output
    assert "## Certificate" not in output


def test_format_ssl_report_markdown_verification_error_with_cert() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
        "cert": {
            "subject": "example.com",
            "issuer": "Test CA",
            "sans": ["example.com"],
            "not_before": "Jan  1 00:00:00 2020 GMT",
            "not_after": "Jan  1 00:00:00 2030 GMT",
            "signature_algorithm": "sha256WithRSAEncryption",
            "key_size": 2048,
        },
        "valid": False,
        "days_remaining": None,
        "chain_length": 0,
    }
    output = format_ssl_report_markdown(data)
    assert "certificate verify failed" in output
    assert "## Certificate" in output
    assert "example.com" in output
    assert "Test CA" in output
    assert "sha256WithRSAEncryption" in output


def test_inspect_certificate_offline(monkeypatch) -> None:
    """inspect_certificate returns an error dict on connection failure."""

    def mock_create_connection(*args, **kwargs):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr("ethscan.ssl.socket.create_connection", mock_create_connection)

    result = inspect_certificate("nonexistent.invalid.host", port=443, timeout=0.1)
    assert result["error"] is not None
    assert "connection refused" in result["error"]
    assert result["cert"] is None
    assert result["valid"] is False
    assert result["chain_length"] == 0


def test_run_ssl_offline(monkeypatch) -> None:
    def mock_inspect_certificate(host, port=443, timeout=5.0):
        return {
            "target": host,
            "port": port,
            "timeout": timeout,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        }

    monkeypatch.setattr("ethscan.ssl.inspect_certificate", mock_inspect_certificate)

    result = run_ssl("https://example.com/path", port=8443, timeout=1.0)
    assert result["host"] == "example.com"
    assert result["target"] == "https://example.com/path"
    assert result["port"] == 8443
    assert result["error"] == "connection refused"