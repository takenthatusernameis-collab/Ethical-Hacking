"""Tests for the ethscan headers module."""

import json
from unittest.mock import patch, MagicMock

import pytest

from ethscan.headers import (
    run_headers,
    format_headers_report_json,
    format_headers_report_markdown,
)
from ethscan.web import SECURITY_HEADERS


def test_run_headers_offline_target(monkeypatch):
    """Test run_headers with an offline target (no network)."""
    def mock_fetch_headers(url, timeout=5.0):
        return {}

    monkeypatch.setattr("ethscan.headers.fetch_headers", mock_fetch_headers)

    results = run_headers("https://nonexistent.invalid.domain.tld", timeout=1.0)

    assert results["target"] == "https://nonexistent.invalid.domain.tld"
    assert results["host"] == "nonexistent.invalid.domain.tld"
    assert results["port"] == 443
    assert results["secure"] is True
    assert "security_headers" in results
    assert results["security_headers"]["present_count"] == 0
    assert results["security_headers"]["missing_count"] == len(SECURITY_HEADERS)


def test_run_headers_with_headers(monkeypatch):
    """Test run_headers when some security headers are present."""
    mock_headers = {
        "content-security-policy": "default-src 'self'",
        "x-frame-options": "DENY",
        "strict-transport-security": "max-age=31536000",
        "server": "nginx",
    }

    def mock_fetch_headers(url, timeout=5.0):
        return mock_headers

    monkeypatch.setattr("ethscan.headers.fetch_headers", mock_fetch_headers)

    results = run_headers("https://example.com", timeout=1.0)

    assert results["security_headers"]["present_count"] == 3
    assert results["security_headers"]["missing_count"] == len(SECURITY_HEADERS) - 3
    assert "Content-Security-Policy" in results["security_headers"]["present"]
    assert "X-Frame-Options" in results["security_headers"]["present"]
    assert "Strict-Transport-Security" in results["security_headers"]["present"]


def test_run_headers_http_target(monkeypatch):
    """Test run_headers with HTTP target (not HTTPS)."""
    def mock_fetch_headers(url, timeout=5.0):
        return {"x-frame-options": "SAMEORIGIN"}

    monkeypatch.setattr("ethscan.headers.fetch_headers", mock_fetch_headers)

    results = run_headers("http://example.com", timeout=1.0)

    assert results["host"] == "example.com"
    assert results["port"] == 80
    assert results["secure"] is False
    assert results["security_headers"]["present_count"] == 1


def test_run_headers_bare_domain(monkeypatch):
    """Test run_headers with bare domain (no scheme)."""
    def mock_fetch_headers(url, timeout=5.0):
        return {}

    monkeypatch.setattr("ethscan.headers.fetch_headers", mock_fetch_headers)

    results = run_headers("example.com", timeout=1.0)

    assert results["host"] == "example.com"
    assert results["port"] == 443
    assert results["secure"] is True


def test_format_headers_report_json():
    """Test JSON formatter for headers report."""
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {"content-security-policy": "default-src 'self'"},
        "security_headers": {
            "present": ["Content-Security-Policy"],
            "missing": [h for h in SECURITY_HEADERS if h != "Content-Security-Policy"],
            "total": len(SECURITY_HEADERS),
            "present_count": 1,
            "missing_count": len(SECURITY_HEADERS) - 1,
        },
    }

    output = format_headers_report_json(data)
    parsed = json.loads(output)

    assert parsed["target"] == "https://example.com"
    assert parsed["security_headers"]["present_count"] == 1
    assert "Content-Security-Policy" in parsed["security_headers"]["present"]


def test_format_headers_report_markdown():
    """Test Markdown formatter for headers report."""
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {"content-security-policy": "default-src 'self'"},
        "security_headers": {
            "present": ["Content-Security-Policy", "X-Frame-Options"],
            "missing": [h for h in SECURITY_HEADERS if h not in ["Content-Security-Policy", "X-Frame-Options"]],
            "total": len(SECURITY_HEADERS),
            "present_count": 2,
            "missing_count": len(SECURITY_HEADERS) - 2,
        },
    }

    output = format_headers_report_markdown(data)

    assert "ethscan Security Headers Report" in output
    assert "example.com" in output
    assert "Present: 2" in output
    assert "Content-Security-Policy" in output
    assert "X-Frame-Options" in output


def test_format_headers_report_markdown_no_present():
    """Test Markdown formatter when no headers are present."""
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {},
        "security_headers": {
            "present": [],
            "missing": list(SECURITY_HEADERS.keys()),
            "total": len(SECURITY_HEADERS),
            "present_count": 0,
            "missing_count": len(SECURITY_HEADERS),
        },
    }

    output = format_headers_report_markdown(data)

    assert "Present: 0" in output
    assert "Missing headers:" in output


def test_format_headers_report_json_empty():
    """Test JSON formatter with empty data."""
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {},
        "security_headers": {
            "present": [],
            "missing": list(SECURITY_HEADERS.keys()),
            "total": len(SECURITY_HEADERS),
            "present_count": 0,
            "missing_count": len(SECURITY_HEADERS),
        },
    }

    output = format_headers_report_json(data)
    parsed = json.loads(output)

    assert parsed["security_headers"]["present_count"] == 0
    assert parsed["security_headers"]["missing_count"] == len(SECURITY_HEADERS)


def test_format_headers_report_markdown_http():
    """Test Markdown formatter for HTTP target."""
    data = {
        "target": "http://example.com",
        "host": "example.com",
        "port": 80,
        "secure": False,
        "headers": {"x-frame-options": "SAMEORIGIN"},
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": [h for h in SECURITY_HEADERS if h != "X-Frame-Options"],
            "total": len(SECURITY_HEADERS),
            "present_count": 1,
            "missing_count": len(SECURITY_HEADERS) - 1,
        },
    }

    output = format_headers_report_markdown(data)

    assert "**HTTPS:** No" in output
    assert "X-Frame-Options" in output