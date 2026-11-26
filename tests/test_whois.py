"""Tests for the ethscan whois module."""

import socket

import pytest

from typing import Any, cast

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
    # Priority order is Registrar > Registrar Name > Sponsoring Registrar. With
    # no plain ``Registrar:`` line, ``Registrar Name:`` (priority 2) wins over
    # ``Sponsoring Registrar:`` (priority 3). The plain ``Registrar:`` pattern
    # must not match the ``Registrar:`` substring inside ``Sponsoring Registrar:``.
    raw = "Sponsoring Registrar: Registrar A\nRegistrar Name: Registrar B\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Registrar B"


def test_parse_whois_plain_registrar_beats_sponsoring() -> None:
    # A real ``Registrar:`` line must win over an earlier ``Sponsoring
    # Registrar:`` line; the plain pattern must not match the substring inside
    # ``Sponsoring Registrar:`` (regression for the substring-match defect).
    raw = "Sponsoring Registrar: Spons Registrar LLC\nRegistrar: Real Registrar Inc\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Real Registrar Inc"


def test_parse_whois_sponsoring_registrar_fallback() -> None:
    # With only a ``Sponsoring Registrar:`` line, it is still used as a fallback.
    raw = "Sponsoring Registrar: Spons Registrar LLC\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Spons Registrar LLC"


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


def test_run_whois_transport_failure_unnamed_type_reported(monkeypatch) -> None:
    """run_whois reports a transport failure of an unnamed type instead of raising.

    The socket creation itself is the seam here: when it fails with a type the
    module's narrow guard did not name, the command must still report the
    failure through its own error field and never crash.
    """

    def boom(*args, **kwargs):
        raise ValueError("socket creation failed")

    monkeypatch.setattr("ethscan.whois.socket.socket", boom)

    result = run_whois("example.com")

    assert result["error"] is not None
    assert "socket creation failed" in result["error"]
    assert result["raw"] == ""
    assert result["parsed"]["registrar"] is None


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
    monkeypatch.setattr(
        "ethscan.whois.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 43))
        ],
    )
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
    monkeypatch.setattr(
        "ethscan.whois.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 43))
        ],
    )
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
    monkeypatch.setattr(
        "ethscan.whois.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 43))
        ],
    )
    with pytest.raises(ConnectionRefusedError):
        query_whois("example.com")


def test_query_whois_ipv6_uses_af_inet6(monkeypatch) -> None:
    """An IPv6 WHOIS server resolves to an AF_INET6 TCP socket."""
    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def connect(self, sockaddr):
            captured["sockaddr"] = sockaddr

        def sendall(self, data):
            pass

        def recv(self, size):
            return b""

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.whois.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 43, 0, 0),
            )
        ],
    )
    monkeypatch.setattr("ethscan.whois.socket.socket", FakeSock)

    assert query_whois("example.com") == ""
    assert captured["family"] == socket.AF_INET6
    assert captured["socktype"] == socket.SOCK_STREAM
    assert captured["proto"] == socket.IPPROTO_TCP
    assert captured["sockaddr"] == ("::1", 43, 0, 0)


def test_query_whois_ipv4_uses_af_inet(monkeypatch) -> None:
    """An IPv4 WHOIS server resolves to an AF_INET TCP socket."""
    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family

        def settimeout(self, timeout):
            pass

        def connect(self, sockaddr):
            captured["sockaddr"] = sockaddr

        def sendall(self, data):
            pass

        def recv(self, size):
            return b""

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.whois.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 43),
            )
        ],
    )
    monkeypatch.setattr("ethscan.whois.socket.socket", FakeSock)

    assert query_whois("example.com") == ""
    assert captured["family"] == socket.AF_INET
    assert captured["sockaddr"] == ("127.0.0.1", 43)


def test_query_whois_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """A resolution failure propagates before any socket is created."""

    def boom(*args, **kwargs):
        raise OSError("name resolution failed")

    monkeypatch.setattr("ethscan.whois.socket.getaddrinfo", boom)

    with pytest.raises(OSError, match="name resolution failed"):
        query_whois("invalid-host")


def test_query_whois_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """An empty resolution result is reported instead of dereferencing it."""
    monkeypatch.setattr("ethscan.whois.socket.getaddrinfo", lambda *a, **kw: [])

    with pytest.raises(OSError, match="no address found"):
        query_whois("invalid-host")


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

    # A referral written as a URL is reduced to its bare hostname so the
    # recursive lookup can resolve it (getaddrinfo rejects a scheme).
    assert extract_referral_server("Refer: whois://whois.example.com") == "whois.example.com"
    assert extract_referral_server("Referral Server: whois://whois.example.com.") == "whois.example.com"
    assert extract_referral_server("WHOIS Server: WHOIS://WHOIS.EXAMPLE.COM") == "whois.example.com"
    assert extract_referral_server("Registrar WHOIS Server:\twhois://whois.first.com.") == "whois.first.com"
    # The whois.iana.org exclusion applies after the scheme is stripped.
    assert extract_referral_server("Refer: whois://whois.iana.org") is None


def test_extract_referral_server_empty_value_does_not_cross_lines() -> None:
    # A label with an empty same-line value must not capture the next line's
    # leading keyword as the referral hostname. The match is confined to the
    # label's own line, so the real referral on a following line is found.
    raw = "Registrar WHOIS Server: \nWHOIS Server: whois.other.com\n"
    assert extract_referral_server(raw) == "whois.other.com"
    raw2 = "Registrar WHOIS Server:\nRefer: whois.other.com\n"
    assert extract_referral_server(raw2) == "whois.other.com"
    # A bare hostname on the line after a label (no same-line value) is not a
    # referral the patterns recognise.
    assert extract_referral_server("Refer:\nwhois.other.com\n") is None


def test_parse_whois_empty_value_does_not_cross_lines() -> None:
    # A field label with an empty same-line value must not capture the next
    # line's leading label as its value. The value is confined to the label's
    # own line, so an empty value yields no value rather than the next line.
    raw = "Creation Date: \nRegistrar: Example Inc\n"
    parsed = parse_whois(raw)
    assert parsed["registrar"] == "Example Inc"
    assert not parsed["creation_date"]

    raw2 = "Registrar: \nCreation Date: 2020-01-01\n"
    parsed2 = parse_whois(raw2)
    assert not parsed2["registrar"]
    assert parsed2["creation_date"] == "2020-01-01"

    # Nameserver/status labels behave the same way: an empty same-line value
    # must not capture the following line's leading token.
    raw3 = "Name Server: \nStatus: ok\n"
    parsed3 = parse_whois(raw3)
    assert parsed3["nameservers"] == []
    assert parsed3["status_codes"] == ["ok"]

    raw4 = "Status: \nRegistrar: Example\n"
    parsed4 = parse_whois(raw4)
    assert parsed4["registrar"] == "Example"
    assert parsed4["status_codes"] == []


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
            mock_query.called = True  # type: ignore[attr-defined]
            return "Registrar: Test Registrar\nReferral Server: whois.registrar.net\n"
        return ""

    monkeypatch.setattr("ethscan.whois.query_whois", cast(Any, mock_query))

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
    assert "```" in output  # Empty raw response
    assert "" in output  # Empty raw response
    assert "```" in output  # Closing backticks


def test_format_whois_report_markdown_with_error() -> None:
    """Top-level error is reported in the markdown report (line 286)."""
    from ethscan.whois import format_whois_report_markdown

    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "raw": "some raw",
        "parsed": {
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "nameservers": [],
            "registrant_org": None,
            "status_codes": [],
            "raw": "some raw",
        },
        "error": "Connection timeout",
    }
    output = format_whois_report_markdown(data)
    assert "- **Error:** Connection timeout" in output


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
    data: dict[str, Any] = {"target": "example.com"}
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "target,example.com" in lines
    assert "registrar," in lines


def test_format_whois_report_csv_missing_fields() -> None:
    data: dict[str, Any] = {}
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


def test_format_whois_report_csv_with_error() -> None:
    """Top-level error row is emitted in the CSV report (line 364)."""
    data = {
        "target": "example.com",
        "server": "whois.iana.org",
        "port": 43,
        "parsed": {
            "registrar": "Example Registrar",
        },
        "error": "Connection timeout",
    }
    output = format_whois_report_csv(data)
    lines = output.splitlines()
    assert "error,Connection timeout" in lines


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


def test_format_whois_report_markdown_non_dict() -> None:
    """Cover line 279: a non-dict payload is reset to {} instead of raising."""
    hostiles: tuple[object, ...] = (None, [], "not a dict", 123, ("tuple",), {"nested": {"bad": "data"}})
    for hostile in hostiles:
        out = format_whois_report_markdown(hostile)  # type: ignore[arg-type]
        assert isinstance(out, str)


def test_format_whois_report_csv_non_dict() -> None:
    """Cover line 350: a non-dict payload is reset to {} instead of raising."""
    hostiles: tuple[object, ...] = (None, [], "not a dict", 123, ("tuple",), {"nested": {"bad": "data"}})
    for hostile in hostiles:
        out = format_whois_report_csv(hostile)  # type: ignore[arg-type]
        assert isinstance(out, str)

def test_format_whois_report_csv_sanitizes_formula_fields() -> None:
    import csv as _csv
    import io as _io

    from ethscan.whois import format_whois_report_csv

    data = {
        "target": "example.com",
        "server": "whois.example.com",
        "port": 43,
        "parsed": {
            "registrar": "=cmd|' /C calc'!A0",
            "creation_date": "2020-01-01",
            "expiration_date": "2030-01-01",
            "registrant_org": "@SUM(A1:A2)",
            "nameservers": ["ns1.example.com"],
            "status_codes": ["ok"],
        },
        "error": "-1+1",
    }
    output = format_whois_report_csv(data)
    reader = list(_csv.reader(_io.StringIO(output)))
    rows = {r[0]: r[1] for r in reader if len(r) >= 2}
    assert rows["registrar"] == "'=cmd|' /C calc'!A0"
    assert rows["registrant_org"] == "'@SUM(A1:A2)"
    assert rows["error"] == "'-1+1"
