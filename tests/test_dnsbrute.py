"""Tests for the ethscan dnsbrute module."""

import socket
import struct
import threading
from typing import List, Tuple

import pytest

from ethscan.dnsbrute import (
    DEFAULT_SUBDOMAINS,
    DEFAULT_RECURSIVE_DEPTH,
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
    query_id: int, rcode: int, answers: List[Tuple[str, int]]
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

    import ethscan.dnsbrute as dnsbrute

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

    original_resolve = dns.resolver.Resolver.resolve

    def mock_resolve(self, hostname, rdtype):
        if self.nameservers == ["8.8.8.8"]:
            if rdtype == "A" and hostname.startswith("www."):
                from dns.rrset import RRset
                from dns.rdata import from_text
                rrset = RRset(dns.name.from_text(hostname), 300, 1, 1)
                rrset.add(from_text("IN", "A", "1.2.3.4"))
                return rrset
            if rdtype == "AAAA" and hostname.startswith("www."):
                from dns.rrset import RRset
                from dns.rdata import from_text
                rrset = RRset(dns.name.from_text(hostname), 300, 1, 1)
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

    results = run_dnsbrute(
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
