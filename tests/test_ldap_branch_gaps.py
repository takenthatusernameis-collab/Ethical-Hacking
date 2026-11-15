"""Focused branch-coverage tests for ethscan.ldap.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/ldap.py over tests/test_ldap.py, tests/test_ldap_hostile_sweep.py and
tests/test_ldap_formatter_hostile_sweep.py.

Covered in this file (reachable):
- 148->159: bracketed host with no closing bracket (e.g. "[::1")
- 155->159: unbracketed host with non-digit port suffix (e.g. "host:abc")
- 330->315: result content with a third OCTET STRING beyond matchedDN and
  diagnosticMessage (extra value ignored)
- 333->315: result content containing an unknown element tag (ignored)
- 361->363: SearchResultEntry whose first TLV is not an OCTET STRING (DN
  left empty, tolerated)
"""
from __future__ import annotations

from ethscan.ldap import (
    TAG_OCTET_STRING,
    TAG_SEQUENCE,
    _ber_length,
    _normalize_target,
    _parse_result_content,
    _parse_search_entry,
)


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _ber_length(len(content)) + content


# --- _normalize_target reachable branch gaps (148->159, 155->159) ---


def test_normalize_target_bracket_without_close() -> None:
    # 148->159: "[::1" starts with "[" but has no closing "]", so
    # close == -1 and the bracket-port branch is skipped; the host is
    # returned verbatim.
    host, port = _normalize_target("[::1")
    assert host == "[::1"
    assert port == 389


def test_normalize_target_unbracketed_nondigit_port() -> None:
    # 155->159: "host:abc" takes the unbracketed host:port branch but
    # the suffix "abc" is not digits, so the port-assignment arc is not
    # taken and the host is returned verbatim.
    host, port = _normalize_target("host:abc")
    assert host == "host:abc"
    assert port == 389


# --- _parse_result_content reachable branch gaps (330->315, 333->315) ---


def test_parse_result_content_extra_octet_string_ignored() -> None:
    # 330->315: a third OCTET STRING after matchedDN and diagnosticMessage
    # has both got_matched_dn and got_diagnostic set, so it is ignored and
    # parsing loops back to the next TLV.
    content = (
        _tlv(TAG_OCTET_STRING, b"dc=example,dc=com")
        + _tlv(TAG_OCTET_STRING, b"first diagnostic")
        + _tlv(TAG_OCTET_STRING, b"extra ignored")
    )
    result: dict[str, object] = {}
    _parse_result_content(content, result)
    assert result["matched_dn"] == "dc=example,dc=com"
    assert result["diagnostic_message"] == "first diagnostic"
    assert "extra" not in str(result)


def test_parse_result_content_unknown_tag_ignored() -> None:
    # 333->315: an unknown element tag (authResponse [7]) matches none of
    # the handled tags, so the elif chain is skipped and parsing loops.
    content = _tlv(0x87, b"opaque-auth-response")
    result: dict[str, object] = {}
    _parse_result_content(content, result)
    assert result == {}


# --- _parse_search_entry reachable branch gap (361->363) ---


def test_parse_search_entry_non_octet_string_first_tlv() -> None:
    # 361->363: the first TLV is a SEQUENCE rather than an OCTET STRING, so
    # the DN assignment is skipped and the entry keeps an empty DN.
    content = _tlv(TAG_SEQUENCE, b"")
    entry = _parse_search_entry(content)
    assert entry == {"dn": "", "attributes": {}}