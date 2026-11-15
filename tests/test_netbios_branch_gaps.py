"""Tests for reachable partial branches in ethscan/netbios.py.

Covers arcs identified by branch coverage that are reachable with crafted inputs.
The arc 131->144 (bracket_end <= 0 under guard) is defensive/unreachable:
the guard `host.startswith("[") and "]:" in host` guarantees find("]:") >= 1.
"""

from __future__ import annotations

import struct

from ethscan.netbios import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SUFFIX,
    RR_CLASS_IN,
    RR_TYPE_NBSTAT,
    _encode_qname,
    _normalize_target,
    run_netbios,
)


def _connector_for(body: bytes):
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None
    return connector


def _build_nbstat_response(
    transaction_id: int = 0x1234,
    qdname: bytes | None = None,
    entries=None,
    rcode: int = 0,
    is_response: bool = True,
    qdcount: int = 1,
    ancount: int = 1,
) -> bytes:
    """Build a raw NBNS NODE STATUS response packet (copied from test_netbios.py)."""
    if qdname is None:
        qdname = _encode_qname(DEFAULT_NAME, DEFAULT_SUFFIX)

    if entries is None:
        # Default system entries
        entries = _system_rdata()

    resp_flag = 0x8000 if is_response else 0x0000
    flags = resp_flag | (rcode & 0x000F)
    header = struct.pack("!HHHHHH", transaction_id, flags, qdcount, ancount, 0, 0)

    if qdcount:
        question = qdname + struct.pack("!HH", RR_TYPE_NBSTAT, RR_CLASS_IN)
    else:
        question = b""

    answer = b"\xc0\x0c"  # compression pointer to offset 12 (question name)
    answer += struct.pack("!HHI", RR_TYPE_NBSTAT, RR_CLASS_IN, 0)  # type, class, ttl
    answer += struct.pack("!H", len(entries)) + entries

    return header + question + answer


def _system_entries() -> list:
    """A typical NBSTAT name table for a workstation server."""
    return [
        _entry("MYHOST", 0x00, 0x0400),     # unique workstation, active
        _entry("MYHOST", 0x20, 0x0400),     # unique file server (SMB shares)
        _entry("MYHOST", 0x01, 0x0400),     # unique messenger
        _entry("WORKGROUP", 0x00, 0x8600),  # group domain name, permanent
        _entry("WORKGROUP", 0x1E, 0x8600),  # group browser-election name
    ]


def _system_rdata(mac: bytes = b"\xa0\xb1\xc2\xd3\xe4\xf5") -> bytes:
    entries = _system_entries()
    return bytes([len(entries)]) + b"".join(entries) + mac + b"\x00" * 10


def _entry(name: str, suffix: int, flags: int) -> bytes:
    """Build an 18-byte NBSTAT NODE_NAME entry (15 name + 1 suffix + 2 flags)."""
    raw_name = name.upper().encode("ascii", "replace").ljust(15, b" ")
    return raw_name + bytes([suffix]) + struct.pack("!H", flags)


# ---------------------------------------------------------------------------
# _normalize_target: non-digit port suffix branches (133->144, 138->144)
# ---------------------------------------------------------------------------

def test_normalize_target_bracketed_ipv6_nondigit_port() -> None:
    """Cover 133->144: bracketed IPv6 with non-digit port part after ']:'.

    The branch is taken when port_part.isdigit() is False.
    Current behavior: host remains unchanged (port part not stripped).
    """
    host, port = _normalize_target("[fd00::1]:abc")
    assert host == "[fd00::1]:abc"  # port not stripped when non-digit
    assert port == DEFAULT_PORT  # falls back to default


def test_normalize_target_unbracketed_nondigit_port() -> None:
    """Cover 138->144: unbracketed host with non-digit port part after ':'.

    The branch is taken when rest.isdigit() is False.
    Current behavior: host remains unchanged (port part not stripped).
    """
    host, port = _normalize_target("192.168.1.100:abc")
    assert host == "192.168.1.100:abc"  # port not stripped when non-digit
    assert port == DEFAULT_PORT  # falls back to default


# ---------------------------------------------------------------------------
# _parse_nbns_response: no-mac and no-names branches (414->416, 416->426)
# ---------------------------------------------------------------------------

def _build_nbstat_response_no_mac() -> bytes:
    """Build NBSTAT response with names but no MAC (rdata shorter than 6 bytes after names)."""
    # One name entry, no room for MAC
    name_entry = b"MYHOST".upper().ljust(15, b" ") + bytes([0x00]) + struct.pack("!H", 0x0400)
    rdata = bytes([1]) + name_entry  # num_names=1, no MAC bytes
    return _build_nbstat_response(entries=rdata)


def _build_nbstat_response_no_names() -> bytes:
    """Build NBSTAT response with MAC but zero names."""
    rdata = bytes([0]) + b"\xaa\xbb\xcc\xdd\xee\xff" + b"\x00" * 10
    return _build_nbstat_response(entries=rdata)


def test_parse_nbns_response_no_mac_covers_414_416() -> None:
    """Cover 414->416: parsed mac is None/falsy, names is truthy."""
    from ethscan.netbios import _parse_nbns_response
    message = _parse_nbns_response(_build_nbstat_response_no_mac())
    assert message["mac"] is None
    assert message["names"] == [{"name": "MYHOST", "suffix": 0, "suffix_hex": "0x00",
                                 "service_type": "Workstation service",
                                 "flags": {"group": False, "unique": True,
                                           "owner_node_type": "B-node",
                                           "permanent": False, "transient": True,
                                           "active": True, "conflict": False,
                                           "deregister": False, "raw": 0x0400}}]


def test_parse_nbns_response_no_names_covers_416_426() -> None:
    """Cover 416->426: parsed names is empty/falsy, mac is truthy."""
    from ethscan.netbios import _parse_nbns_response
    message = _parse_nbns_response(_build_nbstat_response_no_names())
    assert message["mac"] == "aa:bb:cc:dd:ee:ff"
    assert message["names"] == []


def test_run_netbios_no_mac_branch() -> None:
    """End-to-end: run_netbios with response that has names but no MAC."""
    results = run_netbios("192.168.1.100", timeout=1.0, connector=_connector_for(_build_nbstat_response_no_mac()))
    assert results["mac"] is None
    assert results["num_names"] == 1
    assert results["error"] is None


def test_run_netbios_no_names_branch() -> None:
    """End-to-end: run_netbios with response that has MAC but no names."""
    results = run_netbios("192.168.1.100", timeout=1.0, connector=_connector_for(_build_nbstat_response_no_names()))
    assert results["mac"] == "aa:bb:cc:dd:ee:ff"
    assert results["names"] == []
    assert results["num_names"] == 0
    assert results["error"] is None