"""Tests for the ethscan whois module."""

import socket

import pytest

from ethscan.whois import (
    DEFAULT_TIMEOUT,
    DEFAULT_WHOIS_SERVER,
    _normalize_target,
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


def test_normalize_target() -> None:

    # Basic domain
    assert _normalize_target("example.com") == "example.com"
    # With www
    assert _normalize_target("www.example.com") == "www.example.com"
    # URL with http
    assert _normalize_target("http://example.com") == "example.com"
    # URL with https
    assert _normalize_target("https://example.com") == "example.com"
    # URL with path
    assert _normalize_target("https://example.com/path") == "example.com"
    # URL with port
    assert _normalize_target("http://example.com:8080") == "example.com"
    # URL with user/pass
    assert _normalize_target("http://user:pass@example.com") == "example.com"
    # IPv4 address
    assert _normalize_target("192.168.1.1") == "192.168.1.1"
    # IPv4 with port
    assert _normalize_target("http://192.168.1.1:8080") == "192.168.1.1"
    # Leading/trailing whitespace
    assert _normalize_target("  example.com  ") == "example.com"
    # Mixed case
    assert _normalize_target("EXAMPLE.COM") == "example.com"
    assert _normalize_target("Http://Example.Com") == "example.com"


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


def test_run_whois_transport_failure_reported(monkeypatch) -> None:
    """run_whois reports a transport failure of an unnamed type instead of raising."""

    class BoomSocket:
        def __init__(self, *a, **k):
            pass

        def settimeout(self, *a, **k):
            pass

        def connect(self, *a, **k):
            raise RuntimeError("hostile transport")

        def close(self, *a, **k):
            pass

    monkeypatch.setattr("ethscan.whois.socket.socket", BoomSocket)

    result = run_whois("example.com")

    assert result["error"] is not None
    assert "hostile transport" in result["error"]


def test_query_whois_invalid_target() -> None:
    with pytest.raises((socket.gaierror, socket.timeout, ConnectionRefusedError, OSError)):
        query_whois("invalid.tld", server="127.0.0.1", port=43, timeout=0.1)


def test_query_whois_success(monkeypatch) -> None:
    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            pass

        def sendall(self, data):
            pass

        def recv(self, size):
            # Return some data on first call, then empty to break the loop
            if not hasattr(self, 'data_returned'):
                self.data_returned = True
                return b"Registrar: Test Registrar\n"
            return b""

        def close(self):
            pass

    monkeypatch.setattr("socket.socket", MockSocket)
    result = query_whois("example.com")
    assert "Registrar: Test Registrar" in result


def test_query_whois_timeout(monkeypatch) -> None:
    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            pass

        def sendall(self, data):
            pass

        def recv(self, size):
            # Simulate timeout by raising socket.timeout
            raise socket.timeout()

        def close(self):
            pass

    monkeypatch.setattr("socket.socket", MockSocket)
    with pytest.raises(socket.timeout):
        query_whois("example.com", timeout=0.1)


def test_query_whois_connection_refused(monkeypatch) -> None:
    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            # Simulate connection refused
            raise ConnectionRefusedError()

        def sendall(self, data):
            pass

        def recv(self, size):
            return b""

        def close(self):
            pass

    monkeypatch.setattr("socket.socket", MockSocket)
    with pytest.raises(ConnectionRefusedError):
        query_whois("example.com")


def test_extract_referral_server() -> None:

    # Test each pattern
    assert extract_referral_server("Registrar WHOIS Server: whois.example.com") == "whois.example.com"
    assert extract_referral_server("WHOIS Server: whois.registrar.net") == "whois.registrar.net"
    assert extract_referral_server("Referral Server: whois.test.org") == "whois.test.org"
    assert extract_referral_server("Refer: whois.example.com") == "whois.example.com"
    assert extract_referral_server("Registrar URL: whois://whois.example.com") == "whois.example.com"

    # Test case insensitivity
    assert extract_referral_server("registrar whois server: whois.example.com") == "whois.example.com"
    assert extract_referral_server("whois server: whois.example.com") == "whois.example.com"

    # Test trailing dot removal
    assert extract_referral_server("Registrar WHOIS Server: whois.example.com.") == "whois.example.com"
    assert extract_referral_server("Refer: whois.example.com.") == "whois.example.com"

    # Test lowercasing
    assert extract_referral_server("Registrar WHOIS Server: WHOIS.EXAMPLE.COM") == "whois.example.com"

    # Test that whois.iana.org is excluded (returns None)
    assert extract_referral_server("Registrar WHOIS Server: whois.iana.org") is None
    assert extract_referral_server("WHOIS Server: whois.iana.org") is None

    # Test first match wins
    raw = "Registrar WHOIS Server: whois.first.com\nWHOIS Server: whois.second.com"
    assert extract_referral_server(raw) == "whois.first.com"

    # Test no match
    assert extract_referral_server("Some other text without referral") is None
    assert extract_referral_server("") is None
    assert extract_referral_server("   ") is None

    # Test with extra whitespace
    assert extract_referral_server("Registrar WHOIS Server:   whois.example.com   ") == "whois.example.com"


def test_run_whois_non_recursive(monkeypatch) -> None:
    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        return "Registrar: Test Registrar\nCreation Date: 2020-01-01\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=False)
    assert results["target"] == "example.com"
    assert results["server"] == "whois.iana.org"
    assert results["port"] == 43
    assert results["recursive"] is False
    assert results["recursive_hops"] == []
    assert results["parsed"]["registrar"] == "Test Registrar"


def test_run_whois_recursive_no_referral(monkeypatch) -> None:
    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        return "Registrar: Test Registrar\nCreation Date: 2020-01-01\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True)
    assert results["target"] == "example.com"
    assert results["server"] == "whois.iana.org"
    assert results["recursive"] is True
    assert results["recursive_hops"] == []
    assert results["parsed"]["registrar"] == "Test Registrar"


def test_run_whois_recursive_with_referral(monkeypatch) -> None:
    call_count = 0

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First response with referral to another server
            return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"
        else:
            # Second response from the referral server
            return "Registrar: Referral Registrar\nCreation Date: 2021-01-01\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True, max_depth=2)
    assert results["target"] == "example.com"
    assert results["server"] == "whois.iana.org"
    assert results["recursive"] is True
    assert results["max_depth"] == 2
    assert len(results["recursive_hops"]) == 1
    hop = results["recursive_hops"][0]
    assert hop["depth"] == 1
    assert hop["server"] == "whois.registrar.net"
    assert hop["port"] == 43
    assert hop["parsed"]["registrar"] == "Referral Registrar"
    assert hop["parsed"]["creation_date"] == "2021-01-01"
    assert hop["referral_server"] is None  # No further referral in second response
    assert results["parsed"]["registrar"] == "Test Registrar"


def test_run_whois_recursive_max_depth(monkeypatch) -> None:
    call_count = 0

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        nonlocal call_count
        call_count += 1
        # Always return a referral to create a chain
        return f"Registrar: Test Registrar {call_count}\nReferral Server: whois.server{call_count}.net\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True, max_depth=2)
    assert results["target"] == "example.com"
    assert results["recursive"] is True
    assert results["max_depth"] == 2
    # Should only have 2 hops (depth 1 and 2) due to max_depth limit
    assert len(results["recursive_hops"]) == 2
    assert results["recursive_hops"][0]["depth"] == 1
    assert results["recursive_hops"][0]["server"] == "whois.server1.net"
    assert results["recursive_hops"][1]["depth"] == 2
    assert results["recursive_hops"][1]["server"] == "whois.server2.net"


def test_run_whois_recursive_loop_protection(monkeypatch) -> None:
    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        # Always return the same response with a referral to self
        return "Registrar: Test Registrar\nReferral Server: whois.iana.org\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True, max_depth=5)
    assert results["target"] == "example.com"
    assert results["recursive"] is True
    # Should stop early due to loop protection (referral same as current server)
    assert len(results["recursive_hops"]) == 0


def test_run_whois_recursive_connection_failure(monkeypatch) -> None:
    call_count = 0

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First response with referral
            return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"
        else:
            # Second attempt fails
            raise ConnectionRefusedError()

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True)
    assert results["target"] == "example.com"
    assert results["recursive"] is True
    assert len(results["recursive_hops"]) == 1
    hop = results["recursive_hops"][0]
    assert hop["depth"] == 1
    assert hop["server"] == "whois.registrar.net"
    assert hop["error"] == "Connection failed"
    assert hop["parsed"]["registrar"] is None  # parse_whois("") returns None for registrar


def test_run_whois_recursive_empty_response(monkeypatch) -> None:
    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        # First response with referral, second response empty
        if not hasattr(mock_query, 'called'):
            mock_query.called = True
            return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"
        return ""

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True)
    assert results["target"] == "example.com"
    assert results["recursive"] is True
    assert len(results["recursive_hops"]) == 1
    hop = results["recursive_hops"][0]
    assert hop["depth"] == 1
    assert hop["server"] == "whois.registrar.net"
    assert hop["raw"] == ""
    assert hop["parsed"]["registrar"] is None
    assert hop["referral_server"] is None  # extract_referral_server("") returns None


def test_run_whois_default_parameters(monkeypatch) -> None:
    # Test that default parameters are used when not specified
    # We'll mock query_whois to capture what parameters are passed to it
    captured_params = {}

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        captured_params.update({
            'server': server,
            'port': port,
            'timeout': timeout
        })
        return "Registrar: Test Registrar\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    # Import inside test to avoid issues
    from ethscan.whois import run_whois
    run_whois("example.com")

    assert captured_params['server'] == "whois.iana.org"
    assert captured_params['port'] == 43
    assert captured_params['timeout'] == 5.0


def test_parse_whois_edge_cases() -> None:
    from ethscan.whois import parse_whois

    # Empty string
    result = parse_whois("")
    assert result["registrar"] is None
    assert result["creation_date"] is None
    assert result["expiration_date"] is None
    assert result["nameservers"] == []
    assert result["registrant_org"] is None
    assert result["status_codes"] == []
    assert result["raw"] == ""

    # No matching patterns
    result = parse_whois("Some random text without any matching patterns")
    assert result["registrar"] is None
    assert result["creation_date"] is None
    assert result["expiration_date"] is None
    assert result["nameservers"] == []
    assert result["registrant_org"] is None
    assert result["status_codes"] == []
    assert result["raw"] == "Some random text without any matching patterns"

    # Whitespace stripping
    result = parse_whois("Registrar:   Example Registrar, Inc.   \n")
    assert result["registrar"] == "Example Registrar, Inc."

    # Empty match (should become empty string after strip)
    result = parse_whois("Registrar:   \n")
    assert result["registrar"] == ""

    # Multiple patterns - should use first match
    result = parse_whois("Registrar: First Registrar\nRegistrar Name: Second Registrar\n")
    assert result["registrar"] == "First Registrar"

    # Multiple nameservers
    result = parse_whois("Name Server: NS1.EXAMPLE.COM\nName Server: ns2.example.com.\nName Server: NS1.EXAMPLE.COM\n")
    assert result["nameservers"] == ["NS1.EXAMPLE.COM", "ns2.example.com"]
    # Should be sorted, unique, and trailing dots stripped (but case preserved)

    # Multiple status codes
    result = parse_whois("Status: clientTransferProhibited\nStatus: clientUpdateProhibited\nStatus: clientTransferProhibited\n")
    assert result["status_codes"] == ["clientTransferProhibited", "clientUpdateProhibited"]
    # Should be sorted and unique

    # Mixed case sensitivity (already tested but let's be thorough)
    result = parse_whois("registrar: test registrar\nCREATION DATE: 2020-01-01\n")
    assert result["registrar"] == "test registrar"
    assert result["creation_date"] == "2020-01-01"

    # Special characters in values
    result = parse_whois('Registrar: "Test, Registrar" Inc.\n')
    assert result["registrar"] == '"Test, Registrar" Inc.'

    # Newlines in values (should capture up to newline)
    result = parse_whois("Registrar: Test Registrar\nExtra line\n")
    assert result["registrar"] == "Test Registrar"

    # Tab characters
    result = parse_whois("Registrar:\tTest Registrar\t\n")
    assert result["registrar"] == "Test Registrar"


def test_format_whois_report_json_special_values() -> None:
    from ethscan.whois import format_whois_report_json
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": 'Test "quote" & ampersand',
        "parsed": {
            "registrar": 'Test "Registrar"',
            "creation_date": None,
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": None,
            "status_codes": ["clientTransferProhibited"],
            "raw": 'Test "quote" & ampersand',
        },
    }
    output = format_whois_report_json(data)
    # Should contain the values (JSON handles escaping)
    assert 'example.com' in output
    assert 'whois.iana.org' in output
    assert 'Test \\"quote\\" & ampersand' in output  # Escaped quotes in JSON
    assert '"Test \\"Registrar\\""' in output  # Escaped quotes
    assert '2025-01-01' in output
    assert 'ns1.example.com' in output
    assert 'clientTransferProhibited' in output


def test_format_whois_report_markdown_recursive_with_error() -> None:
    from ethscan.whois import format_whois_report_markdown
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "first response",
        "parsed": {
            "registrar": "Test Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": "Test Org",
            "status_codes": ["clientTransferProhibited"],
            "raw": "first response",
        },
        "recursive": True,
        "recursive_hops": [
            {
                "depth": 1,
                "server": "whois.registrar.net",
                "port": 43,
                "raw": "second response with error",
                "parsed": {
                    "registrar": None,
                    "creation_date": None,
                    "expiration_date": None,
                    "nameservers": [],
                    "registrant_org": None,
                    "status_codes": [],
                    "raw": "second response with error",
                },
                "error": "Connection timeout",
                "referral_server": None,
            }
        ],
    }
    output = format_whois_report_markdown(data)
    assert "# ethscan WHOIS Lookup Report" in output
    assert "example.com" in output
    assert "whois.iana.org:43" in output
    assert "Test Registrar" in output
    assert "2020-01-01" in output
    assert "2025-01-01" in output
    assert "Test Org" in output
    assert "ns1.example.com" in output
    assert "clientTransferProhibited" in output
    assert "## Recursive WHOIS Queries" in output
    assert "- **Depth 1:** whois.registrar.net:43 - Connection timeout" in output
    assert "```" in output  # Raw response section
    assert "first response" in output


def test_format_whois_report_markdown_recursive_success() -> None:
    from ethscan.whois import format_whois_report_markdown
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "first response",
        "parsed": {
            "registrar": "Test Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": "Test Org",
            "status_codes": ["clientTransferProhibited"],
            "raw": "first response",
        },
        "recursive": True,
        "recursive_hops": [
            {
                "depth": 1,
                "server": "whois.registrar.net",
                "port": 43,
                "raw": "second response",
                "parsed": {
                    "registrar": "Referral Registrar",
                    "creation_date": "2021-01-01",
                    "expiration_date": "2026-01-01",
                    "nameservers": ["ns1.registrar.net"],
                    "registrant_org": "Referral Org",
                    "status_codes": ["ok"],
                    "raw": "second response",
                },
                "referral_server": "whois.another.net",
            }
        ],
    }
    output = format_whois_report_markdown(data)
    assert "# ethscan WHOIS Lookup Report" in output
    assert "example.com" in output
    assert "Test Registrar" in output
    assert "Referral Registrar" in output
    assert "2020-01-01" in output
    assert "2021-01-01" in output
    assert "ns1.example.com" in output
    assert "## Recursive WHOIS Queries" in output
    assert "- **Depth 1:** whois.registrar.net:43" in output
    assert "  - Registrar: Referral Registrar" in output
    assert "  - Creation Date: 2021-01-01" in output
    assert "  - Referral Server: whois.another.net" in output


def test_format_whois_report_markdown_recursive_no_hops() -> None:
    from ethscan.whois import format_whois_report_markdown
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "response",
        "parsed": {
            "registrar": "Test Registrar",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.example.com"],
            "registrant_org": "Test Org",
            "status_codes": ["clientTransferProhibited"],
            "raw": "response",
        },
        "recursive": True,
        "recursive_hops": [],
    }
    output = format_whois_report_markdown(data)
    assert "# ethscan WHOIS Lookup Report" in output
    assert "example.com" in output
    assert "Test Registrar" in output
    assert "## Recursive WHOIS Queries" in output
    assert "*No referral servers found; no additional hops performed.*" in output


def test_format_whois_report_markdown_empty_raw() -> None:
    from ethscan.whois import format_whois_report_markdown
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "",
        "parsed": {
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "nameservers": [],
            "registrant_org": None,
            "status_codes": [],
            "raw": "",
        },
    }
    output = format_whois_report_markdown(data)
    assert "# ethscan WHOIS Lookup Report" in output
    assert "example.com" in output
    assert "N/A" in output  # All fields should show N/A
    assert "## Nameservers" not in output  # Section should not appear
    assert "## Status Codes" not in output  # Section should not appear
    assert "## Raw Response" in output
    assert "```" in output
    assert "" in output  # Empty raw response
    assert "```" in output  # Closing backticks


# ---------------------------------------------------------------------------


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


def test_run_whois_recursive_referral_equals_current_server(monkeypatch) -> None:
    """referral == current_server must break the recursion (line 209)."""

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", server="whois.registrar.net", recursive=True, max_depth=2)
    assert results["server"] == "whois.registrar.net"
    assert results["recursive"] is True
    assert results["recursive_hops"] == []


def test_run_whois_recursive_response_repeat_loop_protection(monkeypatch) -> None:
    """A repeated hop response must break the recursion (line 242)."""

    def mock_query(target, server="whois.iana.org", port=43, timeout=5.0):
        return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"

    monkeypatch.setattr("ethscan.whois.query_whois", mock_query)

    results = run_whois("example.com", recursive=True, max_depth=5)
    assert results["recursive"] is True
    assert results["max_depth"] == 5
    # One hop is made, then the repeated response stops further recursion.
    assert len(results["recursive_hops"]) == 1
    hop = results["recursive_hops"][0]
    assert hop["depth"] == 1
    assert hop["server"] == "whois.registrar.net"
    assert hop["parsed"]["registrar"] == "Test Registrar"