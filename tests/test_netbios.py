"""Tests for the ethscan netbios module."""

from __future__ import annotations

import csv
import io
import json
import random
import socket
import struct

import pytest

from ethscan.netbios import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SUFFIX,
    RCODE_NAMES,
    RR_CLASS_IN,
    RR_TYPE_NB,
    RR_TYPE_NBSTAT,
    _build_nbns_query,
    _decode_name_chars,
    _encode_name_chars,
    _encode_qname,
    _normalize_target,
    _parse_dns_name,
    _parse_name_flags,
    _parse_nbns_response,
    _parse_nbtstat_rdata,
    _send_recv,
    format_netbios_report_csv,
    format_netbios_report_json,
    format_netbios_report_markdown,
    run_netbios,
)
from ethscan.target import TargetSpecError

# ---------------------------------------------------------------------------
# Test helpers to build well-formed NBNS messages
# ---------------------------------------------------------------------------


def _entry(name: str, suffix: int, flags: int) -> bytes:
    """Build an 18-byte NBSTAT NODE_NAME entry (15 name + 1 suffix + 2 flags)."""
    raw_name = name.upper().encode("ascii", "replace").ljust(15, b" ")
    return raw_name + bytes([suffix]) + struct.pack("!H", flags)


def _build_nbstat_response(
    transaction_id: int = 0x1234,
    qdname: bytes | None = None,
    entries=None,
    rcode: int = 0,
    is_response: bool = True,
    qdcount: int = 1,
    ancount: int = 1,
) -> bytes:
    """Build a raw NBNS NODE STATUS response packet."""
    if qdname is None:
        qdname = _encode_qname(DEFAULT_NAME, DEFAULT_SUFFIX)

    if entries is None:
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


def _full_response(mac: bytes = b"\xa0\xb1\xc2\xd3\xe4\xf5") -> bytes:
    return _build_nbstat_response(
        qdname=_encode_qname(DEFAULT_NAME, DEFAULT_SUFFIX),
        entries=_system_rdata(mac),
    )


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("192.168.1.100:138")
    assert host == "192.168.1.100"
    assert port == 138


def test_normalize_target_url_with_port() -> None:
    host, port = _normalize_target("netbios://192.168.1.100:138")
    assert host == "192.168.1.100"
    assert port == 138


def test_normalize_target_url_default_port() -> None:
    host, port = _normalize_target("netbios://192.168.1.100")
    assert host == "192.168.1.100"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


def test_normalize_target_ipv6_url() -> None:
    host, port = _normalize_target("netbios://[fd00::1]:137")
    assert host == "fd00::1"
    assert port == 137
    host, port = _normalize_target("[fd00::1]:137")
    assert host == "fd00::1"
    assert port == 137
    host, port = _normalize_target("[fd00::1]")
    assert host == "fd00::1"
    assert port == DEFAULT_PORT


def test_normalize_target_bracket_without_port_separator() -> None:
    """A bracketed host lacking ``]:`` keeps the literal target; URLs raise."""
    host, port = _normalize_target("[example")
    assert host == "[example"
    assert port == DEFAULT_PORT
    import pytest
    with pytest.raises(TargetSpecError, match="Invalid IPv6 URL"):
        _normalize_target("netbios://[example")


# ---------------------------------------------------------------------------
# Name encoding / decoding (RFC 1001 first-level encoding)
# ---------------------------------------------------------------------------


def test_encode_qname_structure() -> None:
    q = _encode_qname("MYHOST", 0x00)
    assert q[0] == 0x20  # length prefix (32 encoded chars)
    assert q[-1] == 0x00  # root terminator
    assert len(q) == 34


def test_encode_name_chars_roundtrip() -> None:
    chars = _encode_name_chars("MYHOST", 0x20)
    assert len(chars) == 32
    name, suffix = _decode_name_chars(chars)
    assert name == "MYHOST"
    assert suffix == 0x20


def test_encode_name_chars_wildcard() -> None:
    chars = _encode_name_chars(DEFAULT_NAME, 0x00)
    assert len(chars) == 32
    name, suffix = _decode_name_chars(chars)
    assert name == DEFAULT_NAME
    assert suffix == 0x00


def test_encode_name_chars_padding() -> None:
    chars = _encode_name_chars("AB", 0x00)
    name, suffix = _decode_name_chars(chars)
    assert name == "AB"
    assert suffix == 0x00


_PROPERTY_SEED = 20261127
_NAME_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@#$%^&()[]{}!~`' "


def _rfc1001_first_level_oracle(name: str, suffix: int) -> bytes:
    """Independent RFC 1001 first-level encoding (each nibble -> ASCII A-P)."""
    padded = name.upper().encode("ascii", "replace").ljust(15, b" ")[:15]
    raw = padded + bytes([suffix & 0xFF])
    out = bytearray()
    for byte in raw:
        out.append(0x41 + (byte >> 4))
        out.append(0x41 + (byte & 0x0F))
    return bytes(out)


def test_encode_name_chars_matches_rfc1001_oracle() -> None:
    """First-level encoding matches an independent RFC 1001 oracle."""
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(4000):
        length = rng.randint(0, 15)
        name = "".join(rng.choice(_NAME_ALPHABET) for _ in range(length))
        suffix = rng.randint(0, 255)
        assert _encode_name_chars(name, suffix) == _rfc1001_first_level_oracle(
            name, suffix
        )


def test_encode_decode_roundtrip_random_names() -> None:
    """Names without surrounding spaces round-trip through encode/decode."""
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(4000):
        length = rng.randint(1, 15)
        name = "".join(rng.choice(_NAME_ALPHABET) for _ in range(length))
        # The fixed-width field strips surrounding spaces by design.
        name = (name.strip() or "X")[:15]
        suffix = rng.randint(0, 255)
        decoded, decoded_suffix = _decode_name_chars(
            _encode_name_chars(name, suffix)
        )
        assert decoded == name.upper()
        assert decoded_suffix == suffix


def test_decode_name_chars_invalid_char_raises() -> None:
    with pytest.raises(ValueError):
        _decode_name_chars(b"\x00" * 32)  # 'A'-1 is invalid nibble


def test_decode_name_chars_odd_length_raises() -> None:
    with pytest.raises(ValueError):
        _decode_name_chars(b"A" * 31)


def test_decode_name_chars_too_short_raises() -> None:
    """A name that is too short to hold a suffix byte is malformed.

    A first-level name is 32 chars: 15 name bytes and one suffix byte. A
    shorter (but even) name used to be decoded into fewer than 16 bytes and
    the suffix byte was then read out of range.
    """
    with pytest.raises(ValueError):
        _decode_name_chars(b"A" * 30)
    with pytest.raises(ValueError):
        _decode_name_chars(b"A" * 2)


# ---------------------------------------------------------------------------
# _build_nbns_query
# ---------------------------------------------------------------------------


def test_build_nbns_query_structure() -> None:
    pkt = _build_nbns_query("MYHOST", 0x00, transaction_id=0x1234)
    assert len(pkt) >= 12
    txn, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", pkt[:12])
    assert txn == 0x1234
    assert flags == 0x0000
    assert qd == 1
    assert an == 0
    assert ns == 0
    assert ar == 0


def test_build_nbns_query_contains_qtype_nbtstat() -> None:
    pkt = _build_nbns_query("MYHOST", 0x00, transaction_id=1)
    # question = qname + QTYPE(2) + QCLASS(2); qname ends with 0x00 terminator
    qname = _encode_qname("MYHOST", 0x00)
    qtype, qclass = struct.unpack("!HH", pkt[12 + len(qname):12 + len(qname) + 4])
    assert qtype == RR_TYPE_NBSTAT
    assert qclass == RR_CLASS_IN


def test_build_nbns_query_default_name() -> None:
    pkt = _build_nbns_query()
    msg = _parse_nbns_response(pkt)
    # A query has QDCOUNT=1 with a NBSTAT question; re-parsing the question name.
    assert msg["question_count"] == 1
    assert msg["answer_count"] == 0


# ---------------------------------------------------------------------------
# _parse_dns_name
# ---------------------------------------------------------------------------


def test_parse_dns_name_first_level() -> None:
    q = _encode_qname("MYHOST", 0x00)
    name, offset = _parse_dns_name(q, 0)
    assert name == "MYHOST"
    assert offset == len(q)


def test_parse_dns_name_compression_pointer() -> None:
    q = _encode_qname("MYHOST", 0x00)
    data = q + b"\xc0\x00" + b"\x00" * 6  # pointer back to start
    name, offset = _parse_dns_name(data, len(q))
    assert name == "MYHOST"
    assert offset == len(q) + 2


def test_parse_dns_name_pointer_loop_protection() -> None:
    data = b"\xc0\x02\xc0\x02" + b"\x00"
    with pytest.raises(ValueError):
        _parse_dns_name(data, 0)


def test_parse_dns_name_truncated_label_raises() -> None:
    with pytest.raises(ValueError):
        _parse_dns_name(b"\x05abc", 0)


def test_parse_dns_name_empty_name_returns_empty() -> None:
    # A root label immediately -> no labels collected -> raw is empty.
    name, offset = _parse_dns_name(b"\x00", 0)
    assert name == ""
    assert offset == 1


_DNSNAME_SEED = 20261128
_DNSNAME_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@#$%^&()[]{}!~`' "


def _oracle_first_level(name: str, suffix: int) -> bytes:
    """Independent RFC 1001 first-level encoder (does not reuse ethscan code)."""
    padded = name.upper().encode("ascii", "replace").ljust(15, b" ")[:15]
    raw = padded + bytes([suffix & 0xFF])
    out = bytearray()
    for byte in raw:
        out.append(0x41 + (byte >> 4))
        out.append(0x41 + (byte & 0x0F))
    return bytes(out)


def _oracle_qname(name: str, suffix: int) -> bytes:
    chars = _oracle_first_level(name, suffix)
    return bytes([len(chars)]) + chars + b"\x00"


def _oracle_decoded(name: str) -> str:
    # _decode_name_chars uppercases then strips trailing spaces and NULs.
    return name.upper().rstrip(" ").rstrip("\x00")


def test_parse_dns_name_matches_independent_oracle_random() -> None:
    """Decompression + next_offset match an independent encoder oracle.

    Covers uncompressed qnames and DNS compression pointers (0xC0) that jump
    back to an earlier name, over random names/suffixes.
    """
    rng = random.Random(_DNSNAME_SEED)
    for _ in range(3000):
        length = rng.randint(0, 15)
        name = "".join(rng.choice(_DNSNAME_ALPHABET) for _ in range(length))
        suffix = rng.randint(0, 255)
        exp_name = _oracle_decoded(name)

        q = _oracle_qname(name, suffix)
        got_name, got_off = _parse_dns_name(q, 0)
        assert got_name == exp_name
        assert got_off == len(q)

        pad = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 4)))
        data = q + pad + b"\xc0\x00" + b"\x00" * 4
        ptr_off = len(q) + len(pad)
        got_name, got_off = _parse_dns_name(data, ptr_off)
        assert got_name == exp_name
        assert got_off == ptr_off + 2


def test_parse_dns_name_hostile_bytes_never_crash() -> None:
    """Arbitrary bytes never raise anything but ValueError (no hang/crash)."""
    rng = random.Random(_DNSNAME_SEED + 1)
    for _ in range(3000):
        n = rng.randint(0, 40)
        data = bytes(rng.randint(0, 255) for _ in range(n))
        off = rng.randint(0, n) if n else 0
        try:
            result = _parse_dns_name(data, off)
        except ValueError:
            continue
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _parse_name_flags
# ---------------------------------------------------------------------------


def test_parse_name_flags_unique_active_permanent() -> None:
    flags = _parse_name_flags(0x8600)
    assert flags["group"] is True
    assert flags["unique"] is False
    assert flags["permanent"] is True
    assert flags["active"] is True
    assert flags["conflict"] is False
    assert flags["deregister"] is False
    assert flags["owner_node_type"] == "B-node"


def test_parse_name_flags_unique_transient() -> None:
    flags = _parse_name_flags(0x0400)
    assert flags["group"] is False
    assert flags["unique"] is True
    assert flags["permanent"] is False
    assert flags["transient"] is True


def test_parse_name_flags_conflict_deregister() -> None:
    flags = _parse_name_flags(0x1800)  # DRG (0x1000) | CNF (0x0800)
    assert flags["conflict"] is True
    assert flags["deregister"] is True


def test_parse_name_flags_owner_node_type_m() -> None:
    # ONT bits (14-13) = 10 -> M-node; bit 14 = 0x4000
    flags = _parse_name_flags(0x4000 | 0x0400)
    assert flags["owner_node_type"] == "M-node"


def test_parse_name_flags_owner_node_type_p() -> None:
    # ONT bits (14-13) = 01 -> P-node; bit 13 = 0x2000
    flags = _parse_name_flags(0x2000 | 0x0400)
    assert flags["owner_node_type"] == "P-node"


# ---------------------------------------------------------------------------
# _parse_nbtstat_rdata
# ---------------------------------------------------------------------------


def test_parse_nbtstat_rdata_names_and_mac() -> None:
    rdata = _system_rdata(mac=b"\xaa\xbb\xcc\xdd\xee\xff")
    result = _parse_nbtstat_rdata(rdata)
    assert result["num_names"] == 5
    assert len(result["names"]) == 5
    assert result["mac"] == "aa:bb:cc:dd:ee:ff"
    assert result["names"][0]["name"] == "MYHOST"
    assert result["names"][0]["suffix"] == 0x00
    assert result["names"][0]["service_type"] == "Workstation service"
    assert result["names"][1]["suffix"] == 0x20
    assert result["names"][1]["service_type"] == "File server service"


def test_parse_nbtstat_rdata_group_name() -> None:
    rdata = _system_rdata(mac=b"\x01\x02\x03\x04\x05\x06")
    result = _parse_nbtstat_rdata(rdata)
    workgroup = next(n for n in result["names"] if n["name"] == "WORKGROUP")
    assert workgroup["flags"]["group"] is True
    assert workgroup["flags"]["permanent"] is True


def test_parse_nbtstat_rdata_empty_raises() -> None:
    with pytest.raises(ValueError):
        _parse_nbtstat_rdata(b"")


def test_parse_nbtstat_rdata_truncated_entry_raises() -> None:
    rdata = bytes([3]) + b"\x00" * 10  # claims 3 names but only 10 bytes follow
    with pytest.raises(ValueError):
        _parse_nbtstat_rdata(rdata)


def test_parse_nbtstat_rdata_unknown_suffix() -> None:
    rdata = bytes([1]) + _entry("HOST", 0x99, 0x0400) + b"\x00" * 6
    result = _parse_nbtstat_rdata(rdata)
    assert result["names"][0]["service_type"] == "unknown (0x99)"


def test_parse_nbtstat_rdata_missing_mac() -> None:
    # No room for the 6-byte Unit ID after a single name entry.
    rdata = bytes([1]) + _entry("HOST", 0x00, 0x0400)
    result = _parse_nbtstat_rdata(rdata)
    assert result["mac"] is None
    assert result["names"][0]["name"] == "HOST"


# ---------------------------------------------------------------------------
# _parse_nbtstat_rdata independent-oracle differential tests
# ---------------------------------------------------------------------------

_NBSTAT_SEED = 20261129
_NBSTAT_NAME_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.*@"

# Independent suffix -> service type mapping (RFC 1002 well-known suffixes;
# does not reuse the SUFFIX_SERVICE_TYPES table from ethscan).
_NBSTAT_SUFFIX_ORACLE = {
    0x00: "Workstation service",
    0x01: "Messenger service",
    0x02: "Reserved",
    0x03: "Messenger service (alias)",
    0x04: "Reserved",
    0x05: "Reserved",
    0x06: "Reserved",
    0x07: "Remote Access Service",
    0x08: "Reservoir",
    0x09: "Reservoir",
    0x0A: "Reservoir",
    0x0B: "RAS service",
    0x17: "RAS service",
    0x1B: "Domain master browser",
    0x1C: "Domain controllers",
    0x1D: "Master browser",
    0x1E: "Browser service elections",
    0x20: "File server service",
    0x2B: "Remote Access Service",
    0x2C: "Remote Access Service",
    0x2D: "Remote Access Service",
    0x2E: "Remote Access Service",
    0x2F: "Remote Access Service",
    0x33: "Default name",
    0x34: "SMB server",
}


def _oracle_nbtstat_entry(name: str, suffix: int, flags: int) -> bytes:
    """Independent builder of one 18-byte NBSTAT NODE_NAME entry.

    Encodes the 15-byte space-padded name, one suffix byte, and two big-endian
    flag bytes from scratch; does not reuse the ethscan/_entry test helper.
    """
    raw = name.upper().encode("ascii", "replace")[:15].ljust(15, b" ")
    return raw + bytes([suffix & 0xFF]) + struct.pack("!H", flags & 0xFFFF)


def _oracle_nbtstat_flags(flags: int) -> dict:
    """Independent decode of the 16-bit NODE_NAME_FLAGS field (RFC 1002)."""
    ont = (flags >> 13) & 0x03
    return {
        "group": bool(flags & 0x8000),
        "unique": not bool(flags & 0x8000),
        "owner_node_type": ["B-node", "P-node", "M-node", "reserved"][ont],
        "permanent": bool(flags & 0x0200),
        "transient": not bool(flags & 0x0200),
        "active": bool(flags & 0x0400),
        "conflict": bool(flags & 0x0800),
        "deregister": bool(flags & 0x1000),
        "raw": flags & 0xFFFF,
    }


def test_parse_nbtstat_rdata_matches_independent_oracle_random() -> None:
    """Random NBSTAT RDATA parsed by the implementation matches an
    independent from-scratch builder oracle (names, suffixes, flags, MAC).
    """
    rng = random.Random(_NBSTAT_SEED)
    for _ in range(3000):
        num_names = rng.randint(0, 6)
        entries = []
        expected_names = []
        for _ in range(num_names):
            length = rng.randint(0, 15)
            name = "".join(
                rng.choice(_NBSTAT_NAME_ALPHABET) for _ in range(length)
            )
            suffix = rng.randint(0, 255)
            flags = rng.randint(0, 0xFFFF)
            entries.append(_oracle_nbtstat_entry(name, suffix, flags))
            expected_names.append((name, suffix, flags))

        rdata = bytearray([num_names])
        rdata.extend(b"".join(entries))
        mac = bytes(rng.randint(0, 255) for _ in range(6))
        rdata.extend(mac)
        rdata.extend(bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 3))))

        result = _parse_nbtstat_rdata(bytes(rdata))
        assert result["num_names"] == num_names
        assert len(result["names"]) == num_names
        for i, (name, suffix, flags) in enumerate(expected_names):
            entry = result["names"][i]
            exp_name = name.upper().rstrip(" ").rstrip("\x00")
            assert entry["name"] == exp_name, (i, entry["name"], exp_name)
            assert entry["suffix"] == suffix
            assert entry["suffix_hex"] == f"0x{suffix:02x}"
            want_service = _NBSTAT_SUFFIX_ORACLE.get(
                suffix, f"unknown (0x{suffix:02x})"
            )
            assert entry["service_type"] == want_service
            assert entry["flags"] == _oracle_nbtstat_flags(flags)
        assert result["mac"] == ":".join(f"{b:02x}" for b in mac)


def test_parse_nbtstat_rdata_hostile_bytes_never_crash() -> None:
    """Arbitrary byte buffers raise only ValueError or return a dict; no
    hang, crash, or other exception type.
    """
    rng = random.Random(_NBSTAT_SEED + 1)
    for _ in range(3000):
        n = rng.randint(0, 60)
        data = bytes(rng.randint(0, 255) for _ in range(n))
        try:
            result = _parse_nbtstat_rdata(data)
        except ValueError:
            continue
        assert isinstance(result, dict)
        assert set(result) == {"num_names", "names", "mac"}
        assert isinstance(result["num_names"], int)
        assert isinstance(result["names"], list)
        assert result["mac"] is None or isinstance(result["mac"], str)


# ---------------------------------------------------------------------------
# _parse_nbns_response
# ---------------------------------------------------------------------------


def test_parse_nbns_response_full() -> None:
    message = _parse_nbns_response(_full_response(mac=b"\xaa\xbb\xcc\xdd\xee\xff"))
    assert message["transaction_id"] == 0x1234
    assert message["flags"]["is_response"] is True
    assert message["flags"]["rcode"] == 0
    assert message["question_count"] == 1
    assert message["answer_count"] == 1
    assert message["mac"] == "aa:bb:cc:dd:ee:ff"
    assert len(message["names"]) == 5
    assert message["num_names"] == 5


def test_parse_nbns_response_rcode_error() -> None:
    data = _build_nbstat_response(rcode=3, ancount=0)
    message = _parse_nbns_response(data)
    assert message["flags"]["rcode"] == 3
    assert message["flags"]["rcode_name"] == RCODE_NAMES[3]


def test_parse_nbns_response_not_a_response() -> None:
    data = _build_nbstat_response(is_response=False)
    message = _parse_nbns_response(data)
    assert message["flags"]["is_response"] is False


def test_parse_nbns_response_truncated_header_raises() -> None:
    with pytest.raises(ValueError):
        _parse_nbns_response(b"\x00\x00\x00")


def test_parse_nbns_response_truncated_answer_raises() -> None:
    # ANCOUNT claims an answer but there's no room for it.
    header = struct.pack("!HHHHHH", 0x1234, 0x8000, 0, 1, 0, 0)
    with pytest.raises(ValueError):
        _parse_nbns_response(header)


def test_parse_nbns_response_truncated_rr_header() -> None:
    # Answer name parses but fewer than 10 bytes remain for the RR header.
    header = struct.pack("!HHHHHH", 0x1234, 0x8000, 0, 1, 0, 0)  # ancount=1
    data = header + b"\x05hello\x00"  # name consumes to offset 19; <10 bytes left
    with pytest.raises(ValueError):
        _parse_nbns_response(data)


def test_parse_nbns_response_truncated_rr_rdata() -> None:
    # Full RR header present but rdlength claims more bytes than available.
    header = struct.pack("!HHHHHH", 0x1234, 0x8000, 0, 1, 0, 0)  # ancount=1
    rr = struct.pack("!HHIH", RR_TYPE_NBSTAT, RR_CLASS_IN, 0, 100)  # rdlength=100
    data = header + b"\x05hello\x00" + rr  # no rdata bytes follow
    with pytest.raises(ValueError):
        _parse_nbns_response(data)


def test_parse_nbns_response_nb_record() -> None:
    header = struct.pack("!HHHHHH", 0x1234, 0x8000, 0, 1, 0, 0)  # ancount=1
    rr = struct.pack("!HHIH", RR_TYPE_NB, RR_CLASS_IN, 0, 4)
    data = header + b"\x05hello\x00" + rr + b"\x0a\x00\x00\x01"
    message = _parse_nbns_response(data)
    ans = message["answers"][0]
    assert ans["type_name"] == "nb"
    assert ans["address"] == "10.0.0.1"


def test_parse_nbns_response_unknown_rr_type() -> None:
    header = struct.pack("!HHHHHH", 0x1234, 0x8000, 0, 1, 0, 0)  # ancount=1
    rr = struct.pack("!HHIH", 0x0001, RR_CLASS_IN, 0, 2)
    data = header + b"\x05hello\x00" + rr + b"\x0a\x00"
    message = _parse_nbns_response(data)
    ans = message["answers"][0]
    assert ans["type_name"] == "0x0001"


# ---------------------------------------------------------------------------
# _parse_nbns_response independent-oracle differential tests
# ---------------------------------------------------------------------------

_NBNS_SEED = 20261130

# Independent NBNS RCODE -> name map (RFC 1002); does not reuse ethscan.
_NBNS_RCODE_ORACLE = {
    0: "No error",
    1: "Format error",
    2: "Server failure",
    3: "Name error",
    4: "Unsupported option",
    5: "Refused",
    6: "Name in conflict",
    7: "DNS server (name in use)",
    8: "DNIND (duplicate name)",
    15: "Transaction rejected",
}

# RR types that are neither NB (0x0020) nor NBSTAT (0x0021).
_NBNS_UNKNOWN_TYPES = [0x0001, 0x0002, 0x000F, 0x0010, 0x0022, 0x00FF]


def _oracle_nbstat_name_dict(name: str, suffix: int, flags: int) -> dict:
    """Independent expected name-entry dict (mirrors the RFC 1002 decode)."""
    return {
        "name": name.upper().rstrip(" ").rstrip("\x00"),
        "suffix": suffix,
        "suffix_hex": f"0x{suffix:02x}",
        "service_type": _NBSTAT_SUFFIX_ORACLE.get(
            suffix, f"unknown (0x{suffix:02x})"
        ),
        "flags": _oracle_nbtstat_flags(flags),
    }


def _oracle_build_nbns_message(rng: random.Random) -> tuple[bytes, dict]:
    """Build a random NBNS message from scratch and its expected parse.

    Uses only independent oracles (no ethscan helpers, no test ``_entry`` /
    ``_build_nbstat_response``). Returns the packet bytes and the dict that
    ``_parse_nbns_response`` must produce for it.
    """
    transaction_id = rng.randint(0, 0xFFFF)
    opcode = rng.randint(0, 0xF)
    rcode = rng.randint(0, 0xF)
    is_response = bool(rng.getrandbits(1))
    flags_raw = (0x8000 if is_response else 0x0000) | (opcode << 11) | rcode

    qdcount = rng.randint(0, 1)
    body = b""
    if qdcount:
        qname = "".join(
            rng.choice(_NBSTAT_NAME_ALPHABET) for _ in range(rng.randint(0, 15))
        )
        qsuf = rng.randint(0, 255)
        body += _oracle_qname(qname, qsuf)
        body += struct.pack("!HH", RR_TYPE_NBSTAT, RR_CLASS_IN)

    ancount = rng.randint(0, 4)
    header = struct.pack(
        "!HHHHHH", transaction_id, flags_raw, qdcount, ancount, 0, 0
    )

    answers: list[dict] = []
    top_mac = None
    top_names: list[dict] = []
    for _ in range(ancount):
        # Answer name: a compression pointer to the question (offset 12) when a
        # question exists, otherwise a fresh uncompressed encoded name.
        if qdcount:
            body += b"\xc0\x0c"
        else:
            aname = "".join(
                rng.choice(_NBSTAT_NAME_ALPHABET)
                for _ in range(rng.randint(0, 15))
            )
            body += _oracle_qname(aname, rng.randint(0, 255))

        kind = rng.choice(["nbstat", "nb", "unknown"])
        ttl = rng.randint(0, 0xFFFFFFFF)
        if kind == "nbstat":
            rr_type = RR_TYPE_NBSTAT
            num_names = rng.randint(0, 4)
            entries = []
            exp_names = []
            for _ in range(num_names):
                length = rng.randint(0, 15)
                nm = "".join(
                    rng.choice(_NBSTAT_NAME_ALPHABET) for _ in range(length)
                )
                sf = rng.randint(0, 255)
                fl = rng.randint(0, 0xFFFF)
                entries.append(_oracle_nbtstat_entry(nm, sf, fl))
                exp_names.append(_oracle_nbstat_name_dict(nm, sf, fl))
            mac = bytes(rng.randint(0, 255) for _ in range(6))
            rdata = bytes([num_names]) + b"".join(entries) + mac
            rdata += bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 3)))
            mac_str = ":".join(f"{b:02x}" for b in mac)
            answers.append({
                "type": rr_type,
                "class": RR_CLASS_IN,
                "ttl": ttl,
                "rdata_length": len(rdata),
                "type_name": "nbstat",
                "mac": mac_str,
                "names": exp_names,
                "num_names": num_names,
            })
            if mac_str:
                top_mac = mac_str
            if exp_names:
                top_names = exp_names
        elif kind == "nb":
            rr_type = RR_TYPE_NB
            if rng.random() < 0.8:
                rdata = bytes(rng.randint(0, 255) for _ in range(4))
                addr = ".".join(str(b) for b in rdata)
            else:
                rdata = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 3)))
                addr = None
            answers.append({
                "type": rr_type,
                "class": RR_CLASS_IN,
                "ttl": ttl,
                "rdata_length": len(rdata),
                "type_name": "nb",
                "address": addr,
            })
        else:
            rr_type = rng.choice(_NBNS_UNKNOWN_TYPES)
            rdata = bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 6)))
            answers.append({
                "type": rr_type,
                "class": RR_CLASS_IN,
                "ttl": ttl,
                "rdata_length": len(rdata),
                "type_name": f"0x{rr_type:04x}",
            })

        body += struct.pack("!HHIH", rr_type, RR_CLASS_IN, ttl, len(rdata))
        body += rdata

    packet = header + body
    expected = {
        "transaction_id": transaction_id,
        "flags": {
            "raw": flags_raw,
            "is_response": is_response,
            "opcode": opcode,
            "rcode": rcode,
            "rcode_name": _NBNS_RCODE_ORACLE.get(rcode, f"unknown ({rcode})"),
        },
        "question_count": qdcount,
        "answer_count": ancount,
        "authority_count": 0,
        "additional_count": 0,
        "answers": answers,
        "mac": top_mac,
        "names": top_names,
        "num_names": len(top_names),
    }
    return packet, expected


def test_parse_nbns_response_matches_independent_oracle_random() -> None:
    """Full-message assembly matches an independent from-scratch builder.

    Builds random NBNS responses (random transaction id / flags / opcode /
    rcode, optional question, and a mix of NBSTAT / NB / unknown answers with
    DNS compression pointers) and asserts every parsed field matches the
    oracle: header counts, flags, per-answer records, names, suffixes, flags,
    MAC and NB addresses.
    """
    rng = random.Random(_NBNS_SEED)
    for _ in range(2000):
        packet, expected = _oracle_build_nbns_message(rng)
        result = _parse_nbns_response(packet)
        assert result == expected


def test_parse_nbns_response_hostile_bytes_never_crash() -> None:
    """Arbitrary byte buffers raise only ValueError or return a dict; no
    hang, crash, or other exception type.
    """
    rng = random.Random(_NBNS_SEED + 1)
    for _ in range(3000):
        n = rng.randint(0, 80)
        data = bytes(rng.randint(0, 255) for _ in range(n))
        try:
            result = _parse_nbns_response(data)
        except ValueError:
            continue
        assert isinstance(result, dict)
        assert set(result) == {
            "transaction_id",
            "flags",
            "question_count",
            "answer_count",
            "authority_count",
            "additional_count",
            "answers",
            "mac",
            "names",
            "num_names",
        }
        assert isinstance(result["answers"], list)
        assert result["mac"] is None or isinstance(result["mac"], str)
        assert isinstance(result["names"], list)
        assert result["num_names"] == len(result["names"])


# ---------------------------------------------------------------------------
# _send_recv
# ---------------------------------------------------------------------------


def test_send_recv_with_connector_returns_data() -> None:
    def connector(host, port, request, timeout):
        return b"response", None

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0, connector=connector)
    assert data == b"response"
    assert err is None


def test_send_recv_with_connector_returns_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0, connector=connector)
    assert data is None
    assert err == "timeout"


def test_send_recv_connector_receives_arguments() -> None:
    captured: dict[str, object] = {}

    def connector(host, port, request, timeout):
        captured.update(host=host, port=port, request=request, timeout=timeout)
        return None, "timeout"

    _send_recv("192.168.1.1", 137, b"req-bytes", 2.5, connector=connector)
    assert captured == {
        "host": "192.168.1.1",
        "port": 137,
        "request": b"req-bytes",
        "timeout": 2.5,
    }


def test_send_recv_connector_failure_is_reported() -> None:
    """A connector that fails is reported, never raised."""

    def connector(host, port, request, timeout):
        raise RuntimeError("hostile transport")

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0, connector=connector)
    assert data is None
    assert err is not None
    assert "hostile transport" in err


def test_send_recv_socket_creation_failure_is_reported(monkeypatch) -> None:
    """A socket that cannot even be created is reported, never raised."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda host, port, type, proto: [
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ])
    monkeypatch.setattr("ethscan.netbios.socket.socket", boom)

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "hostile transport" in err


def test_send_recv_socket_creation_failure_of_unnamed_type_is_reported(monkeypatch) -> None:
    """A socket that cannot be created (ValueError) is reported, never raised."""

    def boom(*args, **kwargs):
        raise ValueError("hostile transport")

    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda host, port, type, proto: [
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ])
    monkeypatch.setattr("ethscan.netbios.socket.socket", boom)

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "hostile transport" in err


def test_send_recv_socket_failure_is_reported(monkeypatch) -> None:
    """A transport failure of an unnamed type is reported, never raised."""

    class _BoomSocket:
        def settimeout(self, timeout):
            pass

        def sendto(self, data, address):
            raise RuntimeError("hostile transport")

        def recvfrom(self, size):
            return b"", None

        def close(self):
            pass

    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda host, port, type, proto: [
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ])
    monkeypatch.setattr("ethscan.netbios.socket.socket", lambda *a, **kw: _BoomSocket())

    data, err = _send_recv("h", DEFAULT_PORT, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "hostile transport" in err


# ---------------------------------------------------------------------------
# _send_recv - IPv6 family-aware resolution
# ---------------------------------------------------------------------------


def test_send_recv_ipv6_uses_af_inet6(monkeypatch) -> None:
    """Non-connector path: ::1 resolves to AF_INET6 socket."""
    captured = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def sendto(self, data, sockaddr):
            captured["sendto_sockaddr"] = sockaddr

        def recvfrom(self, size):
            return (_full_response(mac=b"\xaa\xbb\xcc\xdd\xee\xff"), ("::1", 137))

        def close(self):
            pass

    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda host, port, type, proto: [
        (socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("::1", 137, 0, 0))
    ])
    monkeypatch.setattr("ethscan.netbios.socket.socket", FakeSock)

    data, err = _send_recv("::1", 137, b"req", 1.0)
    assert data is not None
    assert err is None
    assert captured["family"] == socket.AF_INET6
    assert captured["sendto_sockaddr"][0] == "::1"


def test_send_recv_ipv4_uses_af_inet(monkeypatch) -> None:
    """Non-connector path: 127.0.0.1 resolves to AF_INET socket."""
    captured = {}

    class FakeSock:
        def __init__(self, family, socktype, proto):
            captured["family"] = family
            captured["socktype"] = socktype
            captured["proto"] = proto

        def settimeout(self, timeout):
            pass

        def sendto(self, data, sockaddr):
            captured["sendto_sockaddr"] = sockaddr

        def recvfrom(self, size):
            return (_full_response(mac=b"\xaa\xbb\xcc\xdd\xee\xff"), ("127.0.0.1", 137))

        def close(self):
            pass

    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda host, port, type, proto: [
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ])
    monkeypatch.setattr("ethscan.netbios.socket.socket", FakeSock)

    data, err = _send_recv("127.0.0.1", 137, b"req", 1.0)
    assert data is not None
    assert err is None
    assert captured["family"] == socket.AF_INET
    assert captured["sendto_sockaddr"][0] == "127.0.0.1"


def test_send_recv_getaddrinfo_failure_is_reported(monkeypatch) -> None:
    """Non-connector path: getaddrinfo failure is reported as error."""
    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda *a, **kw: (_ for _ in ()).throw(OSError("name resolution failed")))

    data, err = _send_recv("invalid-host", 137, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "address resolution failed" in err


def test_send_recv_empty_getaddrinfo_is_reported(monkeypatch) -> None:
    """Non-connector path: empty getaddrinfo result is reported as error."""
    monkeypatch.setattr("ethscan.netbios.socket.getaddrinfo", lambda *a, **kw: [])

    data, err = _send_recv("invalid-host", 137, b"req", 1.0)
    assert data is None
    assert err is not None
    assert "no address found" in err


# ---------------------------------------------------------------------------
# run_netbios
# ---------------------------------------------------------------------------


def test_run_netbios_full_interaction() -> None:
    def connector(host, port, request, timeout):
        return _full_response(mac=b"\xaa\xbb\xcc\xdd\xee\xff"), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["target"] == "192.168.1.100"
    assert results["host"] == "192.168.1.100"
    assert results["port"] == DEFAULT_PORT
    assert results["mac"] == "aa:bb:cc:dd:ee:ff"
    assert results["num_names"] == 5
    assert results["is_server"] is True
    assert results["hostname"] == "MYHOST"
    assert results["is_domain_member"] is True
    assert results["error"] is None
    assert results["queried_name"] == DEFAULT_NAME


def test_run_netbios_timeout_sets_error() -> None:
    def connector(host, port, request, timeout):
        return None, "timeout"

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"] == "node status request failed: timeout"
    assert results["mac"] is None
    assert results["names"] == []


def test_run_netbios_connection_refused() -> None:
    def connector(host, port, request, timeout):
        return None, "[Errno 111] Connection refused"

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"] == "node status request failed: [Errno 111] Connection refused"
    assert results["names"] == []


def test_run_netbios_parse_failure() -> None:
    def connector(host, port, request, timeout):
        return b"\x30\x02\x00", None  # too short / malformed

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"].startswith("response parse failed:")


def test_run_netbios_connector_failure_is_reported() -> None:
    """A failing transport is reported through the error field, not raised."""

    def connector(host, port, request, timeout):
        raise RuntimeError("hostile transport")

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"].startswith("node status request failed:")
    assert "hostile transport" in results["error"]
    assert results["names"] == []


def test_run_netbios_empty_answer_is_reported() -> None:
    """A transport that answers with nothing is reported, not raised."""

    def connector(host, port, request, timeout):
        return None, None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"].startswith("response parse failed:")
    assert results["names"] == []


def test_run_netbios_rcode_error() -> None:
    def connector(host, port, request, timeout):
        return _build_nbstat_response(rcode=3, ancount=0), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["error"].startswith("response rcode 3")
    assert results["names"] == []


def test_run_netbios_not_a_response() -> None:
    def connector(host, port, request, timeout):
        return _build_nbstat_response(is_response=False), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert "not a response" in results["error"]


def test_run_netbios_no_server_when_no_file_service_name() -> None:
    # Only a workstation <00> name, no <20> file server name.
    entries = bytes([1]) + _entry("MYHOST", 0x00, 0x0400) + b"\xaa" * 6 + b"\x00" * 10
    def connector(host, port, request, timeout):
        return _build_nbstat_response(entries=entries), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["is_server"] is False


def test_run_netbios_custom_name() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["request"] = request
        return _full_response(), None

    run_netbios("192.168.1.100", timeout=1.0, name="WORKSTATION", connector=connector)
    request = captured["request"]
    # The queried name should be encoded into the request's question name.
    assert _decode_name_chars(request[13:45])[0] == "WORKSTATION"


def test_run_netbios_custom_suffix() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["request"] = request
        return _full_response(), None

    run_netbios("192.168.1.100", timeout=1.0, name="MYHOST", suffix=0x20, connector=connector)
    request = captured["request"]
    assert _decode_name_chars(request[13:45])[1] == 0x20


def test_run_netbios_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["port"] = port
        return None, "timeout"

    results = run_netbios("192.168.1.100", port=138, timeout=1.0, connector=connector)
    assert captured["port"] == 138
    assert results["port"] == 138


def test_run_netbios_url_target() -> None:
    captured: dict[str, object] = {}

    def connector(host, port, request, timeout):
        captured.update(host=host, port=port)
        return None, "timeout"

    results = run_netbios("netbios://192.168.1.100:138", timeout=1.0, connector=connector)
    assert captured["host"] == "192.168.1.100"
    assert captured["port"] == 138
    assert results["host"] == "192.168.1.100"
    assert results["port"] == 138


def test_run_netbios_name_table_returned_in_results() -> None:
    def connector(host, port, request, timeout):
        return _full_response(mac=b"\xaa\xbb\xcc\xdd\xee\xff"), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    names = results["names"]
    assert any(n["suffix"] == 0x20 and n["service_type"] == "File server service" for n in names)
    suffixes = [n["suffix"] for n in names]
    assert 0x00 in suffixes and 0x20 in suffixes and 0x1E in suffixes


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _full_results() -> dict:
    return {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 137,
        "queried_name": "*",
        "queried_suffix": 0,
        "mac": "aa:bb:cc:dd:ee:ff",
        "names": [
            {
                "name": "MYHOST",
                "suffix": 0,
                "suffix_hex": "0x00",
                "service_type": "Workstation service",
                "flags": {
                    "group": False,
                    "unique": True,
                    "owner_node_type": "B-node",
                    "permanent": False,
                    "transient": True,
                    "active": True,
                    "conflict": False,
                    "deregister": False,
                    "raw": 0x0400,
                },
            },
            {
                "name": "MYHOST",
                "suffix": 32,
                "suffix_hex": "0x20",
                "service_type": "File server service",
                "flags": {
                    "group": False,
                    "unique": True,
                    "owner_node_type": "B-node",
                    "permanent": False,
                    "transient": True,
                    "active": True,
                    "conflict": False,
                    "deregister": False,
                    "raw": 0x0400,
                },
            },
        ],
        "num_names": 2,
        "is_server": True,
        "hostname": "MYHOST",
        "is_domain_member": False,
        "transaction_id": 0x1234,
        "error": None,
    }


def test_format_netbios_report_json() -> None:
    parsed = json.loads(format_netbios_report_json(_full_results()))
    assert parsed["host"] == "192.168.1.100"
    assert parsed["mac"] == "aa:bb:cc:dd:ee:ff"
    assert parsed["is_server"] is True
    assert parsed["num_names"] == 2


def test_format_netbios_report_json_error_case() -> None:
    results = _full_results()
    results["error"] = "node status request failed: timeout"
    results["names"] = []
    results["mac"] = None
    parsed = json.loads(format_netbios_report_json(results))
    assert parsed["error"] == "node status request failed: timeout"


def test_format_netbios_report_markdown_full() -> None:
    output = format_netbios_report_markdown(_full_results())
    assert "# ethscan NetBIOS Report" in output
    assert "**Target:** 192.168.1.100" in output
    assert "**Port:** 137" in output
    assert "**MAC:** aa:bb:cc:dd:ee:ff" in output
    assert "**Names Found:** 2" in output
    assert "## Names" in output
    assert "| MYHOST | 0x00 | Workstation service |" in output
    assert "| MYHOST | 0x20 | File server service |" in output
    assert "## Assessment" in output
    assert "Server:** YES" in output
    assert "**Hostname:** MYHOST" in output


def test_format_netbios_report_markdown_no_names() -> None:
    results = _full_results()
    results["names"] = []
    results["num_names"] = 0
    results["mac"] = None
    results["is_server"] = False
    results["hostname"] = None
    output = format_netbios_report_markdown(results)
    assert "**Names Found:** 0" in output
    assert "Server:** NO" in output


def test_format_netbios_report_markdown_error() -> None:
    results = _full_results()
    results["error"] = "node status request failed: timeout"
    output = format_netbios_report_markdown(results)
    assert "**Error:** node status request failed: timeout" in output


def test_format_netbios_report_markdown_pipe_escaping() -> None:
    results = _full_results()
    results["names"][0]["name"] = "A|B"
    results["mac"] = "aa|bb:cc"
    output = format_netbios_report_markdown(results)
    assert "A\\|B" in output
    assert "aa\\|bb:cc" in output


EXPECTED_HEADER = [
    "target", "host", "port", "mac", "queried_name", "queried_suffix",
    "num_names", "record_type", "name", "suffix", "suffix_hex",
    "service_type", "group", "unique", "owner_node_type", "permanent",
    "transient", "active", "conflict", "deregister", "raw",
    "is_server", "hostname", "is_domain_member", "error",
]


def test_format_netbios_report_csv() -> None:
    output = format_netbios_report_csv(_full_results())
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == EXPECTED_HEADER
    # Summary row first (record_type=summary), then one row per name entry.
    assert rows[1][7] == "summary"
    assert rows[1][0] == "192.168.1.100"
    assert rows[1][3] == "aa:bb:cc:dd:ee:ff"
    assert rows[1][5] == "0"
    assert rows[1][6] == "2"
    assert rows[1][21] == "true"  # is_server
    assert rows[1][22] == "MYHOST"  # hostname
    # Two name entries -> two additional rows (rows[2], rows[3]).
    assert len(rows) == 4
    assert rows[2][7] == "name"
    assert rows[2][8] == "MYHOST"
    assert rows[2][9] == "0"
    assert rows[2][10] == "0x00"
    assert rows[2][11] == "Workstation service"
    assert rows[2][12] == "false"  # group
    assert rows[2][13] == "true"   # unique
    assert rows[2][14] == "B-node"
    assert rows[2][15] == "false"  # permanent
    assert rows[2][16] == "true"   # transient
    assert rows[2][17] == "true"   # active
    assert rows[2][18] == "false"  # conflict
    assert rows[2][19] == "false"  # deregister
    assert rows[2][20] == "1024"
    assert rows[2][21] == ""       # is_server empty on name rows
    assert rows[3][8] == "MYHOST"
    assert rows[3][9] == "32"
    assert rows[3][10] == "0x20"
    assert rows[3][11] == "File server service"


def test_format_netbios_report_csv_one_row_per_name() -> None:
    # Markdown renders a per-name Names table; CSV must NOT collapse names into
    # a single joined cell. Each name entry yields its own row.
    results = _full_results()
    results["names"].append({
        "name": "WORKGROUP", "suffix": 0, "suffix_hex": "0x00",
        "service_type": "Workstation service",
        "flags": {"group": True, "unique": False, "owner_node_type": "P-node",
                  "permanent": True, "transient": False, "active": True,
                  "conflict": False, "deregister": False, "raw": 0x0200},
    })
    results["num_names"] = 3
    output = format_netbios_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == EXPECTED_HEADER
    assert rows[1][7] == "summary"
    assert rows[1][6] == "3"
    name_rows = [r for r in rows[1:] if r[7] == "name"]
    assert len(name_rows) == 3
    # Distinct names, not one joined cell.
    assert {r[8] for r in name_rows} == {"MYHOST", "WORKGROUP"}
    # The group name's group flag is true and unique is false.
    wg = next(r for r in name_rows if r[8] == "WORKGROUP")
    assert wg[12] == "true"   # group
    assert wg[13] == "false"  # unique
    assert wg[14] == "P-node"
    assert wg[15] == "true"   # permanent


def test_format_netbios_report_csv_no_names() -> None:
    results = _full_results()
    results["names"] = []
    results["num_names"] = 0
    results["is_server"] = False
    results["hostname"] = None
    output = format_netbios_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == EXPECTED_HEADER
    assert len(rows) == 2  # header + single summary row
    assert rows[1][7] == "summary"
    assert rows[1][6] == "0"
    assert rows[1][21] == "false"
    assert rows[1][22] == ""


def test_format_netbios_report_csv_commas_in_names() -> None:
    # Per-name rows are CSV-quoted; a comma in a name must not break parsing.
    results = _full_results()
    results["names"][0]["name"] = "HOST,INC"
    output = format_netbios_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    name_rows = [r for r in rows[1:] if r[7] == "name"]
    assert len(name_rows) == 2
    assert name_rows[0][8] == "HOST,INC"


def test_format_netbios_report_csv_error_case() -> None:
    results = _full_results()
    results["error"] = "timeout"
    results["is_server"] = False
    results["hostname"] = None
    results["names"] = []
    results["mac"] = None
    output = format_netbios_report_csv(results)
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[0] == EXPECTED_HEADER
    assert len(rows) == 2
    assert rows[1][7] == "summary"
    assert rows[1][-1] == "timeout"
    assert rows[1][21] == "false"
    assert rows[1][22] == ""
    assert rows[1][3] == ""  # mac empty when None
    assert rows[1][3] == ""  # mac empty when None


def test_format_netbios_report_markdown_empty_name() -> None:
    # A name entry with an empty name hits the "(empty)" fallback (line 615).
    results = _full_results()
    results["names"] = [{"name": "", "suffix": 0, "suffix_hex": "0x00",
                         "service_type": "Workstation service",
                         "flags": {"group": False, "unique": True,
                                   "owner_node_type": "B-node",
                                   "permanent": False, "transient": True,
                                   "active": True, "conflict": False,
                                   "deregister": False, "raw": 0x0400}}]
    results["num_names"] = 1
    results["is_server"] = False
    results["hostname"] = None
    results["is_domain_member"] = False
    output = format_netbios_report_markdown(results)
    assert "| (empty) |" in output


def test_format_netbios_report_markdown_domain_member() -> None:
    # is_domain_member True renders the domain-member assessment line (line 645).
    results = _full_results()
    results["is_domain_member"] = True
    output = format_netbios_report_markdown(results)
    assert "Domain member:" in output and "YES" in output


# Extra coverage for previously-uncovered branches


def test_parse_dns_name_truncated_compression_pointer():
    # offset+1 >= len(data)
    data = b"\xc0"
    with pytest.raises(ValueError):
        from ethscan.netbios import _parse_dns_name
        _parse_dns_name(data, 0)


def test_parse_dns_name_decode_valueerror_fallback():
    # raw bytes that make _decode_name_chars raise
    from ethscan.netbios import _parse_dns_name
    # build one label with invalid length? Instead trigger via decode error by
    # providing a raw label whose decode raises. Simpler: monkey invalid pointer chain
    # Use a label length 1 with byte 0xff (invalid NetBIOS encoding -> ValueError)
    data = bytes([1, 0xFF, 0])
    name, _ = _parse_dns_name(data, 0)
    assert isinstance(name, str)


def test_skip_question_truncated():
    from ethscan.netbios import _skip_question
    with pytest.raises(ValueError):
        _skip_question(b"\x20A" * 1, 0, 1)


def test_skip_question_truncated_question_record():
    # A valid question name followed by fewer than 4 type/class bytes.
    from ethscan.netbios import _skip_question
    with pytest.raises(ValueError):
        _skip_question(b"\x05hello\x00\x00\x00", 0, 1)


def test_send_recv_real_and_errors():
    import socket as _s
    from unittest.mock import patch

    from ethscan.netbios import _send_recv
    # success
    class FakeSock:
        def __init__(self): pass
        def settimeout(self, t): pass
        def sendto(self, req, addr): pass
        def recvfrom(self, n): return (b"data", ("h", 1))
        def close(self): pass
    with patch("ethscan.netbios.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ]):
        with patch("ethscan.netbios.socket.socket", return_value=FakeSock()):
            data, err = _send_recv("h", 137, b"req", 1.0)
            assert data == b"data" and err is None
    # timeout
    class TimeoutSock(FakeSock):
        def recvfrom(self, n): raise _s.timeout()
    with patch("ethscan.netbios.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ]):
        with patch("ethscan.netbios.socket.socket", return_value=TimeoutSock()):
            data, err = _send_recv("h", 137, b"req", 1.0)
            assert data is None and err == "timeout"
    # oserror
    class ErrSock(FakeSock):
        def recvfrom(self, n): raise OSError("boom")
    with patch("ethscan.netbios.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", 137))
    ]):
        with patch("ethscan.netbios.socket.socket", return_value=ErrSock()):
            data, err = _send_recv("h", 137, b"req", 1.0)
            assert err == "boom"


# ---------------------------------------------------------------------------
# A hostile answer: a name that is too short to be a first-level name
# ---------------------------------------------------------------------------


def _short_name_response() -> bytes:
    """Build an NBNS response whose question name is 2 bytes long.

    The name is even in length, so it passes the parity check, but it holds
    fewer than the 16 bytes a first-level name needs.
    """
    header = struct.pack("!HHHHHH", 0x1234, 0x8500, 1, 0, 0, 0)
    question = b"\x02AB\x00" + struct.pack("!HH", RR_TYPE_NBSTAT, RR_CLASS_IN)
    return header + question


def test_parse_dns_name_short_name_is_reported_as_text() -> None:
    """A name that is too short to be first-level encoded is reported as text."""
    name, offset = _parse_dns_name(b"\x02AB\x00", 0)
    assert name == "AB"
    assert offset == 4


def test_parse_nbns_response_short_question_name_does_not_raise() -> None:
    """A short question name is parsed, it does not raise an IndexError."""
    parsed = _parse_nbns_response(_short_name_response())
    assert parsed["question_count"] == 1
    assert parsed["answer_count"] == 0
    assert parsed["names"] == []


def test_run_netbios_hostile_short_name_does_not_leak_a_traceback() -> None:
    """A hostile answer is answered with a result, not with a traceback."""

    def connector(host, port, request, timeout):
        return _short_name_response(), None

    results = run_netbios("192.168.1.100", timeout=1.0, connector=connector)
    assert results["names"] == []
    assert results["mac"] is None


def test_netbios_command_hostile_short_name_does_not_leak_a_traceback() -> None:
    """The command line answers a hostile packet without leaking a traceback."""
    from unittest.mock import patch

    from click.testing import CliRunner

    from ethscan import netbios
    from ethscan.cli import cli

    runner = CliRunner()
    with patch.object(
        netbios, "_send_recv", return_value=(_short_name_response(), None)
    ):
        result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100"])
    exc = result.exception
    assert exc is None or isinstance(exc, SystemExit), (
        f"the netbios command leaked a traceback: {type(exc).__name__}: {exc}"
    )
    assert result.exit_code == 0


def test_format_netbios_report_markdown_non_dict() -> None:
    """Cover line 621: a non-dict payload is reset to {} instead of raising."""
    hostiles: tuple[object, ...] = (None, [], "not a dict", 123, ("tuple",), {"nested": {"bad": "data"}})
    for hostile in hostiles:
        out = format_netbios_report_markdown(hostile)  # type: ignore[arg-type]
        assert isinstance(out, str)


def test_format_netbios_report_csv_non_dict() -> None:
    """Cover line 708: a non-dict payload is reset to {} instead of raising."""
    hostiles: tuple[object, ...] = (None, [], "not a dict", 123, ("tuple",), {"nested": {"bad": "data"}})
    for hostile in hostiles:
        out = format_netbios_report_csv(hostile)  # type: ignore[arg-type]
        assert isinstance(out, str)
