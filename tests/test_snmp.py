"""Tests for the ethscan snmp module."""

import csv
import io
import json

import pytest

from ethscan.snmp import (
    DEFAULT_COMMUNITIES,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    ERROR_STATUS_NAMES,
    STANDARD_OIDS,
    TAG_GET_REQUEST,
    TAG_GET_RESPONSE,
    TAG_INTEGER,
    TAG_NULL,
    TAG_OCTET_STRING,
    TAG_OID,
    TAG_SEQUENCE,
    TAG_TIMETICKS,
    _build_get_request,
    _decode_varbind_value,
    _encode_base128,
    _encode_integer,
    _encode_length,
    _encode_null,
    _encode_oid,
    _encode_oid_value,
    _encode_octet_string,
    _encode_tlv,
    _normalize_target,
    _parse_oid,
    _parse_snmp_message,
    _parse_tlv,
    _probe_community,
    _send_recv,
    format_snmp_report_csv,
    format_snmp_report_json,
    format_snmp_report_markdown,
    run_snmp,
)

SYSDESC = STANDARD_OIDS["sysDescr"]
SYSOBJECTID = STANDARD_OIDS["sysObjectID"]
SYSUPTIME = STANDARD_OIDS["sysUpTime"]
SYSNAME = STANDARD_OIDS["sysName"]


# ---------------------------------------------------------------------------
# Helpers to build well-formed SNMP messages for tests
# ---------------------------------------------------------------------------


def _build_get_response(
    version: int = 1,
    community: str = "public",
    varbinds=None,
    error_status: int = 0,
    request_id: int = 1,
) -> bytes:
    """Build an SNMP GET response message."""
    if varbinds is None:
        varbinds = []
    vb_data = b"".join(
        _encode_tlv(TAG_SEQUENCE, _encode_oid(oid) + _encode_tlv(tag, value))
        for oid, tag, value in varbinds
    )
    pdu = _encode_tlv(
        TAG_GET_RESPONSE,
        _encode_integer(request_id)
        + _encode_integer(error_status)
        + _encode_integer(0)
        + _encode_tlv(TAG_SEQUENCE, vb_data),
    )
    return _encode_tlv(
        TAG_SEQUENCE,
        _encode_integer(version) + _encode_octet_string(community) + pdu,
    )


def _system_varbinds(
    sys_descr: bytes = b"Linux router 5.4.0",
    sys_object_id: bytes = None,
    sys_up_ticks: int = 12345678,
    sys_name: bytes = b"router-01",
):
    """Build the standard MIB-II varbind list for responses."""
    if sys_object_id is None:
        sys_object_id = _encode_oid_value("1.3.6.1.4.1.9.1.1")
    return [
        (SYSDESC, TAG_OCTET_STRING, sys_descr),
        (SYSOBJECTID, TAG_OID, sys_object_id),
        (SYSUPTIME, TAG_TIMETICKS, sys_up_ticks.to_bytes(4, "big")),
        (SYSNAME, TAG_OCTET_STRING, sys_name),
    ]


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("snmp.example.com")
    assert host == "snmp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("snmp.example.com:1161")
    assert host == "snmp.example.com"
    assert port == 1161


def test_normalize_target_url_with_port() -> None:
    host, port = _normalize_target("snmp://snmp.example.com:1161")
    assert host == "snmp.example.com"
    assert port == 1161


def test_normalize_target_url_default_port() -> None:
    host, port = _normalize_target("snmp://snmp.example.com")
    assert host == "snmp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


def test_normalize_target_ipv6_url() -> None:
    host, port = _normalize_target("snmp://[::1]:161")
    assert host == "::1"
    assert port == 161
    host, port = _normalize_target("[::1]:161")
    assert host == "::1"
    assert port == 161
    host, port = _normalize_target("[::1]")
    assert host == "::1"
    assert port == DEFAULT_PORT


# ---------------------------------------------------------------------------
# BER encoding helpers
# ---------------------------------------------------------------------------


def test_encode_length_short_form() -> None:
    assert _encode_length(0) == b"\x00"
    assert _encode_length(5) == b"\x05"
    assert _encode_length(127) == b"\x7f"


def test_encode_length_long_form() -> None:
    assert _encode_length(128) == b"\x81\x80"
    assert _encode_length(200) == b"\x81\xc8"
    assert _encode_length(300) == b"\x82\x01\x2c"


def test_encode_length_negative_raises() -> None:
    with pytest.raises(ValueError):
        _encode_length(-1)


def test_encode_tlv() -> None:
    assert _encode_tlv(TAG_OCTET_STRING, b"hi") == b"\x04\x02hi"


def test_encode_integer() -> None:
    assert _encode_integer(0) == b"\x02\x01\x00"
    assert _encode_integer(1) == b"\x02\x01\x01"
    assert _encode_integer(127) == b"\x02\x01\x7f"
    assert _encode_integer(128) == b"\x02\x02\x00\x80"
    assert _encode_integer(256) == b"\x02\x02\x01\x00"
    assert _encode_integer(-1) == b"\x02\x01\xff"


def test_encode_octet_string() -> None:
    assert _encode_octet_string("pub") == b"\x04\x03pub"


def test_encode_null() -> None:
    assert _encode_null() == b"\x05\x00"


def test_encode_base128() -> None:
    assert _encode_base128(0) == b"\x00"
    assert _encode_base128(1) == b"\x01"
    assert _encode_base128(127) == b"\x7f"
    assert _encode_base128(128) == b"\x81\x00"
    # 16512 = 1*128^2 + 1*128 + 0 -> 0x81 0x81 0x00
    assert _encode_base128(16512) == b"\x81\x81\x00"


def test_encode_base128_negative_raises() -> None:
    with pytest.raises(ValueError):
        _encode_base128(-1)


def test_encode_oid_value() -> None:
    # 1.3.6.1.2.1.1.1.0 -> first byte 1*40+3=43, then 6,1,2,1,1,1,0
    assert _encode_oid_value("1.3.6.1.2.1.1.1.0") == bytes(
        [43, 6, 1, 2, 1, 1, 1, 0]
    )


def test_encode_oid_value_large_component() -> None:
    # 1.3.6.1.4.1.311 -> 311 needs base-128: 0x82 0x37
    value = _encode_oid_value("1.3.6.1.4.1.311")
    assert value == bytes([43, 6, 1, 4, 1, 0x82, 0x37])


def test_encode_oid() -> None:
    encoded = _encode_oid("1.3.6.1.2.1.1.1.0")
    assert encoded[0] == TAG_OID
    assert encoded[1] == 8  # length
    assert encoded[2:] == bytes([43, 6, 1, 2, 1, 1, 1, 0])


def test_encode_oid_single_component() -> None:
    # A lone "1" is treated as 1.0.
    assert _encode_oid_value("1") == bytes([40])


# ---------------------------------------------------------------------------
# _build_get_request
# ---------------------------------------------------------------------------


def test_build_get_request_v2c_structure() -> None:
    request = _build_get_request(1, "public", [SYSDESC])
    message = _parse_snmp_message(request)
    assert message["version"] == 1
    assert message["community"] == "public"
    assert message["pdu_type"] == "get-request"
    assert [vb["oid"] for vb in message["varbinds"]] == [SYSDESC]


def test_build_get_request_v1_version() -> None:
    request = _build_get_request(0, "private", [SYSDESC, SYSUPTIME])
    message = _parse_snmp_message(request)
    assert message["version"] == 0
    assert message["community"] == "private"
    assert [vb["oid"] for vb in message["varbinds"]] == [SYSDESC, SYSUPTIME]


def test_build_get_request_top_level_tag() -> None:
    request = _build_get_request(1, "public", [SYSDESC])
    assert request[0] == TAG_SEQUENCE


def test_build_get_request_contains_community() -> None:
    request = _build_get_request(1, "s3cr3t", [SYSDESC])
    assert b"s3cr3t" in request


def test_build_get_request_all_standard_oids() -> None:
    request = _build_get_request(1, "public", list(STANDARD_OIDS.values()))
    message = _parse_snmp_message(request)
    assert [vb["oid"] for vb in message["varbinds"]] == list(
        STANDARD_OIDS.values()
    )


# ---------------------------------------------------------------------------
# _parse_tlv / _parse_oid
# ---------------------------------------------------------------------------


def test_parse_tlv_short_length() -> None:
    tag, value, offset = _parse_tlv(b"\x04\x03abc", 0)
    assert tag == TAG_OCTET_STRING
    assert value == b"abc"
    assert offset == 5


def test_parse_tlv_long_length() -> None:
    payload = b"x" * 200
    data = b"\x04\x81\xc8" + payload
    tag, value, offset = _parse_tlv(data, 0)
    assert tag == TAG_OCTET_STRING
    assert value == payload
    assert offset == len(data)


def test_parse_tlv_truncated_raises() -> None:
    with pytest.raises(ValueError):
        _parse_tlv(b"\x04\x05ab", 0)


def test_parse_tlv_missing_length_raises() -> None:
    with pytest.raises(ValueError):
        _parse_tlv(b"\x04", 0)


def test_parse_tlv_indefinite_length_raises() -> None:
    with pytest.raises(ValueError):
        _parse_tlv(b"\x04\x80", 0)


def test_parse_oid() -> None:
    assert _parse_oid(bytes([43, 6, 1, 2, 1, 1, 1, 0])) == "1.3.6.1.2.1.1.1.0"


def test_parse_oid_empty() -> None:
    assert _parse_oid(b"") == ""


def test_parse_oid_multibyte_component() -> None:
    # 1.3.6.1.4.1.311
    assert _parse_oid(bytes([43, 6, 1, 4, 1, 0x82, 0x37])) == "1.3.6.1.4.1.311"


# ---------------------------------------------------------------------------
# _decode_varbind_value
# ---------------------------------------------------------------------------


def test_decode_varbind_octet_string() -> None:
    assert _decode_varbind_value(TAG_OCTET_STRING, b"Linux") == "Linux"


def test_decode_varbind_oid() -> None:
    assert (
        _decode_varbind_value(TAG_OID, bytes([43, 6, 1, 2, 1, 1, 2, 1, 0]))
        == "1.3.6.1.2.1.1.2.1.0"
    )


def test_decode_varbind_timeticks() -> None:
    assert _decode_varbind_value(TAG_TIMETICKS, (12345678).to_bytes(4, "big")) == 12345678


def test_decode_varbind_counter32() -> None:
    assert _decode_varbind_value(0x41, (255).to_bytes(4, "big")) == 255


def test_decode_varbind_gauge32() -> None:
    assert _decode_varbind_value(0x42, (7).to_bytes(4, "big")) == 7


def test_decode_varbind_integer() -> None:
    assert _decode_varbind_value(TAG_INTEGER, b"\xff") == -1


def test_decode_varbind_null() -> None:
    assert _decode_varbind_value(TAG_NULL, b"") is None


def test_decode_varbind_ipaddress() -> None:
    assert _decode_varbind_value(0x40, bytes([192, 168, 1, 1])) == "192.168.1.1"


def test_decode_varbind_exception_values() -> None:
    assert _decode_varbind_value(0x80, b"") is None  # endOfMibView
    assert _decode_varbind_value(0x81, b"") is None  # noSuchObject
    assert _decode_varbind_value(0x82, b"") is None  # noSuchInstance


def test_decode_varbind_unknown_type_hex() -> None:
    assert _decode_varbind_value(0x99, b"\xab\xcd") == "abcd"


# ---------------------------------------------------------------------------
# _parse_snmp_message
# ---------------------------------------------------------------------------


def test_parse_snmp_message_full_response() -> None:
    data = _build_get_response(varbinds=_system_varbinds())
    message = _parse_snmp_message(data)
    assert message["version"] == 1
    assert message["community"] == "public"
    assert message["pdu_type"] == "get-response"
    assert message["request_id"] == 1
    assert message["error_status"] == 0
    assert message["error_index"] == 0
    assert [vb["oid"] for vb in message["varbinds"]] == [
        SYSDESC, SYSOBJECTID, SYSUPTIME, SYSNAME
    ]
    assert message["varbinds"][0]["value"] == "Linux router 5.4.0"
    assert message["varbinds"][1]["value"] == "1.3.6.1.4.1.9.1.1"
    assert message["varbinds"][2]["value"] == 12345678
    assert message["varbinds"][2]["value_type"] == "timeticks"
    assert message["varbinds"][3]["value"] == "router-01"


def test_parse_snmp_message_error_status() -> None:
    data = _build_get_response(error_status=2)  # noSuchName
    message = _parse_snmp_message(data)
    assert message["error_status"] == 2
    assert message["varbinds"] == []


def test_parse_snmp_message_truncated_raises() -> None:
    with pytest.raises(ValueError):
        _parse_snmp_message(b"\x30\x05\x02\x01\x01")


def test_parse_snmp_message_wrong_top_level_tag_raises() -> None:
    with pytest.raises(ValueError):
        _parse_snmp_message(b"\x04\x03abc")


def test_parse_snmp_message_trailing_data_raises() -> None:
    data = _build_get_response() + b"\x00"
    with pytest.raises(ValueError):
        _parse_snmp_message(data)


def test_parse_snmp_message_nosuchobject_exception_varbind() -> None:
    # varbind with noSuchObject exception value (0x81 0x00)
    vb = _encode_tlv(TAG_SEQUENCE, _encode_oid(SYSDESC) + b"\x81\x00")
    pdu = _encode_tlv(
        TAG_GET_RESPONSE,
        _encode_integer(1)
        + _encode_integer(0)
        + _encode_integer(0)
        + _encode_tlv(TAG_SEQUENCE, vb),
    )
    data = _encode_tlv(
        TAG_SEQUENCE, _encode_integer(1) + _encode_octet_string("public") + pdu
    )
    message = _parse_snmp_message(data)
    assert message["varbinds"][0]["value"] is None
    assert "noSuchObject" in message["varbinds"][0]["value_type"]


def test_parse_snmp_message_empty_community() -> None:
    data = _build_get_response(community="")
    message = _parse_snmp_message(data)
    assert message["community"] == ""


# ---------------------------------------------------------------------------
# _send_recv
# ---------------------------------------------------------------------------


def test_send_recv_with_connector_returns_data() -> None:
    def connector(host, port, request, timeout):
        return b"response", None

    data, err = _send_recv("h", 161, b"req", 1.0, connector=connector)
    assert data == b"response"
    assert err is None


def test_send_recv_with_connector_returns_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    data, err = _send_recv("h", 161, b"req", 1.0, connector=connector)
    assert data is None
    assert err == "timeout"


def test_send_recv_connector_receives_arguments() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured.update(host=host, port=port, request=request, timeout=timeout)
        return None, "timeout"

    _send_recv("host.example.com", 1161, b"req-bytes", 2.5, connector=connector)
    assert captured == {
        "host": "host.example.com",
        "port": 1161,
        "request": b"req-bytes",
        "timeout": 2.5,
    }


# ---------------------------------------------------------------------------
# _probe_community
# ---------------------------------------------------------------------------


def test_probe_community_valid_v2c() -> None:
    def connector(host, port, request, timeout):
        return _build_get_response(varbinds=_system_varbinds()), None

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is True
    assert entry["version"] == "v2c"
    assert entry["error"] is None
    assert entry["sysDescr"] == "Linux router 5.4.0"
    assert entry["sysUpTime"] == 123456780  # ticks * 10


def test_probe_community_v2c_timeout_then_v1_success() -> None:
    calls = []

    def connector(host, port, request, timeout):
        calls.append(request)
        message = _parse_snmp_message(request)
        if message["version"] == 1:
            return None, "timeout"  # v2c times out
        return _build_get_response(
            version=0, community="public", varbinds=_system_varbinds()
        ), None

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is True
    assert entry["version"] == "v1"
    assert len(calls) == 2  # v2c then v1


def test_probe_community_all_timeouts() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is False
    assert entry["version"] is None
    assert entry["error"] == "v1 request failed: timeout"


def test_probe_community_connection_refused() -> None:
    def connector(host, port, request, timeout):
        return None, "[Errno 111] Connection refused"

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is False
    assert "Connection refused" in entry["error"]


def test_probe_community_error_status() -> None:
    def connector(host, port, request, timeout):
        return _build_get_response(error_status=2), None  # noSuchName

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is False
    assert "error status 2" in entry["error"]
    assert ERROR_STATUS_NAMES[2] in entry["error"]


def test_probe_community_parse_failure() -> None:
    def connector(host, port, request, timeout):
        return b"\x30\x02\x00", None  # malformed

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is False
    assert "response parse failed" in entry["error"]


def test_probe_community_unexpected_pdu() -> None:
    # A get-request PDU (not a get-response) is rejected.
    request_pdu = _build_get_request(1, "public", [SYSDESC])

    def connector(host, port, request, timeout):
        return request_pdu, None

    entry = _probe_community("h", 161, "public", 1.0, connector)
    assert entry["valid"] is False
    assert "unexpected PDU" in entry["error"]


# ---------------------------------------------------------------------------
# run_snmp
# ---------------------------------------------------------------------------


def test_run_snmp_full_interaction() -> None:
    def connector(host, port, request, timeout):
        message = _parse_snmp_message(request)
        if message["community"] == "public":
            return _build_get_response(
                version=message["version"],
                community="public",
                varbinds=_system_varbinds(),
            ), None
        return None, "timeout"

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    assert results["target"] == "snmp.example.com"
    assert results["host"] == "snmp.example.com"
    assert results["port"] == DEFAULT_PORT
    assert results["snmp_version"] == "v2c"
    assert results["valid_communities"] == ["public"]
    assert results["sysDescr"] == "Linux router 5.4.0"
    assert results["sysObjectID"] == "1.3.6.1.4.1.9.1.1"
    assert results["sysUpTime"] == 123456780
    assert results["sysName"] == "router-01"
    assert results["error"] is None
    # Every default community was probed.
    assert [entry["community"] for entry in results["communities"]] == list(
        DEFAULT_COMMUNITIES
    )


def test_run_snmp_multiple_valid_communities() -> None:
    def connector(host, port, request, timeout):
        message = _parse_snmp_message(request)
        if message["community"] in ("public", "private"):
            return _build_get_response(
                version=message["version"],
                community=message["community"],
                varbinds=_system_varbinds(),
            ), None
        return None, "timeout"

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    assert results["valid_communities"] == ["public", "private"]
    # Values come from the first valid community.
    assert results["sysDescr"] == "Linux router 5.4.0"


def test_run_snmp_custom_communities() -> None:
    probed = []

    def connector(host, port, request, timeout):
        message = _parse_snmp_message(request)
        probed.append(message["community"])
        return _build_get_response(
            version=message["version"],
            community=message["community"],
        ), None

    results = run_snmp(
        "snmp.example.com",
        timeout=1.0,
        communities=["s3cr3t"],
        connector=connector,
    )
    assert probed == ["s3cr3t"]
    assert results["valid_communities"] == ["s3cr3t"]


def test_run_snmp_empty_community_valid() -> None:
    def connector(host, port, request, timeout):
        message = _parse_snmp_message(request)
        if message["community"] == "":
            return _build_get_response(
                version=message["version"],
                community="",
                varbinds=_system_varbinds(),
            ), None
        return None, "timeout"

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    assert results["valid_communities"] == [""]
    assert results["sysDescr"] == "Linux router 5.4.0"


def test_run_snmp_all_timeouts_sets_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    assert results["valid_communities"] == []
    assert results["snmp_version"] is None
    assert results["sysDescr"] is None
    assert results["error"] == "v1 request failed: timeout"


def test_run_snmp_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["port"] = port
        return None, "timeout"

    results = run_snmp(
        "snmp.example.com", port=1161, timeout=1.0, connector=connector
    )
    assert captured["port"] == 1161
    assert results["port"] == 1161


def test_run_snmp_url_target() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured.update(host=host, port=port)
        return None, "timeout"

    results = run_snmp("snmp://snmp.example.com:1161", timeout=1.0, connector=connector)
    assert captured["host"] == "snmp.example.com"
    assert captured["port"] == 1161
    assert results["host"] == "snmp.example.com"
    assert results["port"] == 1161


def test_run_snmp_community_error_does_not_mask_success() -> None:
    def connector(host, port, request, timeout):
        message = _parse_snmp_message(request)
        if message["community"] == "public":
            return None, "timeout"
        if message["community"] == "private":
            return _build_get_response(
                version=message["version"],
                community="private",
                varbinds=_system_varbinds(),
            ), None
        return None, "timeout"

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    assert results["valid_communities"] == ["private"]
    # A valid community means no overall error even though "public" failed.
    assert results["error"] is None


def test_run_snmp_response_with_mismatched_community_still_valid() -> None:
    def connector(host, port, request, timeout):
        return _build_get_response(
            community="other", varbinds=_system_varbinds()
        ), None

    results = run_snmp("snmp.example.com", timeout=1.0, connector=connector)
    # Every default community is probed and accepted (the response
    # community string does not have to match the requested one).
    assert results["valid_communities"] == list(DEFAULT_COMMUNITIES)
    assert results["sysDescr"] == "Linux router 5.4.0"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _full_results() -> dict:
    return {
        "target": "snmp.example.com",
        "host": "snmp.example.com",
        "port": 161,
        "snmp_version": "v2c",
        "communities": [
            {
                "community": "public",
                "valid": True,
                "version": "v2c",
                "error": None,
                "sysDescr": "Linux router 5.4.0",
                "sysObjectID": "1.3.6.1.4.1.9.1.1",
                "sysUpTime": 123456780,
                "sysName": "router-01",
            },
            {
                "community": "private",
                "valid": False,
                "version": None,
                "error": "v2c request failed: timeout",
            },
        ],
        "valid_communities": ["public"],
        "sysDescr": "Linux router 5.4.0",
        "sysObjectID": "1.3.6.1.4.1.9.1.1",
        "sysUpTime": 123456780,
        "sysName": "router-01",
        "error": None,
    }


def test_format_snmp_report_json() -> None:
    parsed = json.loads(format_snmp_report_json(_full_results()))
    assert parsed["host"] == "snmp.example.com"
    assert parsed["valid_communities"] == ["public"]
    assert parsed["sysDescr"] == "Linux router 5.4.0"
    assert parsed["communities"][0]["valid"] is True


def test_format_snmp_report_json_error_case() -> None:
    results = _full_results()
    results["error"] = "v2c request failed: timeout"
    results["valid_communities"] = []
    parsed = json.loads(format_snmp_report_json(results))
    assert parsed["error"] == "v2c request failed: timeout"


def test_format_snmp_report_markdown_full() -> None:
    output = format_snmp_report_markdown(_full_results())
    assert "# ethscan SNMP Report" in output
    assert "**Target:** snmp.example.com" in output
    assert "**Port:** 161" in output
    assert "**SNMP Version:** v2c" in output
    assert "## Community Probes" in output
    assert "| public | YES |" in output
    assert "| private | NO |" in output
    assert "## System Information" in output
    assert "**sysDescr:** Linux router 5.4.0" in output
    assert "**sysObjectID:** 1.3.6.1.4.1.9.1.1" in output
    assert "**sysUpTime:** 123456780 ms" in output
    assert "**sysName:** router-01" in output
    assert "## Assessment" in output
    assert "**Valid communities:** public" in output
    assert "Misconfiguration" in output


def test_format_snmp_report_markdown_no_valid_communities() -> None:
    results = _full_results()
    results["communities"] = [
        {"community": "public", "valid": False, "version": None, "error": "v2c request failed: timeout"}
    ]
    results["valid_communities"] = []
    results["sysDescr"] = None
    results["sysObjectID"] = None
    results["sysUpTime"] = None
    results["sysName"] = None
    output = format_snmp_report_markdown(results)
    assert "No valid community strings found." in output
    assert "**sysDescr:** N/A" in output


def test_format_snmp_report_markdown_empty_community_label() -> None:
    results = _full_results()
    results["communities"] = [
        {"community": "", "valid": True, "version": "v2c", "error": None}
    ]
    results["valid_communities"] = [""]
    output = format_snmp_report_markdown(results)
    assert "| (empty) | YES |" in output
    assert "**Valid communities:** (empty)" in output


def test_format_snmp_report_markdown_pipe_escaping() -> None:
    results = _full_results()
    results["sysDescr"] = "a|b|c"
    results["sysName"] = "name|1"
    output = format_snmp_report_markdown(results)
    assert "a\\|b\\|c" in output
    assert "name\\|1" in output


def test_format_snmp_report_markdown_error() -> None:
    results = _full_results()
    results["error"] = "v2c request failed: timeout"
    output = format_snmp_report_markdown(results)
    assert "**Error:** v2c request failed: timeout" in output


def test_format_snmp_report_csv() -> None:
    output = format_snmp_report_csv(_full_results())
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == [
        "target", "host", "port", "snmp_version",
        "sys_descr", "sys_object_id", "sys_up_time_ms", "sys_name", "error",
        "record_type", "community", "community_valid",
        "community_version", "community_error",
    ]
    # Summary row: target-level fields populated, community fields empty.
    summary = rows[1]
    assert summary[9] == "summary"
    assert summary[0] == "snmp.example.com"
    assert summary[1] == "snmp.example.com"
    assert summary[2] == "161"
    assert summary[3] == "v2c"
    assert summary[4] == "Linux router 5.4.0"
    assert summary[5] == "1.3.6.1.4.1.9.1.1"
    assert summary[6] == "123456780"
    assert summary[7] == "router-01"
    assert summary[8] == ""  # no top-level error
    assert summary[10:] == ["", "", "", ""]

    # One community row per probed community (previously collapsed).
    community_rows = [r for r in rows[1:] if r[9] == "community"]
    assert [r[10] for r in community_rows] == ["public", "private"]
    public_row = community_rows[0]
    assert public_row[9] == "community"
    assert public_row[10] == "public"
    assert public_row[11] == "true"
    assert public_row[12] == "v2c"
    assert public_row[13] == ""
    private_row = community_rows[1]
    assert private_row[10] == "private"
    assert private_row[11] == "false"
    assert private_row[12] == ""  # version not negotiated
    assert private_row[13] == "v2c request failed: timeout"
    # Target context is repeated on every community row.
    assert all(r[0] == "snmp.example.com" and r[2] == "161" and r[3] == "v2c" for r in community_rows)
    assert all(r[4:9] == ["", "", "", "", ""] for r in community_rows)


def test_format_snmp_report_csv_no_communities() -> None:
    results = _full_results()
    results["communities"] = []
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    # Header + a single summary row; no community rows.
    assert len(rows) == 2
    assert rows[1][9] == "summary"
    assert not any(r[9] == "community" for r in rows[1:])


def test_format_snmp_report_csv_multiple_communities() -> None:
    results = _full_results()
    results["communities"] = [
        {"community": "public", "valid": True, "version": "v2c", "error": None},
        {"community": "private", "valid": False, "version": None,
         "error": "v2c request failed: timeout"},
        {"community": "", "valid": False, "version": None,
         "error": "v1 request failed: connection refused"},
    ]
    results["valid_communities"] = ["public"]
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    community_rows = [r for r in rows[1:] if r[9] == "community"]
    assert len(community_rows) == 3
    assert [r[10] for r in community_rows] == ["public", "private", ""]
    assert [r[11] for r in community_rows] == ["true", "false", "false"]
    assert [r[12] for r in community_rows] == ["v2c", "", ""]
    assert community_rows[2][10] == ""  # empty community string preserved as its own row
    assert community_rows[2][13] == "v1 request failed: connection refused"


def test_format_snmp_report_csv_one_row_per_community() -> None:
    results = _full_results()
    results["communities"] = [
        {"community": "public", "valid": True, "version": "v2c", "error": None},
        {"community": "private", "valid": True, "version": "v1", "error": None},
    ]
    results["valid_communities"] = ["public", "private"]
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    community_rows = [r for r in rows[1:] if r[9] == "community"]
    assert len(community_rows) == 2
    assert [r[10] for r in community_rows] == ["public", "private"]
    assert [r[11] for r in community_rows] == ["true", "true"]
    assert [r[12] for r in community_rows] == ["v2c", "v1"]


def test_format_snmp_report_csv_preserves_per_community_errors() -> None:
    results = _full_results()
    results["valid_communities"] = []
    results["error"] = "all probes timed out"
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    # Top-level error lives on the summary row (not aggregated into a cell).
    assert rows[1][8] == "all probes timed out"
    community_rows = [r for r in rows[1:] if r[9] == "community"]
    assert len(community_rows) == 2
    assert community_rows[0][10] == "public"
    assert community_rows[0][13] == ""
    assert community_rows[1][10] == "private"
    assert community_rows[1][13] == "v2c request failed: timeout"


def test_format_snmp_report_csv_commas_in_values() -> None:
    results = _full_results()
    results["sysDescr"] = "Linux, version 5.4.0"
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][4] == "Linux, version 5.4.0"


def test_format_snmp_report_csv_no_uptime() -> None:
    results = _full_results()
    results["sysUpTime"] = None
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][6] == ""
