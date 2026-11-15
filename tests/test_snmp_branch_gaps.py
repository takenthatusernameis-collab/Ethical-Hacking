"""Focused branch-coverage tests for ethscan/snmp.py edge cases."""
from __future__ import annotations



from ethscan.snmp import (
    DEFAULT_PORT,
    STANDARD_OIDS,
    TAG_GET_RESPONSE,
    TAG_OCTET_STRING,
    TAG_OID,
    TAG_SEQUENCE,
    TAG_TIMETICKS,
    _encode_integer,
    _encode_octet_string,
    _encode_oid,
    _encode_oid_value,
    _encode_tlv,
    _normalize_target,
    run_snmp,
)

SYSDESC = STANDARD_OIDS["sysDescr"]
SYSOBJECTID = STANDARD_OIDS["sysObjectID"]
SYSUPTIME = STANDARD_OIDS["sysUpTime"]
SYSNAME = STANDARD_OIDS["sysName"]


def _build_get_response(
    version: int = 1,
    community: str = "public",
    varbinds: list[tuple[str, int, bytes]] | None = None,
    error_status: int = 0,
    request_id: int = 1,
) -> bytes:
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
) -> list[tuple[str, int, bytes]]:
    if sys_object_id is None:
        sys_object_id = _encode_oid_value("1.3.6.1.4.1.9.1.1")
    return [
        (SYSDESC, TAG_OCTET_STRING, sys_descr),
        (SYSOBJECTID, TAG_OID, sys_object_id),
        (SYSUPTIME, TAG_TIMETICKS, sys_up_ticks.to_bytes(4, "big")),
        (SYSNAME, TAG_OCTET_STRING, sys_name),
    ]


# --- _normalize_target branches ---


def test_normalize_target_bracketed_host_with_non_numeric_port_suffix() -> None:
    """[::1]:abc -> port_part not digit; host/port parsing falls through (135->146)."""
    host, port = _normalize_target("[::1]:abc")
    assert host == "[::1]:abc"
    assert port == DEFAULT_PORT


def test_normalize_target_host_with_non_numeric_port_suffix() -> None:
    """host:abc -> rest not digit; host unchanged (140->146)."""
    host, port = _normalize_target("snmp.example.com:abc")
    assert host == "snmp.example.com:abc"
    assert port == DEFAULT_PORT


# --- run_snmp loop branch 577->576 ---


def test_run_snmp_preserves_existing_sys_fields_on_second_valid_community() -> None:
    """First valid community sets snmp_version+sys fields; second valid re-enters
    the sys-field loop but skips assignments because results[key] is already set
    (577->576 false branch)."""
    calls: list[str] = []

    def connector(
        host: str, port: int, data: bytes, timeout: float
    ) -> tuple[bytes | None, str | None]:
        calls.append("call")
        return _build_get_response(version=1, community="x", varbinds=_system_varbinds()), None

    results = run_snmp(
        "snmp.example.com",
        communities=["public", "private"],
        connector=connector,
    )
    assert results["valid_communities"] == ["public", "private"]
    assert results["snmp_version"] == "v2c"
    assert results["sysName"] == "router-01"
    # v2c probe succeeds on first try for each community -> 2 calls total
    assert len(calls) == 2
