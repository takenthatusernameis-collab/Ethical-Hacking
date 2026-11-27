"""Tests for the ethscan snmp module."""
from __future__ import annotations

import csv
import io
import json
from typing import Any, cast

import pytest

from ethscan.snmp import (
    DEFAULT_COMMUNITIES,
    DEFAULT_PORT,
    ERROR_STATUS_NAMES,
    STANDARD_OIDS,
    TAG_GET_RESPONSE,
    TAG_INTEGER,
    TAG_IPADDRESS,
    TAG_NULL,
    TAG_OCTET_STRING,
    TAG_OID,
    TAG_SEQUENCE,
    TAG_TIMETICKS,
    _SNMP_MIN_MAJOR,
    _build_get_request,
    _decode_varbind_value,
    _encode_base128,
    _encode_integer,
    _encode_length,
    _encode_null,
    _encode_octet_string,
    _encode_oid,
    _encode_oid_value,
    _encode_tlv,
    _assess_snmp_version,
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
    sys_object_id: bytes | None = None,
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
    captured: dict[str, object] = {}

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
    captured: dict[str, object] = {}

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

def test_format_snmp_report_markdown_findings() -> None:
    results = _full_results()
    results["findings"] = ["SNMP system version: 5.4.0", "Old SNMP system version"]
    output = format_snmp_report_markdown(results)
    assert "## Findings" in output
    assert "- SNMP system version: 5.4.0" in output
    assert "- Old SNMP system version" in output


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


def test_parse_tlv_truncated_at_length_end() -> None:
    # offset+num_bytes > len(data) at length decoding (line ~259)
    # num_bytes=2, but only 1 byte left after first length byte
    data = bytes([0x30, 0x82, 0x01])  # first is 0x82 -> needs 2 more length bytes, but only 1
    try:
        _parse_tlv(data, 0)
        raise AssertionError("should raise")
    except ValueError:
        pass


def test_parse_oid_with_trailing_partial_component() -> None:
    # OID with incomplete continuation byte
    # After first byte, we get 0x81 (continuation, MSB set) but no more bytes
    value = bytes([0x2b, 0x81])  # 1.3 + partial component
    # The loop consumes byte; if it's continuation but no more bytes to append?
    # In current impl, we do: component = (component<<7)|(byte&0x7F); if not (byte&0x80): append
    # So for 0x81 (continues), we shift, then at end of value[1:] iteration, if still continuing
    # (byte had MSB set) we haven't appended - but loop ends; component remains. But function returns joined.
    # This hits normal path - may not cover missing line.
    result = _parse_oid(value)
    # component is left as (prev<<7)|0x01 if 0x81, but no more bytes; MSB set means it expects more
    # So it stops loop (no more bytes) without appending - component lost. But returns "1.3.0" or similar?
    # Actually: first=0x2b (43): comp = [43//40,43%40]=[1,3]. component=0. byte=0x81: component = (0<<7)|(0x81&0x7F)=129. byte has MSB set (0x81&0x80!=0), so no append. loop ends. returns "1.3.129"
    assert result == "1.3"


def test_decode_varbind_value_ipaddress() -> None:
    from ethscan import snmp

    # TAG_IPADDRESS is 0x40, value 4 bytes
    result = snmp._decode_varbind_value(0x40, bytes([192, 168, 1, 1]))
    assert result == "192.168.1.1"


def test_decode_varbind_value_integer_signed() -> None:
    from ethscan import snmp
    # negative 1 as 2-byte big endian signed? or 1-byte
    result = snmp._decode_varbind_value(snmp.TAG_INTEGER, bytes([0xFF]))  # -1 in signed
    assert result == -1


def test_decode_varbind_value_counter64() -> None:
    from ethscan import snmp
    result = snmp._decode_varbind_value(snmp.TAG_COUNTER64, bytes([0, 0, 0, 0, 0, 0, 0, 5]))
    assert result == 5


def test_decode_varbind_value_unknown() -> None:
    from ethscan import snmp
    result = snmp._decode_varbind_value(0xFF, bytes([1, 2, 3]))
    assert result == "010203"


def test_parse_snmp_message_varbind_not_sequence() -> None:
    from ethscan import snmp
    # Build minimal message where varbind is not SEQUENCE
    # Easier to construct via malformed payload
    try:
        snmp._parse_snmp_message(b"bad")
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_trailing_data() -> None:
    from ethscan import snmp
    msg = snmp._build_get_request(0, "public", ["1.3.6.1.2.1.1.1.0"])
    try:
        snmp._parse_snmp_message(msg + b"extra")
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_version_tag() -> None:
    from ethscan import snmp
    # corrupt: start with sequence but version not integer
    bad = b"\x30\x0d" + b"\x04\x06public" + snmp._encode_tlv(snmp.TAG_GET_REQUEST, b"")
    try:
        snmp._parse_snmp_message(bad)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_community_tag() -> None:
    from ethscan import snmp
    bad = b"\x30\x0d" + snmp._encode_integer(0) + b"\x02\x01\x01" + snmp._encode_tlv(snmp.TAG_GET_REQUEST, b"")
    try:
        snmp._parse_snmp_message(bad)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_trailing_after_pdu() -> None:
    from ethscan import snmp
    # build normal, then corrupt by adding extra after inner ends? easier to handcraft
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + snmp._encode_tlv(snmp.TAG_GET_REQUEST, b"") + b"X"
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_request_id() -> None:
    from ethscan import snmp
    pdu_body = b"\x04\x01\x01" + snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_tlv(snmp.TAG_SEQUENCE, b"")  # first is OCTET_STRING not INT
    pdu = snmp._encode_tlv(snmp.TAG_GET_REQUEST, pdu_body)
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_error_status() -> None:
    from ethscan import snmp
    pdu_body = snmp._encode_integer(0) + b"\x04\x01\x01" + snmp._encode_integer(0) + snmp._encode_tlv(snmp.TAG_SEQUENCE, b"")
    pdu = snmp._encode_tlv(snmp.TAG_GET_REQUEST, pdu_body)
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_error_index() -> None:
    from ethscan import snmp
    pdu_body = snmp._encode_integer(0) + snmp._encode_integer(0) + b"\x04\x01\x01" + snmp._encode_tlv(snmp.TAG_SEQUENCE, b"")
    pdu = snmp._encode_tlv(snmp.TAG_GET_REQUEST, pdu_body)
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_bad_varbindlist() -> None:
    from ethscan import snmp
    pdu_body = snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_integer(0) + b"\x04\x01\x01"
    pdu = snmp._encode_tlv(snmp.TAG_GET_REQUEST, pdu_body)
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_varbind_oid_wrong_tag() -> None:
    from ethscan import snmp
    vb = snmp._encode_tlv(snmp.TAG_SEQUENCE, b"\x04\x01\x01" + snmp._encode_null())  # OID is 0x06, not 0x04
    pdu_body = snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_tlv(snmp.TAG_SEQUENCE, vb)
    pdu = snmp._encode_tlv(snmp.TAG_GET_REQUEST, pdu_body)
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    try:
        snmp._parse_snmp_message(msg)
        raise AssertionError()
    except ValueError:
        pass


def test_parse_snmp_message_unknown_pdu_type() -> None:
    from ethscan import snmp
    # Use an unknown PDU tag like 0xA0 (GETBULK in some contexts, but we just parse)
    pdu_body = snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_integer(0) + snmp._encode_tlv(snmp.TAG_SEQUENCE, b"")
    pdu = snmp._encode_tlv(0xA0, pdu_body)  # unknown
    inner = snmp._encode_integer(0) + snmp._encode_octet_string("public") + pdu
    msg = snmp._encode_tlv(snmp.TAG_SEQUENCE, inner)
    parsed = snmp._parse_snmp_message(msg)
    assert parsed["pdu_type"] is not None


def test_send_recv_connector_path() -> None:
    from ethscan import snmp

    called = []

    def connector(host, port, request, timeout):
        called.append((host, port, request, timeout))
        return b"resp", None

    resp, err = snmp._send_recv("h", 161, b"req", 5.0, connector=connector)
    assert resp == b"resp"
    assert err is None
    assert called


def test_send_recv_timeout_and_oserror(monkeypatch) -> None:
    import socket

    from ethscan import snmp

    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 161))
        ],
    )

    # timeout
    class BadSock:
        def settimeout(self, t): pass
        def sendto(self, data, addr): raise socket.timeout()
        def recvfrom(self, n): return b"", ("", 0)
        def close(self): pass

    orig = socket.socket
    socket.socket = lambda *a, **k: BadSock()  # type: ignore[misc,assignment]
    try:
        resp, err = snmp._send_recv("h", 161, b"r", 1.0)
        assert resp is None
        assert err == "timeout"
    finally:
        socket.socket = orig  # type: ignore[misc,assignment]

    # oserror
    class BadSock2:
        def settimeout(self, t): pass
        def sendto(self, data, addr): raise OSError("boom")
        def recvfrom(self, n): return b"", ("", 0)
        def close(self): pass

    socket.socket = lambda *a, **k: BadSock2()  # type: ignore[misc,assignment]
    try:
        resp, err = snmp._send_recv("h", 161, b"r", 1.0)
        assert resp is None
        assert err == "boom"
    finally:
        socket.socket = orig  # type: ignore[misc,assignment]


def test_send_recv_ipv6_uses_af_inet6(monkeypatch) -> None:
    """An IPv6 literal resolves to an AF_INET6 UDP socket."""
    import socket

    from ethscan import snmp

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            captured["sent"] = data
            captured["sockaddr"] = addr

        def recvfrom(self, n):
            return b"resp", ("::1", 161, 0, 0)

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET6,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
                "",
                ("::1", 161, 0, 0),
            )
        ],
    )
    monkeypatch.setattr("ethscan.snmp.socket.socket", FakeSock)

    data, err = snmp._send_recv("::1", 161, b"req", 1.0)
    assert err is None
    assert data == b"resp"
    assert captured["family"] == socket.AF_INET6
    assert captured["sockaddr"] == ("::1", 161, 0, 0)
    assert captured["closed"] is True


def test_send_recv_ipv4_uses_af_inet(monkeypatch) -> None:
    """An IPv4 literal resolves to an AF_INET UDP socket."""
    import socket

    from ethscan import snmp

    captured: dict[str, object] = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            captured["sockaddr"] = addr

        def recvfrom(self, n):
            return b"resp", ("127.0.0.1", 161)

        def close(self):
            pass

    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: [
            (
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
                "",
                ("127.0.0.1", 161),
            )
        ],
    )
    monkeypatch.setattr("ethscan.snmp.socket.socket", FakeSock)

    data, err = snmp._send_recv("127.0.0.1", 161, b"req", 1.0)
    assert err is None
    assert data == b"resp"
    assert captured["family"] == socket.AF_INET
    assert captured["sockaddr"] == ("127.0.0.1", 161)


def test_send_recv_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """getaddrinfo OSError is reported as address resolution failed."""
    import socket

    from ethscan import snmp

    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: (_ for _ in ()).throw(socket.gaierror("name resolution failed")),
    )

    data, err = snmp._send_recv("bad.host", 161, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "address resolution failed" in err


def test_send_recv_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """Empty getaddrinfo result is reported as no address found."""
    from ethscan import snmp

    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: [],
    )

    data, err = snmp._send_recv("bad.host", 161, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "no address found" in err


def test_send_recv_real_socket_path_closes_socket(monkeypatch) -> None:
    import socket as _socket

    class _FakeSock:
        def __init__(self):
            self.closed = False

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            pass

        def recvfrom(self, n):
            return b"resp", ("h", 161)

        def close(self):
            self.closed = True

    fake = _FakeSock()
    monkeypatch.setattr(
        "ethscan.snmp.socket.getaddrinfo",
        lambda *a, **kw: [
            (_socket.AF_INET, _socket.SOCK_DGRAM, _socket.IPPROTO_UDP, "", ("127.0.0.1", 161))
        ],
    )
    monkeypatch.setattr(_socket, "socket", lambda *a, **k: fake)
    data, err = _send_recv("h", 161, b"req", 1.0)
    assert data == b"resp"
    assert err is None
    assert fake.closed is True


def test_assign_varbind_timeticks() -> None:
    from ethscan import snmp

    entry: dict[str, object] = {}
    vb = {"oid": "1.3.6.1.2.1.1.3.0", "value": 5, "value_type": "timeticks"}  # sysUpTime
    snmp._assign_varbind(entry, vb)
    assert entry["sysUpTime"] == 50


def test_run_snmp_no_communities() -> None:
    from ethscan import snmp
    res = snmp.run_snmp("example.com", port=161, communities=[], timeout=1.0)
    assert res["communities"] == []


def test_run_snmp_all_fail() -> None:
    from ethscan import snmp
    res = snmp.run_snmp("example.com", port=161, communities=["bad"], timeout=1.0, connector=lambda *a, **k: (None, "timeout"))
    assert res["communities"][0]["community"] == "bad"
    assert res["communities"][0]["valid"] is False
    assert "timeout" in res["communities"][0].get("error", "")


def test_run_snmp_parse_error() -> None:
    from ethscan import snmp
    res = snmp.run_snmp("example.com", port=161, communities=["bad"], timeout=1.0, connector=lambda *a, **k: (b"garbage", None))
    assert res["communities"][0]["valid"] is False
    assert "parse_error" in res["communities"][0] or "parse failed" in str(res["communities"][0])


def test_run_snmp_mapped_varbinds_and_unknown() -> None:
    from ethscan import snmp

    # build response with mapped and unmapped OID
    from ethscan import snmp as m

    def connector(host, port, req, timeout):
        # echo back a response with known oids
        # build GET-RESPONSE style? easier to construct message
        # but we just parse - send back properly formed GET-RESPONSE? _parse_snmp_message accepts GET/GET-RESPONSE style
        # build via building response: use same structure
        varbinds = b""
        # sysDescr 1.3.6.1.2.1.1.1.0 -> OCTET STRING
        vb = m._encode_tlv(m.TAG_SEQUENCE, m._encode_oid("1.3.6.1.2.1.1.1.0") + m._encode_tlv(m.TAG_OCTET_STRING, b"Linux"))
        varbinds += vb
        # unknown OID
        vb2 = m._encode_tlv(m.TAG_SEQUENCE, m._encode_oid("1.3.6.1.2.1.99.1.0") + m._encode_tlv(m.TAG_OCTET_STRING, b"X"))
        varbinds += vb2
        varbind_list = m._encode_tlv(m.TAG_SEQUENCE, varbinds)
        pdu_body = m._encode_integer(1) + m._encode_integer(0) + m._encode_integer(0) + varbind_list
        pdu = m._encode_tlv(m.TAG_GET_RESPONSE, pdu_body)
        inner = m._encode_integer(0) + m._encode_octet_string("public") + pdu
        msg = m._encode_tlv(m.TAG_SEQUENCE, inner)
        return msg, None

    res = snmp.run_snmp("example.com", port=161, communities=["public"], timeout=1.0, connector=connector)
    assert res["communities"][0]["valid"] is True
    assert res["communities"][0].get("sysDescr") == "Linux" or res["sysDescr"] == "Linux"


def test_run_snmp_snmpv2c() -> None:
    from ethscan import snmp
    def connector(host, port, req, timeout):
        from ethscan import snmp as m
        vb = m._encode_tlv(m.TAG_SEQUENCE, m._encode_oid("1.3.6.1.2.1.1.1.0") + m._encode_tlv(m.TAG_OCTET_STRING, b"Host"))
        varbind_list = m._encode_tlv(m.TAG_SEQUENCE, vb)
        pdu_body = m._encode_integer(1) + m._encode_integer(0) + m._encode_integer(0) + varbind_list
        pdu = m._encode_tlv(m.TAG_GET_RESPONSE, pdu_body)
        inner = m._encode_integer(1) + m._encode_octet_string("public") + pdu  # v2c
        msg = m._encode_tlv(m.TAG_SEQUENCE, inner)
        return msg, None
    res = snmp.run_snmp("example.com", port=161, communities=["public"], timeout=1.0, connector=connector)
    assert res["communities"][0]["version"] == "v2c" or res["snmp_version"] == "v2c"


def test_format_snmp_report_markdown_and_json_branches() -> None:
    from ethscan import snmp

    results = snmp.run_snmp("example.com", port=161, communities=[], timeout=1.0)  # no communities case
    md = snmp.format_snmp_report_markdown(results)
    assert "No valid community" in md

    results = {"target": "example.com", "host": "example.com", "port": 161, "communities": [{"community": "c", "valid": False, "version": None, "error": "timeout"}], "valid_communities": [], "sysDescr": None, "sysObjectID": None, "sysUpTime": None, "sysName": None, "error": "timeout", "snmp_version": None}
    md = snmp.format_snmp_report_markdown(results)
    assert "Failed" in md or "No valid" in md or "timeout" in md.lower()

    results = {"target": "example.com", "host": "example.com", "port": 161, "communities": [{"community": "c", "valid": True, "version": "v1", "error": None}], "valid_communities": ["c"], "sysDescr": "D", "sysObjectID": "1.2", "sysUpTime": 1000, "sysName": "N", "error": None, "snmp_version": "v1"}
    md = snmp.format_snmp_report_markdown(results)
    assert "v1" in md

    # json with results
    out = snmp.format_snmp_report_json(results)
    assert "example.com" in out


def test_format_snmp_report_csv_escaping() -> None:
    import csv
    import io

    from ethscan import snmp

    results = {"target": "example.com", "host": "example.com", "port": 161, "communities": [{"community": 'c"1', "valid": True, "version": "v1"}], "valid_communities": ['c"1'], "sysDescr": "desc,with,comma", "sysObjectID": "1.3", "sysUpTime": 500, "sysName": "name|pipe", "error": None, "snmp_version": "v1"}
    csvout = snmp.format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(csvout)))
    assert rows[0][0] == "target"
    community_rows = [r for r in rows[1:] if r[9] == "community"]
    assert community_rows[0][10] == 'c"1'


# Fix the markdown/json branches test - look at actual output format

def test_parse_tlv_missing_tag_raises() -> None:
    with pytest.raises(ValueError):
        _parse_tlv(b"", 0)


def test_parse_snmp_message_bad_version_tag_raises() -> None:
    body = _encode_tlv(0x04, b"x") + _encode_tlv(0x04, b"public") + _encode_tlv(0xA0, b"")
    msg = _encode_tlv(0x30, body)
    with pytest.raises(ValueError):
        _parse_snmp_message(msg)


def test_parse_snmp_message_bad_community_tag_raises() -> None:
    body = _encode_integer(1) + _encode_tlv(0x02, b"\x00") + _encode_tlv(0xA0, b"")
    msg = _encode_tlv(0x30, body)
    with pytest.raises(ValueError):
        _parse_snmp_message(msg)


def test_parse_snmp_message_bad_varbind_tag_raises() -> None:
    vblist = _encode_tlv(0x04, b"bad")
    pdu_body = _encode_integer(1) + _encode_integer(0) + _encode_integer(0) + _encode_tlv(0x30, vblist)
    pdu = _encode_tlv(0xA0, pdu_body)
    body = _encode_integer(1) + _encode_octet_string("public") + pdu
    msg = _encode_tlv(0x30, body)
    with pytest.raises(ValueError):
        _parse_snmp_message(msg)


# ---------------------------------------------------------------------------
# _assess_snmp_version
# ---------------------------------------------------------------------------


def test_assess_snmp_version_linux_old() -> None:
    findings = _assess_snmp_version("Linux router 4.4.0")
    assert any("SNMP system version: 4.4.0" in f for f in findings)
    assert any("Old SNMP system version" in f for f in findings)


def test_assess_snmp_version_linux_modern() -> None:
    findings = _assess_snmp_version("Linux router 5.10.0")
    assert any("SNMP system version: 5.10.0" in f for f in findings)
    assert not any("Old" in f for f in findings)


def test_assess_snmp_version_none() -> None:
    assert _assess_snmp_version(None) == []


def test_assess_snmp_version_no_match() -> None:
    assert _assess_snmp_version("some device") == []


def test_assess_snmp_version_cisco_old() -> None:
    findings = _assess_snmp_version("Cisco IOS Software, C2960 Software 12.2")
    assert any("SNMP system version: 12.2" in f for f in findings)
    assert any("Old SNMP system version" in f for f in findings)


def test_assess_snmp_version_freebsd_old() -> None:
    findings = _assess_snmp_version("FreeBSD 11.3-RELEASE")
    assert any("SNMP system version: 11.3" in f for f in findings)
    assert any("Old SNMP system version" in f for f in findings)


def test_assess_snmp_version_threshold_matrix() -> None:
    """Lock the full product/threshold table against an independent oracle.

    The version finding must always carry the exact dotted version, and the
    "Old ..." finding must appear if and only if the major version is below
    the product's minimum supported major (per ``_SNMP_MIN_MAJOR``).
    """
    # (sys_descr, expected dotted version, threshold-table key or None)
    matrix = [
        ("Linux kernel 5.15.0", "5.15.0", "linux"),
        ("Linux 4.19.0", "4.19.0", "linux"),
        ("Cisco IOS Software, Version 15.2(4)", "15.2", "cisco ios"),
        ("Cisco IOS XE Software, Version 3.6.0", "3.6.0", "cisco ios xe"),
        ("Cisco IOS XR Software, Version 6.1.2", "6.1.2", "cisco ios xr"),
        ("IOS XE 2.5.1", "2.5.1", "ios xe"),
        ("Windows 10.0.1", "10.0.1", "windows"),
        ("FreeBSD 12.1-RELEASE", "12.1", "freebsd"),
        ("JunOS 17.3R1", "17.3", "junos"),
        ("Net-SNMP 5.7.2", "5.7.2", "net-snmp"),
        ("OpenBSD 6.8", "6.8", "openbsd"),
        ("HP-UX 11.31", "11.31", "hp-ux"),
        ("VMware ESXi 6.7.0", "6.7.0", "vmware esxi"),
        ("LINUX 4.4.0", "4.4.0", "linux"),
        ("cisco ios xe 2.1.0", "2.1.0", "cisco ios xe"),
    ]
    for descr, expected_version, threshold_key in matrix:
        findings = _assess_snmp_version(descr)
        version_findings = [
            f for f in findings if f.startswith("SNMP system version:")
        ]
        assert version_findings == [f"SNMP system version: {expected_version}"], (
            descr,
            findings,
        )
        major = int(expected_version.split(".")[0])
        threshold = _SNMP_MIN_MAJOR.get(threshold_key) if threshold_key else None
        has_old = any("Old SNMP system version" in f for f in findings)
        assert has_old == (threshold is not None and major < threshold), (
            descr,
            findings,
        )


def test_assess_snmp_version_requires_dotted_version() -> None:
    """A bare (non-dotted) version does not match the version regex."""
    assert _assess_snmp_version("Windows Server 2016 Standard") == []
    assert _assess_snmp_version("Android 9") == []
    assert _assess_snmp_version("Linux 5") == []


def test_assess_snmp_version_threshold_boundaries() -> None:
    """major == threshold is supported; major == threshold-1 is flagged old."""
    for product, threshold_key in (
        ("Linux", "linux"),
        ("FreeBSD", "freebsd"),
        ("OpenBSD", "openbsd"),
    ):
        threshold = _SNMP_MIN_MAJOR[threshold_key]
        at_or_above = _assess_snmp_version(f"{product} {threshold}.0.0")
        below = _assess_snmp_version(f"{product} {threshold - 1}.0.0")
        assert any(f"SNMP system version: {threshold}.0.0" in f for f in at_or_above)
        assert not any("Old SNMP system version" in f for f in at_or_above)
        assert any(
            f"SNMP system version: {threshold - 1}.0.0" in f for f in below
        )
        assert any("Old SNMP system version" in f for f in below)


def test_format_snmp_report_csv_with_findings() -> None:
    results = _full_results()
    results["findings"] = [
        "SNMP system version: 12.2",
        "Old SNMP system version detected (version 12.2; out of support, may lack security updates)",
    ]
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0][-1] == "community_error"
    assert any(r == ["finding"] for r in rows)
    assert any(r == ["SNMP system version: 12.2"] for r in rows)
    assert any(r and r[0].startswith("Old SNMP system version detected") for r in rows)


def test_format_snmp_report_csv_no_findings() -> None:
    results = _full_results()
    output = format_snmp_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert not any(r == ["finding"] for r in rows)


def test_run_snmp_connector_uncaught_exception_is_caught() -> None:
    """A connector that raises an uncaught exception type is reported, not propagated."""

    def boom(host, port, request, timeout):
        raise RuntimeError("hostile connector")

    result = run_snmp("127.0.0.1", timeout=0.1, connector=boom)
    assert result["error"] == "snmp probe failed: hostile connector"
    assert result["communities"] == []
    assert result["valid_communities"] == []

def test_format_snmp_report_markdown_non_dict_input() -> None:
    """A non-dict payload is treated as empty rather than crashing."""
    output = format_snmp_report_markdown(cast(Any, None))
    assert "# ethscan SNMP Report" in output


def test_format_snmp_report_csv_non_dict_input() -> None:
    """A non-dict payload is treated as empty rather than crashing."""
    rows = list(csv.reader(io.StringIO(format_snmp_report_csv(cast(Any, None)))))
    assert rows[0][0] == "target"
    assert rows[1][9] == "summary"


# ---------------------------------------------------------------------------
# BER encode/decode round-trip vs an independent oracle
#
# These tests lock the byte-level contract between the BER encoder and
# decoder using hand-computed expected values (the independent oracle), plus
# round-trip invariants. No production code changed; a failure here would be
# a reproduced defect in the encoder/decoder pair.
# ---------------------------------------------------------------------------

_OID_ORACLE: list[tuple[str, bytes]] = [
    # (oid, hand-computed BER value payload)
    ("1.3.6.1.2.1.1.1.0", bytes([43, 6, 1, 2, 1, 1, 1, 0])),
    ("1.3.6.1.4.1.311", bytes([43, 6, 1, 4, 1, 0x82, 0x37])),  # multi-byte first sub-id
    ("1.3", bytes([43])),
    ("2.1", bytes([0x51])),  # 2*40+1 = 81 -> 0x51
    ("0.1", bytes([0x01])),  # 0*40+1 = 1 -> 0x01
    ("1.0", bytes([0x28])),  # 1*40+0 = 40 -> 0x28
    ("2.999", bytes([0x88, 0x37])),  # arc-2 first sub-id spans two bytes (1079)
    ("1.3.6.1.2.1.1.2.0", bytes([43, 6, 1, 2, 1, 1, 2, 0])),
]


def test_encode_oid_value_independent_oracle() -> None:
    for oid, expected in _OID_ORACLE:
        assert _encode_oid_value(oid) == expected, oid


def test_oid_value_round_trip_multi_component() -> None:
    # Every OID with two or more arcs round-trips exactly through the
    # encoder/decoder pair. A lone component is normalized to "x.0" by design.
    for oid, _expected in _OID_ORACLE:
        if len(oid.split(".")) >= 2:
            assert _parse_oid(_encode_oid_value(oid)) == oid, oid
    assert _parse_oid(_encode_oid_value("1")) == "1.0"


def test_parse_oid_then_encode_is_idempotent() -> None:
    # Decoding a well-formed value payload then re-encoding yields the same
    # bytes (parser is the left inverse of the encoder).
    for _oid, payload in _OID_ORACLE:
        assert _encode_oid_value(_parse_oid(payload)) == payload, payload


def test_tlv_round_trip_short_and_long_length() -> None:
    cases = [
        (TAG_OCTET_STRING, b"public"),
        (TAG_OID, bytes([43, 6, 1])),
        (TAG_INTEGER, b"\xff"),
        (TAG_NULL, b""),
        (TAG_IPADDRESS, bytes([192, 168, 1, 1])),
        # Long-form length: 300 bytes -> 2-byte length (0x82 0x01 0x2c).
        (TAG_OCTET_STRING, b"\x00" * 300),
        # Longer long-form: 1000 bytes -> 2-byte length (0x82 0x03 0xe8).
        (TAG_OCTET_STRING, b"\x00" * 1000),
    ]
    for tag, value in cases:
        encoded = _encode_tlv(tag, value)
        tag_out, value_out, offset = _parse_tlv(encoded, 0)
        assert tag_out == tag, (hex(tag), value)
        assert value_out == value, (hex(tag), value)
        assert offset == len(encoded), (hex(tag), value)


def test_decode_varbind_value_independent_oracle() -> None:
    cases = [
        (TAG_OCTET_STRING, b"Linux router 5.4.0", "Linux router 5.4.0"),
        (TAG_OID, bytes([43, 6, 1, 2, 1, 1, 2, 0]), "1.3.6.1.2.1.1.2.0"),
        (TAG_INTEGER, b"\xff", -1),
        (0x41, (255).to_bytes(4, "big"), 255),  # counter32
        (0x42, (7).to_bytes(4, "big"), 7),  # gauge32
        (TAG_TIMETICKS, (12345678).to_bytes(4, "big"), 12345678),
        (TAG_IPADDRESS, bytes([192, 168, 1, 1]), "192.168.1.1"),
        (0x46, (2**40).to_bytes(8, "big"), 2**40),  # counter64
        (0x80, b"", None),  # endOfMibView
        (0x81, b"", None),  # noSuchObject
        (0x82, b"", None),  # noSuchInstance
        (0x99, b"\xab\xcd", "abcd"),  # unknown type -> hex
    ]
    for tag, value, expected in cases:
        assert _decode_varbind_value(tag, value) == expected, (hex(tag), value)


def test_parse_snmp_message_varbind_round_trip() -> None:
    varbinds = [
        (SYSDESC, TAG_OCTET_STRING, b"Linux router 5.4.0"),
        (SYSOBJECTID, TAG_OID, bytes([43, 6, 1, 2, 1, 1, 2, 0])),
        (SYSUPTIME, TAG_TIMETICKS, (12345678).to_bytes(4, "big")),
        (SYSNAME, TAG_OCTET_STRING, b"router-01"),
    ]
    message = _parse_snmp_message(_build_get_response(varbinds=varbinds))
    assert message["version"] == 1
    assert message["community"] == "public"
    assert message["pdu_type"] == "get-response"
    assert [vb["oid"] for vb in message["varbinds"]] == [
        SYSDESC, SYSOBJECTID, SYSUPTIME, SYSNAME
    ]
    assert message["varbinds"][0]["value"] == "Linux router 5.4.0"
    assert message["varbinds"][1]["value"] == "1.3.6.1.2.1.1.2.0"
    assert message["varbinds"][2]["value"] == 12345678
    assert message["varbinds"][3]["value"] == "router-01"
