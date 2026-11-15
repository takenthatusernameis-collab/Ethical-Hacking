"""Branch-coverage gap tests for the ethscan dnssec module.

Each test targets a specific partially-covered branch in ``ethscan/dnssec.py``
that the rest of the suite does not reach. The branches cover hostile or
unusual DNS responses (compression-pointer chains, mixed record types, missing
parent zones/nameservers) and hostile formatter shapes, so exercising them
guards the parser against regressions on untrusted input.

The module is referenced through a single object (``dnssec_mod``) rather than
resolved by string. Some existing tests reload ``ethscan.dnssec`` and briefly
remove it from ``sys.modules``, which can leave a stale duplicate module
object; binding to one object keeps patching and calls consistent.
"""
from __future__ import annotations

import struct
from typing import Any, cast
from unittest.mock import MagicMock

import ethscan.dnssec as dnssec_mod

DNSKEY_QTYPE = dnssec_mod.DNSKEY_QTYPE


def test_parse_dns_name_follows_second_compression_pointer() -> None:
    """A name with two chained compression pointers is followed to completion.

    Exercises the branch where the first pointer is followed (``jumped`` becomes
    True) and a second pointer is encountered: the parser must continue from the
    new pointer rather than record a second ``end_offset``.
    """
    # offset 0:  "com" then pointer to offset 10
    # offset 10: "www" then pointer back to offset 0
    data = (
        b"\x03com"          # 0..3
        b"\xc0\x0a"         # 4..5  -> pointer to offset 10
        b"\x00\x00\x00\x00"  # 6..9  padding
        b"\x03www"          # 10..13
        b"\xc0\x00"         # 14..15 -> pointer to offset 0
    )
    name, offset = dnssec_mod._parse_dns_name(data, 0)
    assert name == "com.www.com"
    # end_offset is captured from the first pointer (offset 4 + 2).
    assert offset == 6


def test_parse_dnskey_response_skips_non_dnskey_answer() -> None:
    """A response whose answer is not a DNSKEY yields no keys but succeeds.

    Exercises the branch where ``record_type != DNSKEY_QTYPE`` and the loop
    continues to the next answer instead of parsing key material.
    """
    question = b"\x07example\x03com\x00" + struct.pack(">HH", DNSKEY_QTYPE, 1)
    header = struct.pack(">HHHHHH", 0x1234, 0x8000, 1, 1, 0, 0)
    # A record (type 1) pointing at the question name, rdlength 4.
    answer = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 3600, 4) + b"\x00\x00\x00\x00"
    data = header + question + answer

    res = dnssec_mod._parse_dnskey_response(data, "example.com")
    assert res["success"] is True
    assert res["error"] is None
    assert res["keys"] == []


def test_query_dnskey_dnspython_filters_non_dnskey_rdata(monkeypatch) -> None:
    """Non-DNSKEY rdata in an answer are skipped (continue-loop branch)."""
    mock_dns = MagicMock()

    other_rdata = MagicMock()
    other_rdata.rdtype = mock_dns.rdatatype.A

    dnskey_rdata = MagicMock()
    dnskey_rdata.rdtype = mock_dns.rdatatype.DNSKEY
    dnskey_rdata.flags = 257
    dnskey_rdata.protocol = 3
    dnskey_rdata.algorithm = 8
    cast(Any, dnskey_rdata).__str__.return_value = "dummy deadbeef"

    mock_answer = MagicMock()
    mock_answer.__iter__.return_value = [other_rdata, dnskey_rdata]
    mock_answer.name = "example.com."
    mock_response = MagicMock()
    mock_response.answer = [mock_answer]
    mock_dns.query.udp.return_value = mock_response
    mock_dns.dnssec.key_id.return_value = 4242

    monkeypatch.setattr(dnssec_mod, "dns", mock_dns, raising=False)
    r = dnssec_mod._query_dnskey_dnspython("example.com", "1.2.3.4", 1.0)
    assert r["success"] is True
    keys = cast("list[dict[str, object]]", r["keys"])
    assert len(keys) == 1
    assert keys[0]["key_tag"] == 4242
    assert keys[0]["algorithm_name"] == "RSASHA256"


def test_query_ds_dnspython_filters_non_ds_rdata(monkeypatch) -> None:
    """Non-DS rdata in an answer are skipped (continue-loop branch)."""
    mock_dns = MagicMock()

    other_rdata = MagicMock()
    other_rdata.rdtype = mock_dns.rdatatype.A

    ds_rdata = MagicMock()
    ds_rdata.rdtype = mock_dns.rdatatype.DS
    ds_rdata.key_tag = 54321
    ds_rdata.algorithm = 8
    ds_rdata.digest_type = 2
    ds_rdata.digest = b"\xaa\xbb"

    mock_answer = MagicMock()
    mock_answer.__iter__.return_value = [other_rdata, ds_rdata]
    mock_answer.name = "example.com."
    mock_response = MagicMock()
    mock_response.answer = [mock_answer]
    mock_dns.query.udp.return_value = mock_response

    monkeypatch.setattr(dnssec_mod, "dns", mock_dns, raising=False)
    r = dnssec_mod._query_ds_dnspython("example.com", "1.2.3.4", 1.0)
    assert r["success"] is True
    records = cast("list[dict[str, object]]", r["records"])
    assert len(records) == 1
    rec = records[0]
    assert rec["key_tag"] == 54321
    assert rec["digest"] == "aabb"
    assert rec["digest_type_name"] == "SHA-256"


def test_run_dnssec_stdlib_root_domain_skips_ds(monkeypatch) -> None:
    """A single-label domain has parent ``.`` so no DS query is attempted.

    Exercises the ``if parent != ".":`` false branch in the stdlib path.
    """
    monkeypatch.setattr(dnssec_mod, "DNS_AVAILABLE", False)
    monkeypatch.setattr(
        dnssec_mod,
        "_resolve_nameservers",
        lambda domain, timeout: ["8.8.8.8"],
    )
    monkeypatch.setattr(
        dnssec_mod,
        "_query_dnskey_raw",
        lambda ns, domain, timeout, **kw: {
            "success": True,
            "keys": [{"name": domain}],
            "error": None,
        },
    )

    results = dnssec_mod.run_dnssec("com", timeout=1.0)
    assert results["domain"] == "com"
    assert results["validated"] is True
    # Only the DNSKEY link is added; the DS block was skipped.
    assert len(cast("list[object]", results["chain"])) == 1


def test_run_dnssec_stdlib_parent_without_nameservers_skips_ds(monkeypatch) -> None:
    """A parent zone with no resolvable nameservers skips the DS query.

    Exercises the ``if parent_ns:`` false branch in the stdlib path.
    """

    def fake_resolve(domain: str, timeout: float) -> list[str]:
        return ["8.8.8.8"] if domain == "example.com" else []

    monkeypatch.setattr(dnssec_mod, "DNS_AVAILABLE", False)
    monkeypatch.setattr(dnssec_mod, "_resolve_nameservers", fake_resolve)
    monkeypatch.setattr(
        dnssec_mod,
        "_query_dnskey_raw",
        lambda ns, domain, timeout, **kw: {
            "success": True,
            "keys": [{"name": domain}],
            "error": None,
        },
    )

    results = dnssec_mod.run_dnssec("example.com", timeout=1.0)
    assert results["domain"] == "example.com"
    assert results["validated"] is True
    assert len(cast("list[object]", results["chain"])) == 1


def test_format_dnssec_markdown_dnskey_keys_not_a_list() -> None:
    """A successful DNSKEY result whose ``keys`` is not a list renders no rows."""
    data: dict[str, Any] = {
        "target": "example.com",
        "domain": "example.com",
        "validated": True,
        "dnskey": {"success": True, "keys": "not-a-list", "error": None},
        "ds": {"success": True, "records": [], "error": None},
        "chain": [],
        "notes": [],
        "dnspython_available": False,
    }
    output = dnssec_mod.format_dnssec_report_markdown(data)
    assert "DNSKEY Records" in output
    # Header is rendered but the non-list value is never iterated into a row.
    assert "| Name | Flags | Protocol | Algorithm | Key Tag |" in output
    assert "not-a-list" not in output


def test_format_dnssec_markdown_ds_records_not_a_list() -> None:
    """A successful DS result whose ``records`` is not a list renders no rows."""
    data: dict[str, Any] = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": False, "keys": [], "error": "boom"},
        "ds": {"success": True, "records": "not-a-list", "error": None},
        "chain": [],
        "notes": [],
        "dnspython_available": False,
    }
    output = dnssec_mod.format_dnssec_report_markdown(data)
    assert "DS Records" in output
    # Header is rendered but the non-list value is never iterated into a row.
    assert "| Name | Key Tag | Algorithm | Digest Type | Digest |" in output
    assert "not-a-list" not in output