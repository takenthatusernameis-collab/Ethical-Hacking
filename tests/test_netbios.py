"""Tests for the ethscan netbios module."""

import csv
import io
import json
import struct

import pytest

from ethscan.netbios import (
    DEFAULT_PORT,
    DEFAULT_NAME,
    DEFAULT_SUFFIX,
    DEFAULT_TIMEOUT,
    RR_CLASS_IN,
    RR_TYPE_NB,
    RR_TYPE_NBSTAT,
    RCODE_NAMES,
    SUFFIX_SERVICE_TYPES,
    _build_nbns_query,
    _decode_name_chars,
    _encode_name_chars,
    _encode_qname,
    _normalize_target,
    _parse_dns_name,
    _parse_name_flags,
    _parse_nbtstat_rdata,
    _parse_nbns_response,
    _send_recv,
    format_netbios_report_csv,
    format_netbios_report_json,
    format_netbios_report_markdown,
    run_netbios,
)


# ---------------------------------------------------------------------------
# Test helpers to build well-formed NBNS messages
# ---------------------------------------------------------------------------


def _entry(name: str, suffix: int, flags: int) -> bytes:
    """Build an 18-byte NBSTAT NODE_NAME entry (15 name + 1 suffix + 2 flags)."""
    raw_name = name.upper().encode("ascii", "replace").ljust(15, b" ")
    return raw_name + bytes([suffix]) + struct.pack("!H", flags)


def _build_nbstat_response(
    transaction_id: int = 0x1234,
    qdname: bytes = None,
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


def test_decode_name_chars_invalid_char_raises() -> None:
    with pytest.raises(ValueError):
        _decode_name_chars(b"\x00" * 32)  # 'A'-1 is invalid nibble


def test_decode_name_chars_odd_length_raises() -> None:
    with pytest.raises(ValueError):
        _decode_name_chars(b"A" * 31)


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
    captured = {}

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
    captured = {}

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
    wg = [r for r in name_rows if r[8] == "WORKGROUP"][0]
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
    name, off = _parse_dns_name(data, 0)
    assert isinstance(name, str)


def test_skip_question_truncated():
    from ethscan.netbios import _skip_question
    with pytest.raises(ValueError):
        _skip_question(b"\x20A" * 1, 0, 1)


def test_send_recv_real_and_errors():
    import socket as _s
    from ethscan.netbios import _send_recv
    from unittest.mock import patch
    # success
    class FakeSock:
        def __init__(self): pass
        def settimeout(self, t): pass
        def sendto(self, req, addr): pass
        def recvfrom(self, n): return (b"data", ("h", 1))
        def close(self): pass
    with patch("ethscan.netbios.socket.socket", return_value=FakeSock()):
        data, err = _send_recv("h", 137, b"req", 1.0)
        assert data == b"data" and err is None
    # timeout
    class TimeoutSock(FakeSock):
        def recvfrom(self, n): raise _s.timeout()
    with patch("ethscan.netbios.socket.socket", return_value=TimeoutSock()):
        data, err = _send_recv("h", 137, b"req", 1.0)
        assert data is None and err == "timeout"
    # oserror
    class ErrSock(FakeSock):
        def recvfrom(self, n): raise OSError("boom")
    with patch("ethscan.netbios.socket.socket", return_value=ErrSock()):
        data, err = _send_recv("h", 137, b"req", 1.0)
        assert err == "boom"
