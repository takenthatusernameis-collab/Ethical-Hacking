"""Tests for the ethscan dnsbrute module."""

import csv
import io
import socket
import struct
import threading

import pytest

from ethscan.dnsbrute import (
    DEFAULT_SUBDOMAINS,
    DNS_AVAILABLE,
    RCODE_NAMES,
    _axfr_result,
    _extract_ns_records,
    _is_subdomain_of,
    _normalize_domain,
    _parse_dns_name,
    attempt_axfr,
    build_axfr_query,
    discover_nameservers,
    format_dnsbrute_report_csv,
    format_dnsbrute_report_json,
    format_dnsbrute_report_markdown,
    parse_dns_response,
    query_axfr_raw,
    run_dnsbrute,
)


def _encode_dns_name(name: str) -> bytes:
    labels = name.split(".")
    return b"".join(bytes([len(label)]) + label.encode() for label in labels) + b"\x00"


def _build_dns_response(
    query_id: int, rcode: int, answers: list[tuple[str, int]]
) -> bytes:
    header = struct.pack(
        ">HHHHHH", query_id, 0x8000 | rcode, 0, len(answers), 0, 0
    )
    body = b""
    for name, rtype in answers:
        body += _encode_dns_name(name)
        body += struct.pack(">HHIH", rtype, 1, 300, 4)
        body += b"\x01\x02\x03\x04"
    return header + body


class _FakeDNSServer:
    """Single-shot TCP DNS server that replies with a canned response."""

    def __init__(self, response: bytes):
        self.response = response
        self.received = b""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        try:
            conn, _ = self.sock.accept()
            self.received = conn.recv(4096)
            conn.sendall(self.response)
            conn.close()
        except OSError:
            pass
        finally:
            self.sock.close()


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ---------------------------------------------------------------------------
# Domain normalization
# ---------------------------------------------------------------------------


def test_normalize_domain_bare() -> None:
    assert _normalize_domain("example.com") == "example.com"


def test_normalize_domain_uppercase() -> None:
    assert _normalize_domain("Example.COM") == "example.com"


def test_normalize_domain_https_url() -> None:
    assert _normalize_domain("https://example.com/path") == "example.com"


def test_normalize_domain_strips_whitespace() -> None:
    assert _normalize_domain("  example.com  ") == "example.com"


def test_normalize_domain_with_port() -> None:
    assert _normalize_domain("http://example.com:8080") == "example.com:8080"


# ---------------------------------------------------------------------------
# AXFR query building
# ---------------------------------------------------------------------------


def test_build_axfr_query_length_prefix() -> None:
    query = build_axfr_query("example.com")
    prefix = struct.unpack(">H", query[:2])[0]
    assert prefix == len(query) - 2


def test_build_axfr_query_header() -> None:
    query = build_axfr_query("example.com", query_id=0x1234)
    message = query[2:]
    query_id, flags, qdcount, _, _, _ = struct.unpack(">HHHHHH", message[:12])
    assert query_id == 0x1234
    assert flags == 0
    assert qdcount == 1


def test_build_axfr_query_question() -> None:
    query = build_axfr_query("example.com")
    message = query[2:]
    assert _encode_dns_name("example.com") in message
    qtype, qclass = struct.unpack(">HH", message[-4:])
    assert qtype == 252
    assert qclass == 1


def test_build_axfr_query_strips_trailing_dot() -> None:
    query = build_axfr_query("example.com.")
    message = query[2:]
    assert _encode_dns_name("example.com") in message


def test_build_axfr_query_custom_id() -> None:
    query = build_axfr_query("example.com", query_id=0xABCD)
    assert struct.unpack(">H", query[2:4])[0] == 0xABCD


# ---------------------------------------------------------------------------
# DNS name parsing
# ---------------------------------------------------------------------------


def test_parse_dns_name_plain() -> None:
    data = _encode_dns_name("www.example.com")
    name, offset = _parse_dns_name(data, 0)
    assert name == "www.example.com"
    assert offset == len(data)


def test_parse_dns_name_compression_pointer() -> None:
    # Name at offset 0 is a pointer to offset 12 where "example.com" is stored.
    name_data = _encode_dns_name("example.com")
    data = b"\xc0\x0c" + b"\x00" * 10 + name_data
    name, offset = _parse_dns_name(data, 0)
    assert name == "example.com"
    assert offset == 2


def test_parse_dns_name_pointer_loop_protection() -> None:
    data = b"\xc0\x00" + b"\x00" * 10
    name, offset = _parse_dns_name(data, 0)
    assert name == ""
    assert offset == 2


# ---------------------------------------------------------------------------
# DNS response parsing
# ---------------------------------------------------------------------------


def test_parse_dns_response_too_short() -> None:
    result = parse_dns_response(b"\x00" * 5)
    assert result["valid"] is False


def test_parse_dns_response_success() -> None:
    data = _build_dns_response(0x1234, 0, [("www.example.com", 1), ("mail.example.com", 1)])
    result = parse_dns_response(data)
    assert result["valid"] is True
    assert result["query_id"] == 0x1234
    assert result["response_code"] == 0
    assert result["response_code_name"] == "NOERROR"
    assert result["answer_count"] == 2
    assert [a["name"] for a in result["answers"]] == [
        "www.example.com",
        "mail.example.com",
    ]
    assert [a["type"] for a in result["answers"]] == [1, 1]


def test_parse_dns_response_refused() -> None:
    data = _build_dns_response(1, 5, [])
    result = parse_dns_response(data)
    assert result["valid"] is True
    assert result["response_code"] == 5
    assert result["response_code_name"] == "REFUSED"
    assert result["answer_count"] == 0


def test_parse_dns_response_unknown_rcode_name() -> None:
    data = _build_dns_response(1, 15, [])
    result = parse_dns_response(data)
    assert result["response_code_name"] == "UNKNOWN"


def test_rcode_names_cover_common_codes() -> None:
    for code in (0, 1, 2, 3, 4, 5):
        assert code in RCODE_NAMES


# ---------------------------------------------------------------------------
# Raw AXFR (stdlib TCP) against a local fake server
# ---------------------------------------------------------------------------


def test_query_axfr_raw_success() -> None:
    response = _build_dns_response(
        0x2B00, 0, [("www.example.com", 1), ("mail.example.com", 1)]
    )
    server = _FakeDNSServer(response)

    result = query_axfr_raw("127.0.0.1", "example.com", timeout=2.0, port=server.port)

    assert result["nameserver"] == "127.0.0.1"
    assert result["success"] is True
    assert result["records_count"] == 2
    assert result["records"] == ["www.example.com", "mail.example.com"]
    assert result["error"] is None


def test_query_axfr_raw_sends_axfr_question() -> None:
    response = _build_dns_response(0x2B00, 0, [("www.example.com", 1)])
    server = _FakeDNSServer(response)

    query_axfr_raw("127.0.0.1", "example.com", timeout=2.0, port=server.port)

    received = server.received
    prefix = struct.unpack(">H", received[:2])[0]
    assert prefix == len(received) - 2
    message = received[2:]
    qtype, qclass = struct.unpack(">HH", message[-4:])
    assert qtype == 252
    assert qclass == 1
    assert _encode_dns_name("example.com") in message


def test_query_axfr_raw_refused() -> None:
    response = _build_dns_response(0x2B00, 5, [])
    server = _FakeDNSServer(response)

    result = query_axfr_raw("127.0.0.1", "example.com", timeout=2.0, port=server.port)

    assert result["success"] is False
    assert result["records_count"] == 0
    assert "REFUSED" in result["error"]


def test_query_axfr_raw_empty_response() -> None:
    response = _build_dns_response(0x2B00, 0, [])
    server = _FakeDNSServer(response)

    result = query_axfr_raw("127.0.0.1", "example.com", timeout=2.0, port=server.port)

    assert result["success"] is False
    assert "empty response" in result["error"]


def test_query_axfr_raw_connection_refused() -> None:
    port = _free_port()
    result = query_axfr_raw("127.0.0.1", "example.com", timeout=1.0, port=port)
    assert result["success"] is False
    assert result["records_count"] == 0
    assert result["error"]


def test_query_axfr_raw_invalid_response() -> None:
    server = _FakeDNSServer(b"garbage")
    result = query_axfr_raw("127.0.0.1", "example.com", timeout=2.0, port=server.port)
    assert result["success"] is False
    assert result["error"] == "invalid response"


# ---------------------------------------------------------------------------
# attempt_axfr dispatch
# ---------------------------------------------------------------------------


def test_attempt_axfr_uses_raw_path_without_dnspython(monkeypatch) -> None:
    response = _build_dns_response(0x2B00, 0, [("www.example.com", 1)])
    server = _FakeDNSServer(response)

    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)
    result = attempt_axfr("127.0.0.1", "example.com", timeout=2.0, port=server.port)

    assert result["success"] is True
    assert result["records"] == ["www.example.com"]


def test_attempt_axfr_uses_dnspython_when_available(monkeypatch) -> None:
    calls = {}

    def fake_dnspython(nameserver, zone, timeout=2.0):
        calls["nameserver"] = nameserver
        calls["zone"] = zone
        calls["timeout"] = timeout
        return _axfr_result(nameserver, True, ["example.com 300 IN SOA ns1"], None)

    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", True)
    monkeypatch.setattr("ethscan.dnsbrute._axfr_dnspython", fake_dnspython)

    result = attempt_axfr("ns1.example.com", "example.com", timeout=3.0)

    assert calls == {"nameserver": "ns1.example.com", "zone": "example.com", "timeout": 3.0}
    assert result["success"] is True
    assert result["records"] == ["example.com 300 IN SOA ns1"]


def test_attempt_axfr_dnspython_not_installed(monkeypatch) -> None:
    import builtins

    from ethscan import dnsbrute

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("dns."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = dnsbrute._axfr_dnspython("ns1.example.com", "example.com")

    assert result["success"] is False
    assert result["error"] == "dnspython not installed"


# ---------------------------------------------------------------------------
# Nameserver discovery
# ---------------------------------------------------------------------------


def test_discover_nameservers_unavailable_without_dnspython(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)
    assert discover_nameservers("example.com") == []


def test_discover_nameservers_lookup(monkeypatch) -> None:
    def fake_resolve(domain, record_type, timeout=2.0):
        assert domain == "example.com"
        assert record_type == "NS"
        return ["ns1.example.com.", "ns2.example.com.", "ns1.example.com."]

    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", True)
    monkeypatch.setattr("ethscan.dnsbrute.resolve_with_dnspython", fake_resolve)

    nameservers = discover_nameservers("example.com")

    assert nameservers == ["ns1.example.com", "ns2.example.com"]


def test_discover_nameservers_empty_lookup(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", True)
    monkeypatch.setattr(
        "ethscan.dnsbrute.resolve_with_dnspython", lambda *a, **k: []
    )
    assert discover_nameservers("example.com") == []


# ---------------------------------------------------------------------------
# Helper functions for recursive AXFR
# ---------------------------------------------------------------------------


def test_extract_ns_records() -> None:
    records = [
        "example.com 300 IN NS ns1.example.com",
        "example.com 300 IN NS ns2.example.com",
        "www.example.com 300 IN A 1.2.3.4",
        "example.com 300 IN MX 10 mail.example.com",
    ]
    ns_records = _extract_ns_records(records)
    assert ns_records == ["ns1.example.com", "ns2.example.com"]


def test_extract_ns_records_empty() -> None:
    records = [
        "www.example.com 300 IN A 1.2.3.4",
        "mail.example.com 300 IN A 5.6.7.8",
    ]
    assert _extract_ns_records(records) == []


def test_extract_ns_records_with_trailing_dot() -> None:
    records = [
        "example.com 300 IN NS ns1.example.com.",
        "example.com 300 IN NS ns2.example.com",
    ]
    ns_records = _extract_ns_records(records)
    assert ns_records == ["ns1.example.com", "ns2.example.com"]


def test_is_subdomain_of_exact_match() -> None:
    assert _is_subdomain_of("example.com", "example.com") is True


def test_is_subdomain_of_subdomain() -> None:
    assert _is_subdomain_of("www.example.com", "example.com") is True
    assert _is_subdomain_of("mail.sub.example.com", "example.com") is True


def test_is_subdomain_of_not_subdomain() -> None:
    assert _is_subdomain_of("example.org", "example.com") is False
    assert _is_subdomain_of("other.com", "example.com") is False


def test_is_subdomain_of_with_trailing_dots() -> None:
    assert _is_subdomain_of("www.example.com.", "example.com.") is True
    assert _is_subdomain_of("example.com", "example.com.") is True


# ---------------------------------------------------------------------------
# run_dnsbrute
# ---------------------------------------------------------------------------


def test_run_dnsbrute_offline_target() -> None:
    results = run_dnsbrute(
        "nonexistent.invalid.domain.tld",
        subdomains=["www", "mail"],
        timeout=1.0,
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["zone"] == "nonexistent.invalid.domain.tld"
    assert results["nameserver_source"] in ("lookup", "none")
    assert results["subdomains_tested"] == 2
    assert results["resolved_count"] == 0
    assert len(results["all_results"]) == 2
    for entry in results["all_results"]:
        assert entry["a"] == []
        assert entry["aaaa"] == []
    assert results["resolved"] == []
    assert "axfr" in results
    assert results["axfr_success"] is False


def test_run_dnsbrute_uses_default_wordlist(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute("nonexistent.invalid.domain.tld", timeout=1.0)
    assert results["subdomains_tested"] == len(DEFAULT_SUBDOMAINS)


def test_run_dnsbrute_url_target(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute("https://example.com/path", subdomains=["www"], timeout=1.0)
    assert results["domain"] == "example.com"
    assert results["all_results"][0]["hostname"] == "www.example.com"


def test_run_dnsbrute_ns_option(monkeypatch) -> None:
    axfr_calls = []

    def fake_axfr(nameserver, zone, timeout=2.0):
        axfr_calls.append((nameserver, zone))
        return _axfr_result(nameserver, False, [], "refused")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns2.example.com", "ns1.example.com", "ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
    )

    assert results["nameserver_source"] == "option"
    assert results["nameservers"] == ["ns1.example.com", "ns2.example.com"]
    assert axfr_calls == [
        ("ns1.example.com", "example.com"),
        ("ns2.example.com", "example.com"),
    ]
    assert len(results["axfr"]) == 2
    assert all(entry["error"] == "refused" for entry in results["axfr"])


def test_run_dnsbrute_ns_lookup_source(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", True)
    monkeypatch.setattr(
        "ethscan.dnsbrute.resolve_with_dnspython",
        lambda domain, rtype, timeout=2.0: ["ns1.example.com."],
    )
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )

    results = run_dnsbrute("example.com", subdomains=["www"], timeout=1.0)

    assert results["nameserver_source"] == "lookup"
    assert results["nameservers"] == ["ns1.example.com"]


def test_run_dnsbrute_no_nameservers_available(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)
    results = run_dnsbrute("example.com", subdomains=["www"], timeout=1.0)
    assert results["nameserver_source"] == "none"
    assert results["nameservers"] == []
    assert results["axfr"] == []
    assert results["axfr_success"] is False
    assert results["axfr_total_records"] == 0


def test_run_dnsbrute_resolves_a_and_aaaa(monkeypatch) -> None:
    def fake_a(hostname, timeout=2.0):
        return ["1.2.3.4"] if hostname.startswith("www.") else []

    def fake_aaaa(hostname, timeout=2.0):
        return ["::1"] if hostname.startswith("www.") else []

    monkeypatch.setattr("ethscan.dnsbrute.resolve_a_records", fake_a)
    monkeypatch.setattr("ethscan.dnsbrute.resolve_aaaa_records", fake_aaaa)
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www", "mail"],
        timeout=1.0,
    )

    assert results["resolved_count"] == 1
    resolved = results["resolved"][0]
    assert resolved["subdomain"] == "www"
    assert resolved["hostname"] == "www.example.com"
    assert resolved["a"] == ["1.2.3.4"]
    assert resolved["aaaa"] == ["::1"]


def test_run_dnsbrute_axfr_success_aggregation(monkeypatch) -> None:
    def fake_axfr(nameserver, zone, timeout=2.0):
        if nameserver == "ns1.example.com":
            return _axfr_result(nameserver, True, ["www.example.com", "mail.example.com"], None)
        return _axfr_result(nameserver, False, [], "refused")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com", "ns2.example.com"],
        subdomains=["www"],
        timeout=1.0,
    )

    assert results["axfr_success"] is True
    assert results["axfr_total_records"] == 2


def test_run_dnsbrute_axfr_failure_aggregation(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute(
        "example.com", nameservers=["ns1.example.com"], subdomains=["www"], timeout=1.0
    )
    assert results["axfr_success"] is False
    assert results["axfr_total_records"] == 0


def test_run_dnsbrute_reports_dnspython_flag() -> None:
    results = run_dnsbrute(
        "nonexistent.invalid.domain.tld", subdomains=["www"], timeout=1.0
    )
    assert results["dnspython_available"] == DNS_AVAILABLE


def test_run_dnsbrute_empty_nameservers_option(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute(
        "example.com", nameservers=["", "  "], subdomains=["www"], timeout=1.0
    )
    assert results["nameservers"] == []
    assert results["nameserver_source"] == "option"
    assert results["axfr"] == []


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _sample_data() -> dict:
    return {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": False,
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            }
        ],
        "axfr_success": False,
        "axfr_total_records": 0,
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "a": [],
                "aaaa": [],
            },
        ],
    }


def test_format_dnsbrute_report_json() -> None:
    output = format_dnsbrute_report_json(_sample_data())
    assert "example.com" in output
    assert "ns1.example.com" in output
    assert "transfer refused (REFUSED)" in output
    assert "1.2.3.4" in output
    assert "axfr_success" in output


def test_format_dnsbrute_report_json_axfr_success() -> None:
    data = _sample_data()
    data["axfr"][0]["success"] = True
    data["axfr"][0]["records"] = ["www.example.com"]
    data["axfr"][0]["records_count"] = 1
    data["axfr"][0]["error"] = None
    data["axfr_success"] = True
    data["axfr_total_records"] = 1
    output = format_dnsbrute_report_json(data)
    assert '"success": true' in output
    assert "www.example.com" in output


def test_format_dnsbrute_report_markdown() -> None:
    output = format_dnsbrute_report_markdown(_sample_data())
    assert "# ethscan DNS Brute Force Report" in output
    assert "**Target:** example.com" in output
    assert "**Zone:** example.com" in output
    assert "ns1.example.com" in output
    assert "source: option" in output
    assert "**AXFR Successful:** No" in output
    assert "**Subdomains Tested:** 2" in output
    assert "**Resolved:** 1" in output
    assert "## AXFR Attempts" in output
    assert "### ns1.example.com" in output
    assert "transfer refused (REFUSED)" in output
    assert "## Resolved Subdomains" in output
    assert "## All Results" in output
    assert "1.2.3.4" in output
    assert "N/A" in output


def test_format_dnsbrute_report_markdown_axfr_records() -> None:
    data = _sample_data()
    data["axfr"][0]["success"] = True
    data["axfr"][0]["records"] = ["www.example.com", "mail.example.com"]
    data["axfr"][0]["records_count"] = 2
    data["axfr"][0]["error"] = None
    data["axfr_success"] = True
    data["axfr_total_records"] = 2
    output = format_dnsbrute_report_markdown(data)
    assert "**AXFR Successful:** Yes" in output
    assert "**AXFR Records:** 2" in output
    assert "```" in output
    assert "mail.example.com" in output


def test_format_dnsbrute_report_markdown_no_nameservers() -> None:
    data = _sample_data()
    data["nameservers"] = []
    data["nameserver_source"] = "none"
    data["axfr"] = []
    output = format_dnsbrute_report_markdown(data)
    assert "**Nameservers:** None (source: none)" in output
    assert "No nameservers available for AXFR attempts." in output


def test_format_dnsbrute_report_markdown_dnspython_available() -> None:
    data = _sample_data()
    data["dnspython_available"] = True
    output = format_dnsbrute_report_markdown(data)
    assert "**dnspython Available:** Yes" in output


def test_format_dnsbrute_report_markdown_escapes_pipes() -> None:
    data = _sample_data()
    data["all_results"][0]["subdomain"] = "www|evil"
    data["resolved"][0]["subdomain"] = "www|evil"
    output = format_dnsbrute_report_markdown(data)
    assert "www\\|evil" in output


def test_format_dnsbrute_report_markdown_multiple_ips() -> None:
    data = _sample_data()
    data["resolved"][0]["a"] = ["1.2.3.4", "5.6.7.8"]
    data["resolved"][0]["aaaa"] = ["::1"]
    data["all_results"][0]["a"] = ["1.2.3.4", "5.6.7.8"]
    data["all_results"][0]["aaaa"] = ["::1"]
    output = format_dnsbrute_report_markdown(data)
    assert "1.2.3.4, 5.6.7.8" in output
    assert "::1" in output


def test_axfr_result_helper() -> None:
    result = _axfr_result("ns1.example.com", True, ["www.example.com"], None)
    assert result == {
        "nameserver": "ns1.example.com",
        "success": True,
        "records_count": 1,
        "records": ["www.example.com"],
        "error": None,
    }


def test_run_dnsbrute_with_resolver(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute(
        "nonexistent.invalid.domain.tld",
        nameservers=["ns1.example.com"],
        subdomains=["www", "mail"],
        timeout=1.0,
        resolver="8.8.8.8",
    )
    assert results["target"] == "nonexistent.invalid.domain.tld"
    assert results["domain"] == "nonexistent.invalid.domain.tld"
    assert results["zone"] == "nonexistent.invalid.domain.tld"
    assert results["nameserver_source"] == "option"
    assert results["subdomains_tested"] == 2
    assert results["resolved_count"] == 0
    assert results["resolver"] == "8.8.8.8"
    assert results["dnspython_available"] is False


def test_run_dnsbrute_resolver_used_for_resolution(monkeypatch) -> None:
    try:
        import dns.resolver
    except ImportError:
        pytest.skip("dnspython not installed")


    def mock_resolve(self, hostname, rdtype):
        if self.nameservers == ["8.8.8.8"]:
            if rdtype == "A" and hostname.startswith("www."):
                from dns.rdata import from_text
                from dns.rrset import RRset
                rrset = RRset(
                    dns.name.from_text(hostname),
                    dns.rdataclass.IN,
                    dns.rdatatype.A,
                )
                rrset.ttl = 300
                rrset.add(from_text("IN", "A", "1.2.3.4"))
                return rrset
            if rdtype == "AAAA" and hostname.startswith("www."):
                from dns.rdata import from_text
                from dns.rrset import RRset
                rrset = RRset(
                    dns.name.from_text(hostname),
                    dns.rdataclass.IN,
                    dns.rdatatype.AAAA,
                )
                rrset.ttl = 300
                rrset.add(from_text("IN", "AAAA", "::1"))
                return rrset
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", mock_resolve)
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www", "mail"],
        timeout=1.0,
        resolver="8.8.8.8",
    )

    assert results["resolved_count"] == 1
    assert results["resolver"] == "8.8.8.8"
    assert results["dnspython_available"] is True


def test_format_dnsbrute_report_json_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            }
        ],
        "axfr_success": False,
        "axfr_total_records": 0,
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "a": [],
                "aaaa": [],
            },
        ],
        "resolver": "8.8.8.8",
    }
    output = format_dnsbrute_report_json(data)
    assert "example.com" in output
    assert "8.8.8.8" in output


def test_format_dnsbrute_report_markdown_with_resolver() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            }
        ],
        "axfr_success": False,
        "axfr_total_records": 0,
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolved": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            }
        ],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "a": ["1.2.3.4"],
                "aaaa": [],
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "a": [],
                "aaaa": [],
            },
        ],
        "resolver": "8.8.8.8",
    }
    output = format_dnsbrute_report_markdown(data)
    assert "# ethscan DNS Brute Force Report" in output
    assert "**Resolver:** 8.8.8.8 (dnspython: Yes)" in output


# ---------------------------------------------------------------------------
# Recursive AXFR tests
# ---------------------------------------------------------------------------


def test_run_dnsbrute_recursive_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(
        "ethscan.dnsbrute.attempt_axfr",
        lambda ns, zone, timeout=2.0: _axfr_result(ns, False, [], "refused"),
    )
    results = run_dnsbrute(
        "example.com", nameservers=["ns1.example.com"], subdomains=["www"], timeout=1.0
    )
    assert results.get("recursive") is False
    assert results.get("max_depth") == 0
    assert "recursive_axfr" in results
    assert results["recursive_axfr"] == []


def test_run_dnsbrute_recursive_enabled(monkeypatch) -> None:
    """Test recursive AXFR when enabled with successful zone transfer."""
    axfr_calls = []

    def fake_axfr(nameserver, zone, timeout=2.0):
        axfr_calls.append((nameserver, zone))
        if zone == "example.com" and nameserver == "ns1.example.com":
            # Return NS records for subdomain nameservers
            return _axfr_result(
                nameserver,
                True,
                [
                    "example.com 300 IN NS ns1.example.com",
                    "example.com 300 IN NS ns2.example.com",
                    "sub.example.com 300 IN NS ns1.sub.example.com",
                ],
                None,
            )
        if zone == "example.com" and nameserver == "ns1.sub.example.com":
            return _axfr_result(
                nameserver,
                True,
                ["sub.example.com 300 IN A 1.2.3.4"],
                None,
            )
        return _axfr_result(nameserver, False, [], "refused")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
        recursive=True,
        max_depth=2,
    )

    assert results["recursive"] is True
    assert results["max_depth"] == 2
    assert results["axfr_success"] is True
    # Should have attempted AXFR against ns1.example.com (depth 1)
    # and then against ns1.sub.example.com (depth 2, discovered from NS records)
    assert len(axfr_calls) >= 2
    # Check recursive AXFR results
    recursive_axfr = results.get("recursive_axfr", [])
    assert len(recursive_axfr) >= 1
    assert any(entry["depth"] == 2 for entry in recursive_axfr)


def test_run_dnsbrute_recursive_respects_max_depth(monkeypatch) -> None:
    """Test that recursive AXFR respects max_depth limit."""
    axfr_calls = []

    def fake_axfr(nameserver, zone, timeout=2.0):
        axfr_calls.append((nameserver, zone))
        if zone == "example.com" and nameserver == "ns1.example.com":
            return _axfr_result(
                nameserver,
                True,
                [
                    "example.com 300 IN NS ns1.example.com",
                    "example.com 300 IN NS ns2.example.com",
                    "sub.example.com 300 IN NS ns1.sub.example.com",
                ],
                None,
            )
        if zone == "example.com" and nameserver == "ns1.sub.example.com":
            return _axfr_result(
                nameserver,
                True,
                [
                    "sub.example.com 300 IN NS ns1.deep.example.com",
                ],
                None,
            )
        if zone == "example.com" and nameserver == "ns1.deep.example.com":
            return _axfr_result(
                nameserver,
                True,
                ["deep.example.com 300 IN A 1.2.3.4"],
                None,
            )
        return _axfr_result(nameserver, False, [], "refused")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    # max_depth=2 should only go to depth 2, not depth 3
    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
        recursive=True,
        max_depth=2,
    )

    # Should not have called AXFR for ns1.deep.example.com (depth 3)
    ns_names = [call[0] for call in axfr_calls]
    assert "ns1.deep.example.com" not in ns_names
    # Should have recursive results up to depth 2
    recursive_axfr = results.get("recursive_axfr", [])
    depths = [entry["depth"] for entry in recursive_axfr]
    assert max(depths) <= 2


def test_run_dnsbrute_recursive_filters_non_subdomain_ns(monkeypatch) -> None:
    """Test that recursive AXFR only follows NS records that are subdomains of the target."""
    axfr_calls = []

    def fake_axfr(nameserver, zone, timeout=2.0):
        axfr_calls.append((nameserver, zone))
        if zone == "example.com" and nameserver == "ns1.example.com":
            # Return NS records including one that's NOT a subdomain
            return _axfr_result(
                nameserver,
                True,
                [
                    "example.com 300 IN NS ns1.example.com",
                    "example.com 300 IN NS ns1.otherdomain.com",  # Not a subdomain
                    "sub.example.com 300 IN NS ns1.sub.example.com",  # Is a subdomain
                ],
                None,
            )
        if zone == "example.com" and nameserver == "ns1.sub.example.com":
            return _axfr_result(nameserver, True, ["sub.example.com 300 IN A 1.2.3.4"], None)
        return _axfr_result(nameserver, False, [], "refused")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
        recursive=True,
        max_depth=2,
    )

    # Should only have recursed to ns1.sub.example.com, not ns1.otherdomain.com
    ns_names = [call[0] for call in axfr_calls]
    assert "ns1.otherdomain.com" not in ns_names
    assert "ns1.sub.example.com" in ns_names


def test_format_dnsbrute_report_json_recursive() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": True,
                "records_count": 2,
                "records": ["example.com 300 IN NS ns1.example.com"],
                "error": None,
            }
        ],
        "axfr_success": True,
        "axfr_total_records": 2,
        "recursive_axfr": [
            {
                "nameserver": "ns1.sub.example.com",
                "zone": "example.com",
                "depth": 2,
                "success": True,
                "records_count": 1,
                "records": ["sub.example.com 300 IN A 1.2.3.4"],
                "error": None,
            }
        ],
        "recursive_axfr_total_records": 1,
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_dnsbrute_report_json(data)
    assert "example.com" in output
    assert "recursive_axfr" in output
    assert "ns1.sub.example.com" in output
    assert '"depth": 2' in output
    assert "recursive_axfr_total_records" in output


def test_format_dnsbrute_report_markdown_recursive() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": True,
                "records_count": 2,
                "records": ["example.com 300 IN NS ns1.example.com"],
                "error": None,
            }
        ],
        "axfr_success": True,
        "axfr_total_records": 2,
        "recursive_axfr": [
            {
                "nameserver": "ns1.sub.example.com",
                "zone": "example.com",
                "depth": 2,
                "success": True,
                "records_count": 1,
                "records": ["sub.example.com 300 IN A 1.2.3.4"],
                "error": None,
            }
        ],
        "recursive_axfr_total_records": 1,
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_dnsbrute_report_markdown(data)
    assert "# ethscan DNS Brute Force Report" in output
    assert "**Recursive AXFR:** Yes (max depth: 2)" in output
    assert "**Recursive AXFR Records:** 1" in output
    assert "## Recursive AXFR Attempts" in output
    assert "ns1.sub.example.com" in output
    assert "depth: 2" in output
    assert "sub.example.com 300 IN A 1.2.3.4" in output


def test_format_dnsbrute_report_csv() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["1.2.3.4"], "aaaa": ["::1"]},
            {"subdomain": "api", "hostname": "api.example.com", "a": [], "aaaa": []},
        ],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "domain", "record_type", "subdomain", "hostname", "a_records", "aaaa_records", "resolved", "nameserver", "zone", "depth", "success", "error", "record"]
    assert reader[1] == ["example.com", "example.com", "subdomain", "www", "www.example.com", "1.2.3.4", "::1", "true", "", "", "", "", "", ""]
    assert reader[2] == ["example.com", "example.com", "subdomain", "api", "api.example.com", "", "", "false", "", "", "", "", "", ""]


def test_format_dnsbrute_report_csv_empty() -> None:
    data = {"target": "example.com", "domain": "example.com", "all_results": []}
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0][0] == "target"
    assert reader[0] == ["target", "domain", "record_type", "subdomain", "hostname", "a_records", "aaaa_records", "resolved", "nameserver", "zone", "depth", "success", "error", "record"]


def test_format_dnsbrute_report_csv_multi_ip() -> None:
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["1.1.1.1", "2.2.2.2"], "aaaa": []},
        ],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[1][5] == "1.1.1.1 2.2.2.2"


def test_format_dnsbrute_report_csv_axfr_records() -> None:
    """Test CSV output includes AXFR zone-transfer records."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [],
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": True,
                "records_count": 2,
                "records": [
                    "example.com 300 IN SOA ns1.example.com. admin.example.com. 2023010101 7200 3600 1209600 3600",
                    "example.com 300 IN NS ns1.example.com",
                ],
                "error": None,
            },
            {
                "nameserver": "ns2.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            },
        ],
        "recursive_axfr": [],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))

    # Header
    assert reader[0] == [
        "target",
        "domain",
        "record_type",
        "subdomain",
        "hostname",
        "a_records",
        "aaaa_records",
        "resolved",
        "nameserver",
        "zone",
        "depth",
        "success",
        "error",
        "record",
    ]

    # First AXFR record (SOA)
    assert reader[1][0] == "example.com"
    assert reader[1][1] == "example.com"
    assert reader[1][2] == "axfr"
    assert reader[1][8] == "ns1.example.com"
    assert reader[1][9] == "example.com"
    assert reader[1][10] == "1"
    assert reader[1][11] == "true"
    assert reader[1][12] == ""
    assert "SOA" in reader[1][13]
    assert "ns1.example.com" in reader[1][13]

    # Second AXFR record (NS)
    assert reader[2][2] == "axfr"
    assert reader[2][8] == "ns1.example.com"
    assert "NS" in reader[2][13]

    # Failed AXFR attempt (empty records but metadata preserved)
    assert reader[3][2] == "axfr"
    assert reader[3][8] == "ns2.example.com"
    assert reader[3][11] == "false"
    assert reader[3][12] == "transfer refused (REFUSED)"
    assert reader[3][13] == ""


def test_format_dnsbrute_report_csv_recursive_axfr() -> None:
    """Test CSV output includes recursive AXFR records."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [],
        "axfr": [],
        "recursive_axfr": [
            {
                "nameserver": "ns1.sub.example.com",
                "zone": "example.com",
                "depth": 2,
                "success": True,
                "records_count": 1,
                "records": ["sub.example.com 300 IN A 1.2.3.4"],
                "error": None,
            }
        ],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))

    # Header + 1 recursive AXFR record
    assert len(reader) == 2
    assert reader[1][2] == "recursive_axfr"
    assert reader[1][8] == "ns1.sub.example.com"
    assert reader[1][9] == "example.com"
    assert reader[1][10] == "2"
    assert reader[1][11] == "true"
    assert reader[1][13] == "sub.example.com 300 IN A 1.2.3.4"


def test_format_dnsbrute_report_csv_axfr_escaping() -> None:
    """Test CSV properly escapes commas and quotes in AXFR records."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [],
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": True,
                "records_count": 1,
                "records": ['example.com 300 IN TXT "hello, world"', "example.com 300 IN MX 10 mail,backup.example.com"],
                "error": None,
            }
        ],
        "recursive_axfr": [],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))

    # CSV writer should handle escaping
    assert len(reader) == 3  # header + 2 records
    assert "hello, world" in reader[1][13]
    assert "mail,backup.example.com" in reader[2][13]


def test_format_dnsbrute_report_csv_mixed_subdomain_and_axfr() -> None:
    """Test CSV output with both subdomain results and AXFR records."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["1.2.3.4"], "aaaa": []},
        ],
        "axfr": [
            {
                "nameserver": "ns1.example.com",
                "zone": "example.com",
                "depth": 1,
                "success": True,
                "records_count": 1,
                "records": ["example.com 300 IN NS ns1.example.com"],
                "error": None,
            }
        ],
        "recursive_axfr": [],
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))

    assert len(reader) == 3  # header + subdomain + axfr
    # First row: subdomain
    assert reader[1][2] == "subdomain"
    assert reader[1][3] == "www"
    assert reader[1][5] == "1.2.3.4"
    # Second row: AXFR
    assert reader[2][2] == "axfr"
    assert reader[2][8] == "ns1.example.com"
    assert "NS" in reader[2][13]


# ---------------------------------------------------------------------------
# _parse_dns_name edge cases (truncated / malformed DNS names)
# ---------------------------------------------------------------------------


def test_parse_dns_name_empty_data_breaks_on_offset_check() -> None:
    """Offset beyond data exits immediately (line 103)."""
    assert _parse_dns_name(b"", 0) == ("", 0)


def test_parse_dns_name_truncated_compression_pointer() -> None:
    """Compression pointer with no following byte is skipped (lines 110-111)."""
    assert _parse_dns_name(b"\xc0", 0) == ("", 2)


def test_parse_dns_name_invalid_length_byte() -> None:
    """A high-bit length byte that is not a pointer stops parsing (lines 123-124)."""
    assert _parse_dns_name(b"\x80", 0) == ("", 1)


def test_parse_dns_name_label_past_end_of_data() -> None:
    """A declared label longer than the remaining data stops parsing (line 127)."""
    assert _parse_dns_name(b"\x03ab", 0) == ("", 1)


# ---------------------------------------------------------------------------
# parse_dns_response edge cases (question section, truncated answers)
# ---------------------------------------------------------------------------


def _encode_question(name: str) -> bytes:
    body = b""
    for label in name.split("."):
        body += bytes([len(label)]) + label.encode()
    body += b"\x00"
    body += struct.pack(">HH", 1, 1)
    return body


def test_parse_dns_response_parses_question_section() -> None:
    """A non-empty question section advances the offset (lines 182-183)."""
    header = struct.pack(">HHHHHH", 0xABCD, 0x8000, 1, 0, 0, 0)
    data = header + _encode_question("example.com")
    parsed = parse_dns_response(data)
    assert parsed["valid"] is True
    assert parsed["query_id"] == 0xABCD
    assert parsed["question_count"] == 1
    assert parsed["answers"] == []


def test_parse_dns_response_truncated_answer_record() -> None:
    """An answer record header truncated past the end stops parsing (line 189)."""
    header = struct.pack(">HHHHHH", 0xABCD, 0x8000, 0, 1, 0, 0)
    name = _encode_dns_name("example.com")[:-1]  # 9 bytes, no room for fixed header
    data = header + name
    parsed = parse_dns_response(data)
    assert parsed["valid"] is True
    assert parsed["answer_count"] == 1
    assert parsed["answers"] == []


# ---------------------------------------------------------------------------
# dnspython branches via fake-dns injection + reload (dnspython not installed)
# ---------------------------------------------------------------------------


def _install_fake_dns(monkeypatch):
    """Inject a fake dns package so dnsbrute's dnspython import path is exercised."""
    import sys
    import types

    dns_pkg = types.ModuleType("dns")
    dns_pkg.__path__ = []
    dns_resolver = types.ModuleType("dns.resolver")
    dns_exception = types.ModuleType("dns.exception")
    dns_query = types.ModuleType("dns.query")
    dns_zone = types.ModuleType("dns.zone")

    class DNSException(Exception):
        pass

    class FormError(DNSException):
        pass

    dns_exception.DNSException = DNSException
    dns_exception.FormError = FormError

    class _Resolver:
        def __init__(self):
            self.timeout = None
            self.lifetime = None
            self.nameservers = []

        def resolve(self, hostname, rdtype):
            return []

    dns_resolver.Resolver = _Resolver
    dns_pkg.resolver = dns_resolver
    dns_pkg.exception = dns_exception
    dns_pkg.query = dns_query
    dns_pkg.zone = dns_zone

    monkeypatch.setitem(sys.modules, "dns", dns_pkg)
    monkeypatch.setitem(sys.modules, "dns.resolver", dns_resolver)
    monkeypatch.setitem(sys.modules, "dns.exception", dns_exception)
    monkeypatch.setitem(sys.modules, "dns.query", dns_query)
    monkeypatch.setitem(sys.modules, "dns.zone", dns_zone)
    return dns_pkg, dns_resolver, dns_exception, dns_query, dns_zone


def _reload_dnsbrute(monkeypatch):
    """Reload ethscan.dnsbrute with the fake dns package bound."""
    from importlib import reload

    import ethscan.dnsbrute as dnsbrute_mod

    _install_fake_dns(monkeypatch)
    reload(dnsbrute_mod)
    return dnsbrute_mod


def _restore_dnsbrute(monkeypatch):
    """Remove the fake dns package and restore ethscan.dnsbrute to stdlib-only state."""
    import sys
    from importlib import reload

    import ethscan.dnsbrute as dnsbrute_mod

    monkeypatch.delitem(sys.modules, "dns", raising=False)
    monkeypatch.delitem(sys.modules, "dns.resolver", raising=False)
    monkeypatch.delitem(sys.modules, "dns.exception", raising=False)
    monkeypatch.delitem(sys.modules, "dns.query", raising=False)
    monkeypatch.delitem(sys.modules, "dns.zone", raising=False)
    reload(dnsbrute_mod)


def test_dnsbrute_dns_available_module_imports(monkeypatch) -> None:
    """Module-level dnspython imports succeed and DNS_AVAILABLE is True (lines 16-17)."""
    dnsbrute_mod = _reload_dnsbrute(monkeypatch)
    try:
        assert dnsbrute_mod.DNS_AVAILABLE is True
        assert dnsbrute_mod.dns is not None
    finally:
        _restore_dnsbrute(monkeypatch)


def test_axfr_dnspython_success_path(monkeypatch) -> None:
    """_axfr_dnspython builds records from a dnspython zone transfer (lines 303, 307-323)."""
    dnsbrute_mod = _reload_dnsbrute(monkeypatch)
    try:

        class _Rdata:
            def __init__(self, text: str) -> None:
                self.text = text

            def __str__(self) -> str:
                return self.text

        class _Rdataset:
            def __init__(self, ttl: int, rdtype_name: str, rdatas: list) -> None:
                self.ttl = ttl
                self.rdtype_name = rdtype_name
                self._rdatas = rdatas

            def __iter__(self):
                return iter(self._rdatas)

        class _Node:
            def __init__(self, rdatasets: list) -> None:
                self.rdatasets = rdatasets

        class _Zone:
            def __init__(self) -> None:
                self.nodes = {
                    "example.com": _Node(
                        [_Rdataset(300, "NS", [_Rdata("ns1.example.com")])]
                    )
                }

        def fake_xfr(nameserver, zone, timeout=None, lifetime=None):
            return object()

        def fake_from_xfr(source):
            return _Zone()

        dnsbrute_mod.dns.query.xfr = fake_xfr
        dnsbrute_mod.dns.zone.from_xfr = fake_from_xfr

        result = dnsbrute_mod.attempt_axfr("ns1.example.com", "example.com", timeout=1.0)
        assert result["success"] is True
        assert result["error"] is None
        assert result["records"] == ["example.com 300 IN NS ns1.example.com"]
    finally:
        _restore_dnsbrute(monkeypatch)


def test_axfr_dnspython_form_error_and_oserror(monkeypatch) -> None:
    """_axfr_dnspython handles FormError and generic DNS/OS errors (lines 310-313)."""
    dnsbrute_mod = _reload_dnsbrute(monkeypatch)
    try:
        form_error = dnsbrute_mod.dns.exception.FormError("boom")

        def raising_xfr(nameserver, zone, timeout=None, lifetime=None):
            raise form_error

        dnsbrute_mod.dns.query.xfr = raising_xfr
        result = dnsbrute_mod.attempt_axfr("ns1.example.com", "example.com", timeout=1.0)
        assert result["success"] is False
        assert result["error"] == "transfer refused (boom)"

        def raising_oserror(nameserver, zone, timeout=None, lifetime=None):
            raise OSError("network down")

        dnsbrute_mod.dns.query.xfr = raising_oserror
        result = dnsbrute_mod.attempt_axfr("ns2.example.com", "example.com", timeout=1.0)
        assert result["success"] is False
        assert result["error"] == "network down"
    finally:
        _restore_dnsbrute(monkeypatch)


def test_resolve_label_uses_custom_resolver(monkeypatch) -> None:
    """_resolve_label uses dnspython with a custom resolver when available (lines 374-391)."""
    dnsbrute_mod = _reload_dnsbrute(monkeypatch)
    try:

        class _Rdata:
            def __init__(self, text: str) -> None:
                self.text = text

            def __str__(self) -> str:
                return self.text

        def fake_resolve(self, hostname, rdtype):
            if rdtype == "A":
                return [_Rdata("93.184.216.34")]
            if rdtype == "AAAA":
                return [_Rdata("2606:2800:220:1:248:1893:25c8:1946")]
            return []

        dnsbrute_mod.dns.resolver.Resolver.resolve = fake_resolve

        def fake_axfr(nameserver, zone, timeout=2.0):
            return _axfr_result(nameserver, False, [], "refused")

        monkeypatch.setattr(dnsbrute_mod, "attempt_axfr", fake_axfr)

        results = dnsbrute_mod.run_dnsbrute(
            "example.com",
            nameservers=["ns1.example.com"],
            resolver="1.2.3.4",
            subdomains=["www"],
            timeout=1.0,
        )
        assert results["resolver"] == "1.2.3.4"
        assert results["dnspython_available"] is True
        by_name = {entry["subdomain"]: entry for entry in results["resolved"]}
        assert by_name["www"]["a"] == ["93.184.216.34"]
        assert by_name["www"]["aaaa"] == ["2606:2800:220:1:248:1893:25c8:1946"]
    finally:
        _restore_dnsbrute(monkeypatch)


def test_resolve_label_custom_resolver_swallows_dns_errors(monkeypatch) -> None:
    """_resolve_label swallows DNSException from A and AAAA lookups (lines 381-382, 390-391)."""
    dnsbrute_mod = _reload_dnsbrute(monkeypatch)
    try:
        dns_exception = dnsbrute_mod.dns.exception

        def fake_resolve(self, hostname, rdtype):
            raise dns_exception.DNSException("no such name")

        dnsbrute_mod.dns.resolver.Resolver.resolve = fake_resolve

        def fake_axfr(nameserver, zone, timeout=2.0):
            return _axfr_result(nameserver, False, [], "refused")

        monkeypatch.setattr(dnsbrute_mod, "attempt_axfr", fake_axfr)

        results = dnsbrute_mod.run_dnsbrute(
            "example.com",
            nameservers=["ns1.example.com"],
            resolver="1.2.3.4",
            subdomains=["www"],
            timeout=1.0,
        )
        assert results["resolver"] == "1.2.3.4"
        by_name = {entry["subdomain"]: entry for entry in results["resolved"]}
        assert by_name == {}
    finally:
        _restore_dnsbrute(monkeypatch)


# ---------------------------------------------------------------------------
# Recursive AXFR guard and failure paths
# ---------------------------------------------------------------------------


def test_run_dnsbrute_recursive_max_depth_zero_hits_guard(monkeypatch) -> None:
    """max_depth=0 stops recursion at the depth guard immediately (line 448)."""
    calls = []

    def fake_axfr(nameserver, zone, timeout=2.0):
        calls.append((nameserver, zone))
        return _axfr_result(
            nameserver, True, ["example.com 300 IN NS ns1.example.com"], None
        )

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
        recursive=True,
        max_depth=0,
    )

    assert results["recursive"] is True
    assert results["max_depth"] == 0
    assert results["recursive_axfr"] == []
    assert results["axfr"] == []
    assert calls == []


def test_run_dnsbrute_recursive_depth_two_failure(monkeypatch) -> None:
    """A failed depth-2 AXFR still records an entry with error and no records."""
    def fake_axfr(nameserver, zone, timeout=2.0):
        if nameserver == "ns1.example.com":
            return _axfr_result(
                nameserver,
                True,
                ["example.com 300 IN NS ns1.sub.example.com"],
                None,
            )
        return _axfr_result(nameserver, False, [], "transfer refused (REFUSED)")

    monkeypatch.setattr("ethscan.dnsbrute.attempt_axfr", fake_axfr)

    results = run_dnsbrute(
        "example.com",
        nameservers=["ns1.example.com"],
        subdomains=["www"],
        timeout=1.0,
        recursive=True,
        max_depth=2,
    )

    recursive = results["recursive_axfr"]
    assert len(recursive) == 1
    assert recursive[0]["nameserver"] == "ns1.sub.example.com"
    assert recursive[0]["depth"] == 2
    assert recursive[0]["success"] is False
    assert recursive[0]["error"] == "transfer refused (REFUSED)"
    assert recursive[0]["records"] == []


def test_format_dnsbrute_report_markdown_recursive_entry_with_error() -> None:
    """Markdown renderer prints the error for a failed recursive entry (line 596)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [],
        "axfr_success": False,
        "axfr_total_records": 0,
        "recursive_axfr": [
            {
                "nameserver": "ns1.sub.example.com",
                "zone": "example.com",
                "depth": 2,
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            }
        ],
        "recursive_axfr_total_records": 0,
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_dnsbrute_report_markdown(data)
    assert "## Recursive AXFR Attempts" in output
    assert "- **Error:** transfer refused (REFUSED)" in output


def test_format_dnsbrute_report_csv_recursive_entry_no_records() -> None:
    """CSV renderer emits a row for a recursive entry without records (line 719)."""
    data = {
        "target": "example.com",
        "domain": "example.com",
        "zone": "example.com",
        "nameservers": ["ns1.example.com"],
        "nameserver_source": "option",
        "dnspython_available": True,
        "axfr": [],
        "axfr_success": False,
        "axfr_total_records": 0,
        "recursive_axfr": [
            {
                "nameserver": "ns1.sub.example.com",
                "zone": "example.com",
                "depth": 2,
                "success": False,
                "records_count": 0,
                "records": [],
                "error": "transfer refused (REFUSED)",
            }
        ],
        "recursive_axfr_total_records": 0,
        "subdomains_tested": 1,
        "resolved_count": 0,
        "resolved": [],
        "all_results": [],
        "recursive": True,
        "max_depth": 2,
    }
    output = format_dnsbrute_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    rows = [row for row in reader if row[2] == "recursive_axfr"]
    assert len(rows) == 1
    assert rows[0][8] == "ns1.sub.example.com"
    assert rows[0][10] == "2"
    assert rows[0][11] == "false"
    assert rows[0][12] == "transfer refused (REFUSED)"
    assert rows[0][13] == ""
