"""Tests for the ethscan ldap module."""

import csv
import io
import json
import socket
import threading

import pytest

from ethscan.ldap import (
    DEFAULT_LDAP_VERSION,
    DEFAULT_LDAPS_PORT,
    DEFAULT_PORT,
    FILTER_TAG_PRESENT,
    LDAP_TAG_BIND_REQUEST,
    LDAP_TAG_BIND_RESPONSE,
    LDAP_TAG_SEARCH_REQUEST,
    LDAP_TAG_SEARCH_RESULT_DONE,
    LDAP_TAG_SEARCH_RESULT_ENTRY,
    TAG_BOOLEAN,
    TAG_ENUMERATED,
    TAG_INTEGER,
    TAG_OCTET_STRING,
    TAG_SEQUENCE,
    TAG_SET,
    _build_bind_request,
    _build_root_dse_search,
    _int_bytes,
    _ber_length,
    _ber_tlv,
    _normalize_target,
    _parse_ldap_response,
    _read_length,
    _read_tlv,
    _send_recv,
    format_ldap_report_csv,
    format_ldap_report_json,
    format_ldap_report_markdown,
    run_ldap,
)


# ---------------------------------------------------------------------------
# Helpers to build well-formed LDAP responses
# ---------------------------------------------------------------------------


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _ber_length(len(content)) + content


def _build_bind_response(
    result_code: int = 0,
    matched_dn: bytes = b"",
    diagnostic: bytes = b"",
    version: int = None,
    message_id: int = 1,
    referral: bytes = None,
) -> bytes:
    """Build a raw LDAPMessage wrapping a BindResponse."""
    inner = b""
    if version is not None:
        inner += _tlv(TAG_INTEGER, bytes([version]))
    inner += _tlv(TAG_ENUMERATED, bytes([result_code]))
    inner += _tlv(TAG_OCTET_STRING, matched_dn)
    inner += _tlv(TAG_OCTET_STRING, diagnostic)
    if referral is not None:
        inner += _tlv(0x83, referral)
    op = _tlv(LDAP_TAG_BIND_RESPONSE, inner)
    msg = _tlv(TAG_INTEGER, bytes([message_id])) + op
    return _tlv(TAG_SEQUENCE, msg)


def _build_search_result_entry(
    dn: bytes = b"",
    attributes=None,
    message_id: int = 2,
) -> bytes:
    """Build a raw LDAPMessage wrapping a SearchResultEntry.

    ``attributes`` is a list of ``(type, [values])`` tuples.
    """
    inner = _tlv(TAG_OCTET_STRING, dn)
    for attr_type, values in (attributes or []):
        attr_inner = _tlv(TAG_OCTET_STRING, attr_type.encode("utf-8"))
        vals = b"".join(_tlv(TAG_OCTET_STRING, v.encode("utf-8")) for v in values)
        attr_inner += _tlv(TAG_SET, vals)
        inner += _tlv(TAG_SEQUENCE, attr_inner)
    op = _tlv(LDAP_TAG_SEARCH_RESULT_ENTRY, inner)
    msg = _tlv(TAG_INTEGER, bytes([message_id])) + op
    return _tlv(TAG_SEQUENCE, msg)


def _build_search_result_done(
    result_code: int = 0,
    matched_dn: bytes = b"",
    diagnostic: bytes = b"",
    message_id: int = 2,
) -> bytes:
    """Build a raw LDAPMessage wrapping a SearchResultDone."""
    inner = _tlv(TAG_ENUMERATED, bytes([result_code]))
    inner += _tlv(TAG_OCTET_STRING, matched_dn)
    inner += _tlv(TAG_OCTET_STRING, diagnostic)
    op = _tlv(LDAP_TAG_SEARCH_RESULT_DONE, inner)
    msg = _tlv(TAG_INTEGER, bytes([message_id])) + op
    return _tlv(TAG_SEQUENCE, msg)


def _root_dse_response() -> bytes:
    """Build a typical RootDSE search response (entry + done)."""
    entry = _build_search_result_entry(
        dn=b"",
        attributes=[
            ("namingContexts", ["dc=example,dc=com"]),
            ("supportedLDAPVersion", ["3"]),
            ("vendorName", ["OpenLDAP Project"]),
            ("vendorVersion", ["2.6.4"]),
            ("supportedSASLMechanisms", ["EXTERNAL", "PLAIN"]),
        ],
    )
    done = _build_search_result_done(result_code=0)
    return entry + done


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT == 389


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("192.168.1.100:10389")
    assert host == "192.168.1.100"
    assert port == 10389


def test_normalize_target_ldap_url_default_port() -> None:
    host, port = _normalize_target("ldap://192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT


def test_normalize_target_ldap_url_with_port() -> None:
    host, port = _normalize_target("ldap://192.168.1.100:10389")
    assert host == "192.168.1.100"
    assert port == 10389


def test_normalize_target_ldaps_url_defaults_to_636() -> None:
    host, port = _normalize_target("ldaps://192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_LDAPS_PORT == 636


def test_normalize_target_ldaps_url_with_port() -> None:
    host, port = _normalize_target("ldaps://192.168.1.100:1636")
    assert host == "192.168.1.100"
    assert port == 1636


def test_normalize_target_ipv6_with_port() -> None:
    host, port = _normalize_target("[fd00::1]:389")
    assert host == "fd00::1"
    assert port == 389


def test_normalize_target_ipv6_no_port() -> None:
    host, port = _normalize_target("[fd00::1]")
    assert host == "fd00::1"
    assert port == DEFAULT_PORT


def test_normalize_target_ipv6_url_with_port() -> None:
    host, port = _normalize_target("ldap://[fd00::1]:389")
    assert host == "fd00::1"
    assert port == 389


def test_normalize_target_strips_whitespace() -> None:
    host, port = _normalize_target("  ldap://192.168.1.100  ")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


# ---------------------------------------------------------------------------
# BER encoding helpers
# ---------------------------------------------------------------------------


def test_ber_length_short_form() -> None:
    assert _ber_length(0) == b"\x00"
    assert _ber_length(1) == b"\x01"
    assert _ber_length(127) == b"\x7f"


def test_ber_length_long_form() -> None:
    assert _ber_length(128) == b"\x81\x80"
    assert _ber_length(255) == b"\x81\xff"
    assert _ber_length(256) == b"\x82\x01\x00"
    assert _ber_length(0x10000) == b"\x83\x01\x00\x00"


def test_ber_length_negative_raises() -> None:
    with pytest.raises(ValueError):
        _ber_length(-1)


def test_ber_tlv_structure() -> None:
    tlv = _ber_tlv(TAG_OCTET_STRING, b"abc")
    assert tlv == b"\x04\x03abc"


def test_int_bytes() -> None:
    assert _int_bytes(0) == b"\x00"
    assert _int_bytes(1) == b"\x01"
    assert _int_bytes(3) == b"\x03"
    assert _int_bytes(127) == b"\x7f"
    assert _int_bytes(128) == b"\x00\x80"  # sign bit kept clear
    assert _int_bytes(256) == b"\x01\x00"


def test_int_bytes_negative_raises() -> None:
    with pytest.raises(ValueError):
        _int_bytes(-1)


# ---------------------------------------------------------------------------
# _build_bind_request
# ---------------------------------------------------------------------------


def test_build_bind_request_structure() -> None:
    request = _build_bind_request()
    # Outer SEQUENCE envelope.
    assert request[0] == TAG_SEQUENCE
    # messageID INTEGER = 1, then bindRequest [APPLICATION 0].
    assert request[2] == TAG_INTEGER
    assert request[5] == LDAP_TAG_BIND_REQUEST


def test_build_bind_request_version_3() -> None:
    request = _build_bind_request(3)
    # The bindRequest content is a single INTEGER with value 3.
    assert request[7:10] == bytes([TAG_INTEGER, 0x01, 0x03])


def test_build_bind_request_version_2() -> None:
    request = _build_bind_request(2)
    assert request[7:10] == bytes([TAG_INTEGER, 0x01, 0x02])


def test_build_bind_request_message_id() -> None:
    request = _build_bind_request(message_id=7)
    assert request[2:5] == bytes([TAG_INTEGER, 0x01, 0x07])


def test_build_bind_request_length_consistency() -> None:
    request = _build_bind_request()
    outer_len = _read_length(request, 1)[0]
    assert outer_len == len(request) - 2  # tag + length consumed


def test_build_bind_request_deterministic() -> None:
    assert _build_bind_request() == _build_bind_request()


# ---------------------------------------------------------------------------
# _build_root_dse_search
# ---------------------------------------------------------------------------


def test_build_root_dse_search_structure() -> None:
    request = _build_root_dse_search()
    assert request[0] == TAG_SEQUENCE
    assert request[2] == TAG_INTEGER
    assert request[5] == LDAP_TAG_SEARCH_REQUEST


def test_build_root_dse_search_base_object_empty() -> None:
    request = _build_root_dse_search()
    # searchRequest content starts with baseObject OCTET STRING (empty DN).
    assert request[7:9] == bytes([TAG_OCTET_STRING, 0x00])


def test_build_root_dse_search_filter_is_present_objectclass() -> None:
    request = _build_root_dse_search()
    assert bytes([FILTER_TAG_PRESENT, 0x0B]) + b"objectClass" in request


def test_build_root_dse_search_empty_attribute_list() -> None:
    request = _build_root_dse_search()
    # Trailing empty SEQUENCE (AttributeDescriptionList).
    assert request.endswith(bytes([TAG_SEQUENCE, 0x00]))


def test_build_root_dse_search_message_id() -> None:
    request = _build_root_dse_search(message_id=9)
    assert request[2:5] == bytes([TAG_INTEGER, 0x01, 0x09])


# ---------------------------------------------------------------------------
# _read_length / _read_tlv
# ---------------------------------------------------------------------------


def test_read_length_short_form() -> None:
    assert _read_length(b"\x05ab", 0) == (5, 1)


def test_read_length_long_form() -> None:
    assert _read_length(b"\x81\x80" + b"x" * 128, 0) == (128, 2)


def test_read_length_truncated_raises() -> None:
    # Long-form length declared but no length octets follow.
    with pytest.raises(ValueError):
        _read_length(b"\x81", 0)


def test_read_length_short_form_needs_no_content() -> None:
    # A short-form length is readable even when the content is absent;
    # the truncation is caught by the TLV reader instead.
    assert _read_length(b"\x05", 0) == (5, 1)


def test_read_tlv_basic() -> None:
    tag, content, end = _read_tlv(b"\x04\x03abc\x00", 0)
    assert tag == TAG_OCTET_STRING
    assert content == b"abc"
    assert end == 5


def test_read_tlv_truncated_content_raises() -> None:
    with pytest.raises(ValueError):
        _read_tlv(b"\x04\x03ab", 0)


def test_read_tlv_offset_past_end_raises() -> None:
    with pytest.raises(ValueError):
        _read_tlv(b"", 0)


# ---------------------------------------------------------------------------
# _parse_ldap_response
# ---------------------------------------------------------------------------


def test_parse_bind_success() -> None:
    parsed = _parse_ldap_response(_build_bind_response(result_code=0))
    assert parsed["error"] is None
    assert parsed["message_id"] == 1
    assert parsed["protocol_op"] == "bindResponse"
    assert parsed["protocol_op_tag"] == LDAP_TAG_BIND_RESPONSE
    assert parsed["result_code"] == 0
    assert parsed["result_code_name"] == "success"
    assert parsed["matched_dn"] == ""
    assert parsed["diagnostic_message"] == ""


def test_parse_bind_invalid_credentials() -> None:
    parsed = _parse_ldap_response(
        _build_bind_response(result_code=49, diagnostic=b"invalid credentials"),
    )
    assert parsed["result_code"] == 49
    assert parsed["result_code_name"] == "invalidCredentials"
    assert parsed["diagnostic_message"] == "invalid credentials"


def test_parse_bind_operations_error() -> None:
    parsed = _parse_ldap_response(_build_bind_response(result_code=1))
    assert parsed["result_code"] == 1
    assert parsed["result_code_name"] == "operationsError"


def test_parse_bind_response_with_version() -> None:
    parsed = _parse_ldap_response(_build_bind_response(version=3))
    assert parsed["version"] == 3


def test_parse_bind_matched_dn_and_diagnostic() -> None:
    parsed = _parse_ldap_response(
        _build_bind_response(
            result_code=32,
            matched_dn=b"dc=example,dc=com",
            diagnostic=b"no such object",
        ),
    )
    assert parsed["matched_dn"] == "dc=example,dc=com"
    assert parsed["diagnostic_message"] == "no such object"


def test_parse_bind_referral() -> None:
    parsed = _parse_ldap_response(
        _build_bind_response(result_code=10, referral=b"ldap://other.example.com"),
    )
    assert parsed["result_code"] == 10
    assert parsed["referral"] == "ldap://other.example.com"


def test_parse_unknown_result_code() -> None:
    parsed = _parse_ldap_response(_build_bind_response(result_code=123))
    assert parsed["result_code"] == 123
    assert parsed["result_code_name"] == "unknown (123)"


def test_parse_search_result_entry() -> None:
    response = _build_search_result_entry(
        dn=b"dc=example,dc=com",
        attributes=[("namingContexts", ["dc=example,dc=com"])],
    )
    parsed = _parse_ldap_response(response)
    assert parsed["error"] is None
    assert parsed["protocol_op"] == "searchResultEntry"
    assert len(parsed["entries"]) == 1
    entry = parsed["entries"][0]
    assert entry["dn"] == "dc=example,dc=com"
    assert entry["attributes"]["namingContexts"] == ["dc=example,dc=com"]


def test_parse_search_result_done() -> None:
    parsed = _parse_ldap_response(_build_search_result_done(result_code=0))
    assert parsed["protocol_op"] == "searchResultDone"
    assert parsed["result_code"] == 0


def test_parse_multiple_messages_entry_then_done() -> None:
    response = _root_dse_response()
    parsed = _parse_ldap_response(response)
    assert parsed["error"] is None
    assert parsed["message_id"] == 2  # last message wins
    assert len(parsed["entries"]) == 1
    assert parsed["result_code"] == 0  # from SearchResultDone


def test_parse_root_dse_attributes() -> None:
    response = _build_search_result_entry(
        attributes=[
            ("supportedLDAPVersion", ["3"]),
            ("supportedSASLMechanisms", ["EXTERNAL", "PLAIN"]),
        ],
    )
    parsed = _parse_ldap_response(response)
    attrs = parsed["entries"][0]["attributes"]
    assert attrs["supportedLDAPVersion"] == ["3"]
    assert attrs["supportedSASLMechanisms"] == ["EXTERNAL", "PLAIN"]


def test_parse_empty_response() -> None:
    parsed = _parse_ldap_response(None)
    assert parsed["error"] == "no response received"
    parsed = _parse_ldap_response(b"")
    assert parsed["error"] == "no response received"


def test_parse_truncated_response() -> None:
    response = _build_bind_response(result_code=0)
    parsed = _parse_ldap_response(response[:-1])
    assert parsed["error"] is not None
    assert "malformed" in parsed["error"]


def test_parse_non_ldap_response() -> None:
    # A well-formed BER TLV that is not a SEQUENCE is not an LDAP message.
    parsed = _parse_ldap_response(b"\x04\x03abc")
    assert parsed["error"] is not None
    assert "not an LDAP message" in parsed["error"]


def test_parse_truncated_ldap_response() -> None:
    # 'H' (0x48) is a short-form length of 72, longer than the buffer.
    parsed = _parse_ldap_response(b"HTTP/1.1 200 OK\r\n\r\n")
    assert parsed["error"] is not None
    assert "malformed" in parsed["error"]


def test_parse_unknown_protocol_op() -> None:
    inner = _tlv(TAG_ENUMERATED, b"\x00") + _tlv(TAG_OCTET_STRING, b"") + _tlv(TAG_OCTET_STRING, b"")
    op = _tlv(0x70, inner)  # unknown application tag
    msg = _tlv(TAG_INTEGER, b"\x01") + op
    response = _tlv(TAG_SEQUENCE, msg)
    parsed = _parse_ldap_response(response)
    assert parsed["error"] is None
    assert parsed["protocol_op"].startswith("unknown (0x70")
    # Result content is only decoded for known result-type ops.
    assert parsed["result_code"] is None


def test_parse_empty_message_content() -> None:
    # A SEQUENCE with no content: no messageID to read.
    response = _tlv(TAG_SEQUENCE, b"")
    parsed = _parse_ldap_response(response)
    assert parsed["error"] is not None
    assert "malformed LDAP message" in parsed["error"]


def test_parse_raw_preview_capped() -> None:
    response = _build_bind_response(diagnostic=b"x" * 200)
    parsed = _parse_ldap_response(response)
    assert len(parsed["raw_preview"]) <= 96  # 48 bytes -> 96 hex chars


# ---------------------------------------------------------------------------
# _send_recv
# ---------------------------------------------------------------------------


def test_send_recv_with_connector() -> None:
    def connector(host, port, request, timeout):
        assert host == "192.168.1.100"
        assert port == 389
        return b"data", None

    data, err = _send_recv("192.168.1.100", 389, b"req", 1.0, connector=connector)
    assert data == b"data"
    assert err is None


def test_send_recv_with_connector_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    data, err = _send_recv("192.168.1.100", 389, b"req", 1.0, connector=connector)
    assert data is None
    assert err == "timeout"


def test_send_recv_real_socket_refused() -> None:
    # Bind a socket to reserve a port, close it, then probe it: the
    # connection should be refused and reported as an error string.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    listener.close()
    data, err = _send_recv("127.0.0.1", port, b"req", 1.0)
    assert data is None
    assert err is not None


# ---------------------------------------------------------------------------
# run_ldap
# ---------------------------------------------------------------------------


def _success_connector(host, port, request, timeout):
    """Fake connector: anonymous bind success + full RootDSE."""
    if request[5] == LDAP_TAG_BIND_REQUEST:
        return _build_bind_response(result_code=0), None
    return _root_dse_response(), None


def test_run_ldap_success_with_root_dse() -> None:
    results = run_ldap("192.168.1.100", connector=_success_connector)
    assert results["accessible"] is True
    assert results["host"] == "192.168.1.100"
    assert results["port"] == DEFAULT_PORT
    assert results["anonymous_bind"] is True
    assert results["bind_result_code"] == 0
    assert results["bind_result"] == "success"
    assert results["error"] is None
    assert results["root_dse"]["namingContexts"] == ["dc=example,dc=com"]
    assert results["root_dse"]["vendorName"] == ["OpenLDAP Project"]
    assert results["root_dse"]["supportedSASLMechanisms"] == ["EXTERNAL", "PLAIN"]
    assert results["root_dse_error"] is None
    assert results["banner"] is not None
    assert "anonymous bind allowed" in results["banner"]


def test_run_ldap_anonymous_bind_denied() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(
                result_code=49, diagnostic=b"invalid credentials",
            ), None
        return _root_dse_response(), None

    results = run_ldap("ldap://192.168.1.100", connector=connector)
    assert results["accessible"] is True
    assert results["anonymous_bind"] is False
    assert results["bind_result_code"] == 49
    assert results["diagnostic_message"] == "invalid credentials"
    assert any("invalidCredentials" in n for n in results["notes"])
    # RootDSE still probed and reported.
    assert results["root_dse"]["vendorName"] == ["OpenLDAP Project"]


def test_run_ldap_protocol_error_note_for_v3() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=2), None
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["bind_result_code"] == 2
    assert any("--ldap-version 2" in n for n in results["notes"])


def test_run_ldap_no_protocol_error_note_for_v2() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=2), None
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", ldap_version=2, connector=connector)
    assert results["ldap_version"] == 2
    assert not any("--ldap-version 2" in n for n in results["notes"])


def test_run_ldap_timeout() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "bind request failed: timeout"
    assert results["anonymous_bind"] is False


def test_run_ldap_refused() -> None:
    def connector(host, port, request, timeout):
        return None, "Connection refused"

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert "Connection refused" in results["error"]


def test_run_ldap_no_response() -> None:
    def connector(host, port, request, timeout):
        return None, None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is False
    assert results["error"] == "bind request failed: no response"


def test_run_ldap_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["port"] = port
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", port=10389, connector=connector)
    assert results["port"] == 10389
    assert captured["port"] == 10389


def test_run_ldap_ldap_version_passthrough() -> None:
    requests = []

    def connector(host, port, request, timeout):
        requests.append(bytes(request))
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", ldap_version=2, connector=connector)
    assert results["ldap_version"] == 2
    assert len(requests) == 2
    # The bind request (first probe) encodes version 2.
    assert requests[0][7:10] == bytes([TAG_INTEGER, 0x01, 0x02])


def test_run_ldap_sends_bind_then_search() -> None:
    requests = []

    def connector(host, port, request, timeout):
        requests.append(bytes(request))
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is True
    assert len(requests) == 2
    assert requests[0][5] == LDAP_TAG_BIND_REQUEST
    assert requests[1][5] == LDAP_TAG_SEARCH_REQUEST


def test_run_ldap_bind_malformed_response() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return b"\x30\x01\x00", None  # malformed: content has no TLV
        return _root_dse_response(), None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is True  # a response was received
    assert results["error"] is not None
    assert "malformed LDAP message" in results["error"]


def test_run_ldap_root_dse_search_error() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return None, "timeout"

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["accessible"] is True
    assert results["anonymous_bind"] is True
    assert results["root_dse"] == {}
    assert results["root_dse_error"] == "root DSE search failed: timeout"


def test_run_ldap_root_dse_no_response() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return None, None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["root_dse_error"] == "root DSE search failed: no response"


def test_run_ldap_root_dse_access_denied() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return _build_search_result_done(result_code=50), None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["root_dse"] == {}
    assert results["root_dse_error"] == "root DSE search returned insufficientAccessRights"


def test_run_ldap_root_dse_malformed() -> None:
    def connector(host, port, request, timeout):
        if request[5] == LDAP_TAG_BIND_REQUEST:
            return _build_bind_response(result_code=0), None
        return b"not-ldap", None

    results = run_ldap("192.168.1.100", connector=connector)
    assert results["root_dse"] == {}
    assert results["root_dse_error"] is not None


def test_run_ldap_unresolvable_host() -> None:
    results = run_ldap("nonexistent.invalid.domain.tld", timeout=0.5)
    assert results["accessible"] is False
    assert results["error"] is not None
    assert "bind request failed" in results["error"]


def test_run_ldap_ldaps_url_implies_tls() -> None:
    results = run_ldap("ldaps://192.168.1.100:636", connector=_success_connector)
    assert results["port"] == 636
    assert results["protocol"] == "LDAPS"


def test_run_ldap_port_636_implies_tls() -> None:
    results = run_ldap("192.168.1.100", port=636, connector=_success_connector)
    assert results["protocol"] == "LDAPS"


def test_run_ldap_send_recv_tls_against_plain_listener() -> None:
    # A TLS-wrapped probe against a plain TCP listener fails the
    # handshake and must surface a graceful error, not raise.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def acceptor():
        try:
            conn, _ = listener.accept()
            conn.recv(4096)
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=acceptor, daemon=True)
    thread.start()
    try:
        data, err = _send_recv("127.0.0.1", port, b"req", 2.0, use_tls=True)
        assert data is None
        assert err is not None
    finally:
        thread.join(timeout=3.0)
        listener.close()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _mock_results(target: str = "192.168.1.100") -> dict:
    return {
        "target": target,
        "host": "192.168.1.100",
        "port": 389,
        "accessible": True,
        "protocol": "LDAP",
        "ldap_version": 3,
        "message_id": 1,
        "bind_result_code": 0,
        "bind_result": "success",
        "matched_dn": "",
        "diagnostic_message": "",
        "referral": None,
        "anonymous_bind": True,
        "root_dse": {
            "namingContexts": ["dc=example,dc=com"],
            "supportedLDAPVersion": ["3"],
            "vendorName": ["OpenLDAP Project"],
            "vendorVersion": ["2.6.4"],
            "supportedSASLMechanisms": ["EXTERNAL", "PLAIN"],
        },
        "root_dse_error": None,
        "banner": "LDAPv3; anonymous bind allowed; vendor=OpenLDAP Project",
        "raw_preview": "3008020101",
        "notes": [],
        "error": None,
    }


def test_format_ldap_report_json() -> None:
    report = format_ldap_report_json(_mock_results())
    parsed = json.loads(report)
    assert parsed["accessible"] is True
    assert parsed["anonymous_bind"] is True
    assert parsed["root_dse"]["vendorName"] == ["OpenLDAP Project"]


def test_format_ldap_report_json_inaccessible() -> None:
    results = _mock_results()
    results["accessible"] = False
    results["error"] = "bind request failed: timeout"
    parsed = json.loads(format_ldap_report_json(results))
    assert parsed["accessible"] is False
    assert parsed["error"] == "bind request failed: timeout"


def test_format_ldap_report_markdown() -> None:
    report = format_ldap_report_markdown(_mock_results())
    assert "# ethscan LDAP Reconnaissance Report" in report
    assert "## Anonymous Bind" in report
    assert "**Anonymous Bind:** Yes" in report
    assert "**Result:** success" in report
    assert "## Server Identity (RootDSE)" in report
    assert "**vendorName:** OpenLDAP Project" in report
    assert "**namingContexts:** dc=example,dc=com" in report
    assert "**supportedSASLMechanisms:** EXTERNAL, PLAIN" in report
    assert "## Response Preview" in report


def test_format_ldap_report_markdown_bind_denied() -> None:
    results = _mock_results()
    results["anonymous_bind"] = False
    results["bind_result_code"] = 49
    results["bind_result"] = "invalidCredentials"
    results["diagnostic_message"] = "invalid credentials"
    results["notes"] = ["anonymous bind rejected (invalidCredentials); ..."]
    report = format_ldap_report_markdown(results)
    assert "**Anonymous Bind:** No" in report
    assert "**Result:** invalidCredentials" in report
    assert "**Diagnostic Message:** invalid credentials" in report
    assert "## Notes" in report


def test_format_ldap_report_markdown_no_root_dse() -> None:
    results = _mock_results()
    results["root_dse"] = {}
    results["root_dse_error"] = "root DSE search failed: timeout"
    report = format_ldap_report_markdown(results)
    assert "## Server Identity (RootDSE)" in report
    assert "**Error:** root DSE search failed: timeout" in report


def test_format_ldap_report_markdown_other_attributes() -> None:
    results = _mock_results()
    results["root_dse"] = {"customAttribute": ["value1", "value2"]}
    report = format_ldap_report_markdown(results)
    assert "### Other RootDSE Attributes" in report
    assert "**customAttribute:** value1, value2" in report


def test_format_ldap_report_markdown_inaccessible() -> None:
    results = _mock_results()
    results["accessible"] = False
    results["anonymous_bind"] = False
    results["error"] = "bind request failed: timeout"
    report = format_ldap_report_markdown(results)
    assert "**Accessible:** No" in report
    assert "**Error:** bind request failed: timeout" in report
    assert "**Anonymous Bind:** No" in report


def test_format_ldap_report_csv() -> None:
    report = format_ldap_report_csv(_mock_results())
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"
    assert "anonymous_bind" in reader[0]
    row = reader[1]
    assert row[0] == "192.168.1.100"
    assert row[3] == "true"  # accessible
    assert row[8] == "true"  # anonymous_bind
    assert row[11] == "OpenLDAP Project"  # vendor_name
    assert row[12] == "2.6.4"  # vendor_version
    assert row[13] == "dc=example,dc=com"  # naming_contexts
    assert row[14] == "3"  # supported_ldap_versions


def test_format_ldap_report_csv_inaccessible() -> None:
    results = _mock_results()
    results["accessible"] = False
    results["anonymous_bind"] = False
    results["error"] = "bind request failed: timeout"
    report = format_ldap_report_csv(results)
    reader = list(csv.reader(io.StringIO(report)))
    row = reader[1]
    assert row[3] == "false"
    assert row[8] == "false"
    assert row[17] == "bind request failed: timeout"


def test_format_ldap_report_csv_empty_root_dse() -> None:
    results = _mock_results()
    results["root_dse"] = {}
    report = format_ldap_report_csv(results)
    reader = list(csv.reader(io.StringIO(report)))
    row = reader[1]
    assert row[11] == ""  # vendor_name
    assert row[15] == ""  # root_dse_attributes
