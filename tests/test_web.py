"""Tests for the ethscan web security module."""

import json
from unittest.mock import patch, MagicMock

from ethscan.web import (
    _parse_url,
    check_information_disclosure,
    check_security_headers,
    check_ssl_configuration,
    fetch_headers,
    format_web_report_csv,
    format_web_report_json,
    format_web_report_markdown,
    run_web_checks,
)


# ---------------------------------------------------------------------------
# _parse_url
# ---------------------------------------------------------------------------


def test_parse_url_https() -> None:
    host, port, secure = _parse_url("https://example.com")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_parse_url_http_with_port() -> None:
    host, port, secure = _parse_url("http://example.com:8080")
    assert host == "example.com"
    assert port == 8080
    assert secure is False


def test_parse_url_bare_host() -> None:
    host, port, secure = _parse_url("example.com")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_parse_url_http_default_port() -> None:
    host, port, secure = _parse_url("http://example.com")
    assert host == "example.com"
    assert port == 80
    assert secure is False


def test_parse_url_https_with_path() -> None:
    host, port, secure = _parse_url("https://example.com/path/to/page.html")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_parse_url_ipv4_address() -> None:
    host, port, secure = _parse_url("http://192.168.1.1:8080")
    assert host == "192.168.1.1"
    assert port == 8080
    assert secure is False


def test_parse_url_strips_whitespace() -> None:
    host, port, secure = _parse_url("  example.com  ")
    assert host == "example.com"
    assert port == 443
    assert secure is True


def test_parse_url_localhost() -> None:
    host, port, secure = _parse_url("localhost")
    assert host == "localhost"
    assert port == 443
    assert secure is True


# ---------------------------------------------------------------------------
# check_security_headers
# ---------------------------------------------------------------------------


def test_check_security_headers_all_missing() -> None:
    result = check_security_headers({})
    assert result["present_count"] == 0
    assert result["missing_count"] == result["total"]
    assert len(result["present"]) == 0
    assert len(result["missing"]) == result["total"]


def test_check_security_headers_all_present() -> None:
    from ethscan.web import SECURITY_HEADERS

    headers = {h.lower(): "value" for h in SECURITY_HEADERS}
    result = check_security_headers(headers)
    assert result["present_count"] == result["total"]
    assert result["missing_count"] == 0


def test_check_security_headers_partial_present() -> None:
    headers = {
        "content-security-policy": "default-src 'self'",
        "x-frame-options": "DENY",
    }
    result = check_security_headers(headers)
    assert result["present_count"] == 2
    assert result["missing_count"] == result["total"] - 2
    assert "Content-Security-Policy" in result["present"]
    assert "X-Frame-Options" in result["present"]
    assert "X-Content-Type-Options" in result["missing"]


def test_check_security_headers_case_insensitive() -> None:
    headers = {"content-security-policy": "default-src 'self'"}
    result = check_security_headers(headers)
    assert "Content-Security-Policy" in result["present"]
    assert result["present_count"] == 1
    assert result["missing_count"] == result["total"] - 1


# ---------------------------------------------------------------------------
# check_information_disclosure
# ---------------------------------------------------------------------------


def test_check_information_disclosure_detects_server() -> None:
    headers = {"server": "Apache/2.4.1", "content-type": "text/html"}
    findings = check_information_disclosure(headers)
    assert len(findings) == 1
    assert findings[0]["header"] == "Server"
    assert findings[0]["value"] == "Apache/2.4.1"


def test_check_information_disclosure_no_findings() -> None:
    headers = {"content-type": "text/html"}
    findings = check_information_disclosure(headers)
    assert findings == []


def test_check_information_disclosure_multiple_headers() -> None:
    headers = {
        "server": "Apache/2.4.1",
        "x-powered-by": "PHP/7.4.0",
        "content-type": "text/html",
    }
    findings = check_information_disclosure(headers)
    assert len(findings) == 2
    assert findings[0]["header"] == "Server"
    assert findings[1]["header"] == "X-Powered-By"
    assert findings[0]["value"] == "Apache/2.4.1"
    assert findings[1]["value"] == "PHP/7.4.0"
    assert findings[0]["description"] == "Reveals server software version."
    assert findings[1]["description"] == "Reveals technology stack."


def test_check_information_disclosure_case_insensitive() -> None:
    headers = {"server": "Apache/2.4.1"}
    findings = check_information_disclosure(headers)
    assert len(findings) == 1
    assert findings[0]["header"] == "Server"
    assert findings[0]["description"] == "Reveals server software version."


# ---------------------------------------------------------------------------
# check_ssl_configuration
# ---------------------------------------------------------------------------


def test_check_ssl_configuration_invalid_host() -> None:
    result = check_ssl_configuration("nonexistent.invalid.domain.tld", timeout=2.0)
    assert result["valid"] is False
    assert result["error"] is not None


@patch("ethscan.web.socket.create_connection")
@patch("ethscan.web.ssl.create_default_context")
def test_check_ssl_configuration_success(mock_ssl_context, mock_socket) -> None:
    mock_sock = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock
    mock_ctx = MagicMock()
    mock_ssl_context.return_value = mock_ctx
    mock_ssock = MagicMock()
    mock_ctx.wrap_socket.return_value.__enter__.return_value = mock_ssock
    mock_ssock.get_verified_chain.return_value = []
    mock_ssock.getpeercert.return_value = {
        "subject": ((("commonName", "example.com"), ("organizationName", "Test")),),
        "issuer": ((("commonName", "Let's Encrypt"), ("organizationUnitName", "Cert")),),
        "notAfter": "Jan  1 00:00:00 2027 GMT",
    }

    result = check_ssl_configuration("example.com", timeout=5.0)
    assert result["valid"] is True
    assert result["subject"] == "example.com"
    assert result["issuer"] == "Let's Encrypt"
    assert result["not_after"] == "Jan  1 00:00:00 2027 GMT"
    assert result["days_remaining"] > 0
    assert result["chain_length"] == 0
    assert result["error"] is None


@patch("ethscan.web.socket.create_connection")
def test_check_ssl_configuration_connection_error(mock_socket) -> None:
    mock_socket.side_effect = OSError("Connection refused")
    result = check_ssl_configuration("example.com", port=443, timeout=5.0)
    assert result["valid"] is False
    assert result["error"] is not None
    assert result["subject"] is None
    assert result["issuer"] is None


@patch("ethscan.web.socket.create_connection")
@patch("ethscan.web.ssl.create_default_context")
def test_check_ssl_configuration_ssl_error(mock_ssl_context, mock_socket) -> None:
    import ssl

    mock_sock = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock
    mock_ctx = MagicMock()
    mock_ssl_context.return_value = mock_ctx
    mock_ctx.wrap_socket.side_effect = ssl.SSLError("SSL handshake failed")

    result = check_ssl_configuration("example.com", timeout=5.0)
    assert result["valid"] is False
    assert result["error"] is not None


@patch("ethscan.web.socket.create_connection")
@patch("ethscan.web.ssl.create_default_context")
def test_check_ssl_configuration_expired_cert(mock_ssl_context, mock_socket) -> None:
    mock_sock = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock
    mock_ctx = MagicMock()
    mock_ssl_context.return_value = mock_ctx
    mock_ssock = MagicMock()
    mock_ctx.wrap_socket.return_value.__enter__.return_value = mock_ssock
    mock_ssock.get_verified_chain.return_value = []
    mock_ssock.getpeercert.return_value = {
        "subject": ((("commonName", "example.com"), ("organizationName", "Test")),),
        "issuer": ((("commonName", "Let's Encrypt"), ("organizationUnitName", "Cert")),),
        "notAfter": "Jan  1 00:00:00 2020 GMT",
    }

    result = check_ssl_configuration("example.com", timeout=5.0)
    assert result["valid"] is False
    assert result["days_remaining"] < 0
    assert result["not_after"] == "Jan  1 00:00:00 2020 GMT"
    assert result["error"] is None


# ---------------------------------------------------------------------------
# fetch_headers
# ---------------------------------------------------------------------------


def test_fetch_headers_offline() -> None:
    headers = fetch_headers("http://nonexistent.invalid.domain.tld", timeout=1.0)
    assert headers == {}


@patch("ethscan.web.urllib.request.urlopen")
def test_fetch_headers_success(mock_urlopen) -> None:
    mock_response = MagicMock()
    mock_response.headers = {
        "Content-Type": "text/html",
        "X-Frame-Options": "DENY",
        "Server": "Apache/2.4.1",
    }
    mock_urlopen.return_value.__enter__.return_value = mock_response

    headers = fetch_headers("https://example.com")
    assert "content-type" in headers
    assert headers["content-type"] == "text/html"
    assert headers["x-frame-options"] == "DENY"
    assert headers["server"] == "Apache/2.4.1"


@patch("ethscan.web.urllib.request.urlopen")
def test_fetch_headers_http_error(mock_urlopen) -> None:
    import urllib.error

    mock_headers = {"Content-Type": "text/html"}
    error = urllib.error.HTTPError(
        url="https://example.com",
        code=404,
        msg="Not Found",
        hdrs=mock_headers,
        fp=None,
    )
    mock_urlopen.side_effect = error

    headers = fetch_headers("https://example.com")
    assert "content-type" in headers
    assert headers["content-type"] == "text/html"


@patch("ethscan.web.urllib.request.urlopen")
def test_fetch_headers_connection_error(mock_urlopen) -> None:
    import urllib.error

    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
    headers = fetch_headers("https://example.com", timeout=5.0)
    assert headers == {}


# ---------------------------------------------------------------------------
# run_web_checks
# ---------------------------------------------------------------------------


def test_run_web_checks_offline_target() -> None:
    results = run_web_checks(
        "http://nonexistent.invalid.domain.tld", ["headers", "info_disclosure"], timeout=2.0
    )
    assert results["target"].startswith("http://")
    assert results["secure"] is False
    assert "headers" in results
    assert "security_headers" in results
    assert "information_disclosure" in results


@patch("ethscan.web.fetch_headers")
def test_run_web_checks_https(mock_fetch_headers) -> None:
    mock_fetch_headers.return_value = {
        "content-security-policy": "default-src 'self'",
        "x-frame-options": "DENY",
    }
    results = run_web_checks("https://example.com", ["headers", "info_disclosure"], timeout=1.0)
    assert results["secure"] is True
    assert results["port"] == 443
    assert results["host"] == "example.com"
    assert results["target"] == "https://example.com"
    assert results["security_headers"]["present_count"] == 2
    assert len(results["information_disclosure"]) == 0


@patch("ethscan.web.check_ssl_configuration")
def test_run_web_checks_ssl_check(mock_check_ssl) -> None:
    mock_check_ssl.return_value = {
        "valid": True,
        "error": None,
        "subject": "example.com",
        "issuer": "Let's Encrypt",
        "not_after": "Jan  1 00:00:00 2027 GMT",
        "days_remaining": 100,
        "chain_length": 0,
    }
    results = run_web_checks("https://example.com", ["ssl"], timeout=1.0)
    assert "ssl" in results
    assert results["ssl"]["valid"] is True
    assert results["ssl"]["subject"] == "example.com"
    assert results["ssl"]["issuer"] == "Let's Encrypt"


@patch("ethscan.web.fetch_headers")
def test_run_web_checks_url_target(mock_fetch_headers) -> None:
    mock_fetch_headers.return_value = {"content-type": "text/html"}
    results = run_web_checks("http://example.com:8080", ["headers"], timeout=1.0)
    assert results["target"] == "http://example.com:8080"
    assert results["host"] == "example.com"
    assert results["port"] == 8080
    assert results["secure"] is False
    mock_fetch_headers.assert_called_once()


def test_run_web_checks_empty_checks() -> None:
    results = run_web_checks("https://example.com", [], timeout=1.0)
    assert "headers" not in results
    assert "security_headers" not in results
    assert "information_disclosure" not in results
    assert "ssl" not in results
    assert results["target"] == "https://example.com"
    assert results["secure"] is True


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def test_format_web_report_json() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": ["Content-Security-Policy"],
            "missing": ["X-Frame-Options"],
            "total": 7,
            "present_count": 1,
            "missing_count": 6,
        },
    }
    output = format_web_report_json(data)
    assert "example.com" in output
    assert "security_headers" in output


def test_format_web_report_json_full() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {"content-type": "text/html"},
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": ["Content-Security-Policy"],
            "total": 7,
            "present_count": 1,
            "missing_count": 6,
        },
        "information_disclosure": [],
        "ssl": {"valid": True, "error": None},
    }
    output = format_web_report_json(data)
    parsed = json.loads(output)
    assert parsed["target"] == "https://example.com"
    assert parsed["host"] == "example.com"
    assert parsed["secure"] is True
    assert parsed["security_headers"]["total"] == 7
    assert parsed["information_disclosure"] == []
    assert parsed["ssl"]["valid"] is True


def test_format_web_report_json_empty() -> None:
    data = {}
    output = format_web_report_json(data)
    parsed = json.loads(output)
    assert parsed == {}


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


def test_format_web_report_markdown() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": ["Content-Security-Policy"],
            "missing": ["X-Frame-Options"],
            "total": 7,
            "present_count": 1,
            "missing_count": 6,
        },
        "information_disclosure": [],
        "ssl": {
            "valid": True,
            "subject": "example.com",
            "issuer": "Let's Encrypt",
            "not_after": "Jan  1 00:00:00 2027 GMT",
            "days_remaining": 100,
        },
    }
    output = format_web_report_markdown(data)
    assert "# ethscan Web Security Report" in output
    assert "example.com" in output
    assert "## Security Headers" in output
    assert "## Information Disclosure" in output
    assert "## SSL/TLS" in output


def test_format_web_report_markdown_no_security_headers() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "information_disclosure": [],
        "ssl": {"valid": False, "error": "Connection failed"},
    }
    output = format_web_report_markdown(data)
    assert "## Security Headers" not in output
    assert "## Information Disclosure" in output
    assert "## SSL/TLS" in output


def test_format_web_report_markdown_no_information_disclosure() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": [],
            "missing": [],
            "total": 7,
            "present_count": 0,
            "missing_count": 7,
        },
        "ssl": {"valid": False, "error": "Connection failed"},
    }
    output = format_web_report_markdown(data)
    assert "## Security Headers" in output
    assert "## Information Disclosure" not in output
    assert "## SSL/TLS" in output


def test_format_web_report_markdown_no_ssl() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": [],
            "missing": [],
            "total": 7,
            "present_count": 0,
            "missing_count": 7,
        },
        "information_disclosure": [],
    }
    output = format_web_report_markdown(data)
    assert "## Security Headers" in output
    assert "## SSL/TLS" not in output


def test_format_web_report_markdown_with_pipe_in_header() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "information_disclosure": [
            {"header": "Server", "value": "Apache|extra", "description": "Server|info"},
        ],
    }
    output = format_web_report_markdown(data)
    assert "## Information Disclosure" in output
    assert "Apache|extra" in output
    assert "| Server |" in output


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_web_report_csv_basic() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": ["Content-Security-Policy"],
        },
        "information_disclosure": [
            {"header": "Server", "value": "Apache", "description": "Server header exposed"},
        ],
        "ssl": {
            "valid": True,
            "error": None,
            "subject": "CN=example.com",
            "issuer": "Let's Encrypt",
            "not_after": "2024-12-31",
            "days_remaining": 100,
            "chain_length": 2,
        },
    }
    output = format_web_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target,https://example.com" in lines
    assert "https,true" in lines
    assert "security_header,status" in lines
    assert "X-Frame-Options,present" in lines
    assert "Content-Security-Policy,missing" in lines
    assert "disclosure_header,value,description" in lines
    assert "Server,Apache,Server header exposed" in lines
    assert "ssl_field,value" in lines
    assert "subject,CN=example.com" in lines


def test_format_web_report_csv_empty() -> None:
    data = {"target": "https://example.com", "host": "example.com", "port": 443, "secure": False}
    output = format_web_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target,https://example.com" in lines
    assert "https,false" in lines


def test_format_web_report_csv_missing_fields() -> None:
    data = {"target": "https://example.com", "host": "example.com", "port": 443, "secure": True}
    output = format_web_report_csv(data)
    assert "security_header,status" not in output
    assert "disclosure_header,value,description" not in output


def test_format_web_report_csv_escaping() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "information_disclosure": [
            {"header": "X-Powered-By", "value": "ASP.NET, Version=4.0", "description": "Framework, version"},
        ],
    }
    output = format_web_report_csv(data)
    assert '"ASP.NET, Version=4.0"' in output
    assert '"Framework, version"' in output


def test_format_web_report_csv_ssl_fields() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "ssl": {
            "valid": True,
            "subject": "CN=example.com",
            "issuer": "Let's Encrypt",
            "not_after": "2024-12-31",
            "days_remaining": 150,
        },
    }
    output = format_web_report_csv(data)
    assert "ssl_field,value" in output
    assert "subject,CN=example.com" in output
    assert "days_remaining,150" in output
    assert "valid,true" in output
    assert "issuer,Let's Encrypt" in output


def test_format_web_report_csv_no_security_headers() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "information_disclosure": [],
    }
    output = format_web_report_csv(data)
    assert "security_header,status" not in output
    assert "target,https://example.com" in output
    assert "https,true" in output


def test_format_web_report_csv_ssl_error() -> None:
    data = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "ssl": {
            "valid": False,
            "error": "Connection failed",
        },
    }
    output = format_web_report_csv(data)
    assert "ssl_field,value" in output
    assert "error,Connection failed" in output
    assert "valid,false" in output
