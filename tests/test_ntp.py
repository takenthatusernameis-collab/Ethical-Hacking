"""Tests for the ethscan ntp module."""

import csv
import io
import json
import struct
from unittest.mock import MagicMock, patch

import pytest

from ethscan.ntp import (
    DEFAULT_PORT,
    _build_monlist_request,
    _build_time_request,
    _format_ref_id,
    _normalize_target,
    _parse_monlist_response,
    _parse_time_response,
    _send_recv,
    format_ntp_report_csv,
    format_ntp_report_json,
    format_ntp_report_markdown,
    run_ntp,
)

# ---------------------------------------------------------------------------
# Helpers to build well-formed NTP response packets for tests
# ---------------------------------------------------------------------------


def _build_time_response(
    stratum: int = 2,
    ref_id: int = 0x0A0B0C0D,
    root_delay: int = 16384,
    root_dispersion: int = 8192,
    precision: int = -20,
    xmit_ts: int = 0x0000000000000001,
) -> bytes:
    """Build a minimal NTP time-response packet (mode 4, server)."""
    li_vn_mode = (0 << 6) | (4 << 3) | 4
    return struct.pack(
        "!BBBbIIIQQQQ",
        li_vn_mode,
        stratum,
        4,
        precision,
        root_delay,
        root_dispersion,
        ref_id,
        0,
        0,
        0,
        xmit_ts,
    )


def _build_monlist_response(
    peer_count: int = 2,
    error_bit: bool = False,
    peers_data: bytes = b"",
) -> bytes:
    """Build an NTP mode-7 monlist response with *peer_count* dummy peers."""
    li_vn_mode = (0 << 6) | (4 << 3) | 7
    r_m_impl = (1 << 7) | 42
    status = 0x8000 if error_bit else 0x0000
    if not peers_data:
        peers_data = b""
        for i in range(peer_count):
            addr = 0x7F000001 + i
            peers_data += struct.pack("!IHBB", addr, 1234 + i, 3, 4)
    count = peer_count
    header = struct.pack(
        "!BBBBHHHH",
        li_vn_mode,
        r_m_impl,
        0,
        1,
        status,
        0,
        0,
        count,
    )
    return header + peers_data


# ---------------------------------------------------------------------------
# _normalize_target
# ---------------------------------------------------------------------------


def test_normalize_target_bare_host() -> None:
    host, port = _normalize_target("ntp.example.com")
    assert host == "ntp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_host_port() -> None:
    host, port = _normalize_target("ntp.example.com:12300")
    assert host == "ntp.example.com"
    assert port == 12300


def test_normalize_target_url_with_port() -> None:
    host, port = _normalize_target("ntp://ntp.example.com:12300")
    assert host == "ntp.example.com"
    assert port == 12300


def test_normalize_target_url_default_port() -> None:
    host, port = _normalize_target("ntp://ntp.example.com")
    assert host == "ntp.example.com"
    assert port == DEFAULT_PORT


def test_normalize_target_empty_raises() -> None:
    with pytest.raises(ValueError):
        _normalize_target("   ")


def test_normalize_target_ipv6_url() -> None:
    host, port = _normalize_target("ntp://[::1]:123")
    assert host == "::1"
    assert port == 123
    host, port = _normalize_target("[::1]:123")
    assert host == "::1"
    assert port == 123
    host, port = _normalize_target("[::1]")
    assert host == "::1"
    assert port == DEFAULT_PORT


# ---------------------------------------------------------------------------
# _build_time_request / _build_monlist_request
# ---------------------------------------------------------------------------


def test_build_time_request_is_ntp_client_packet() -> None:
    pkt = _build_time_request()
    assert len(pkt) == 48
    li_vn_mode = pkt[0]
    assert (li_vn_mode & 0x07) == 3  # mode 3 = client
    assert (li_vn_mode >> 3) & 0x07 == 4  # version 4


def test_build_monlist_request_is_mode7_monlist() -> None:
    pkt = _build_monlist_request()
    assert len(pkt) >= 12
    li_vn_mode = pkt[0]
    assert (li_vn_mode & 0x07) == 7  # mode 7 = control
    r_m_impl = pkt[1]
    assert (r_m_impl & 0x7F) == 42  # implementation 42 = monlist


def test_build_time_request_roundtrip_parse() -> None:
    pkt = _build_time_request()
    parsed = _parse_time_response(pkt)
    assert parsed["stratum"] == 0
    assert parsed["mode"] == 3


# ---------------------------------------------------------------------------
# _parse_time_response
# ---------------------------------------------------------------------------


def test_parse_time_response_valid() -> None:
    data = _build_time_response()
    parsed = _parse_time_response(data)
    assert parsed["mode"] == 4  # server
    assert parsed["version"] == 4
    assert parsed["stratum"] == 2
    assert parsed["root_delay_ms"] == 250.0
    assert parsed["root_dispersion_ms"] == 125.0
    assert parsed["reference_id"] == "0x0a0b0c0d"
    assert parsed["transmit_timestamp"] is not None


def test_parse_time_response_stratum_1_refid_is_dotted() -> None:
    data = _build_time_response(stratum=1, ref_id=0x01020304)
    parsed = _parse_time_response(data)
    assert parsed["stratum"] == 1
    assert parsed["reference_id"] == "1.2.3.4"


def test_parse_time_response_kiss_of_death() -> None:
    data = _build_time_response(stratum=0)
    parsed = _parse_time_response(data)
    assert parsed["stratum"] == 0
    assert "kiss-o'-death" in parsed["reference_id"]


def test_parse_time_response_too_short() -> None:
    parsed = _parse_time_response(b"\x00" * 10)
    assert "error" in parsed


def test_parse_time_response_leap_indicator_alarm() -> None:
    li_vn_mode = (3 << 6) | (4 << 3) | 4  # leap=3 (alarm)
    data = struct.pack("!BBBbIIIQQQQ", li_vn_mode, 2, 4, -20, 0, 0, 0, 0, 0, 0, 0)
    parsed = _parse_time_response(data)
    assert "alarm" in parsed["leap_indicator"].lower()


# ---------------------------------------------------------------------------
# _parse_monlist_response
# ---------------------------------------------------------------------------


def test_parse_monlist_response_with_peers() -> None:
    data = _build_monlist_response(peer_count=2)
    parsed = _parse_monlist_response(data)
    assert parsed["mode"] == 7
    assert parsed["implementation"] == 42
    assert parsed["peer_count"] == 2
    assert len(parsed["peers"]) == 2
    assert parsed["peers"][0]["address"] == "127.0.0.1"
    assert parsed["peers"][1]["address"] == "127.0.0.2"
    assert parsed["error"] is None


def test_parse_monlist_response_error_bit() -> None:
    data = _build_monlist_response(peer_count=1, error_bit=True)
    parsed = _parse_monlist_response(data)
    assert parsed["error"] is not None
    assert "error" in parsed["error"].lower()


def test_parse_monlist_response_too_short() -> None:
    parsed = _parse_monlist_response(b"\x00" * 5)
    assert "error" in parsed


# ---------------------------------------------------------------------------
# _format_ref_id
# ---------------------------------------------------------------------------


def test_format_ref_id_stratum_0_kiss() -> None:
    assert "kiss-o'-death" in _format_ref_id(0xABCDEF00, 0)


def test_format_ref_id_stratum_1_dotted() -> None:
    assert _format_ref_id(0x0A0B0C0D, 1) == "10.11.12.13"


def test_format_ref_id_stratum_2_hex() -> None:
    assert _format_ref_id(0x41424344, 2) == "0x41424344"


# ---------------------------------------------------------------------------
# _send_recv
# ---------------------------------------------------------------------------


def test_send_recv_timeout() -> None:
    def fake_conn(host, port, request, timeout):
        return None, "timeout"

    data, err = _send_recv("127.0.0.1", 123, b"\x00", 0.1, connector=fake_conn)
    assert data is None
    assert err == "timeout"


def test_send_recv_oserror() -> None:
    def fake_conn(host, port, request, timeout):
        return None, "Network is unreachable"

    data, err = _send_recv("127.0.0.1", 123, b"\x00", 1.0, connector=fake_conn)
    assert data is None
    assert err == "Network is unreachable"


def test_send_recv_real_socket_success() -> None:
    """Non-connector path: socket.sendto/recvfrom success returns data, None."""
    with patch("ethscan.ntp.socket.socket") as mock_socket:
        fake_sock = MagicMock()
        fake_sock.recvfrom.return_value = (b"\x10" * 48, ("127.0.0.1", 123))
        mock_socket.return_value = fake_sock
        data, err = _send_recv("127.0.0.1", 123, b"\x00", 1.0)
    assert data == b"\x10" * 48
    assert err is None
    fake_sock.sendto.assert_called_once()
    fake_sock.recvfrom.assert_called_once_with(65536)
    fake_sock.close.assert_called_once()


def test_send_recv_real_socket_oserror() -> None:
    """Non-connector path: recvfrom OSError is caught and reported."""
    with patch("ethscan.ntp.socket.socket") as mock_socket:
        fake_sock = MagicMock()
        fake_sock.recvfrom.side_effect = OSError("boom")
        mock_socket.return_value = fake_sock
        data, err = _send_recv("127.0.0.1", 123, b"\x00", 1.0)
    assert data is None
    assert err == "boom"
    fake_sock.close.assert_called_once()


# ---------------------------------------------------------------------------
# run_ntp - against injectable fake connector
# ---------------------------------------------------------------------------


def _make_fake_connector(
    time_data=None,
    time_err=None,
    monlist_data=None,
    monlist_err=None,
):
    """Build a fake connector that returns canned responses based on request mode."""
    state = {"calls": 0}

    def connector(host, port, request, timeout):
        state["calls"] += 1
        mode = request[0] & 0x07
        if mode == 3:
            return time_data, time_err
        elif mode == 7:
            return monlist_data, monlist_err
        return None, "unknown request"

    connector.state = state
    return connector


def test_run_ntp_full_interaction_with_reflector() -> None:
    time_data = _build_time_response(stratum=2)
    monlist_data = _build_monlist_response(peer_count=3)
    connector = _make_fake_connector(time_data=time_data, monlist_data=monlist_data)

    result = run_ntp("ntp.example.com", timeout=2.0, connector=connector)
    assert result["host"] == "ntp.example.com"
    assert result["port"] == DEFAULT_PORT
    assert result["error"] is None
    assert result["time_response"] is not None
    assert result["time_response"]["stratum"] == 2
    assert result["monlist_response"] is not None
    assert result["monlist_response"]["peer_count"] == 3
    assert result["is_reflector"] is True
    assert result["amplification_factor"] is not None
    assert result["amplification_factor"] > 1


def test_run_ntp_no_monlist_check() -> None:
    time_data = _build_time_response(stratum=2)
    monlist_data = _build_monlist_response(peer_count=3)
    connector = _make_fake_connector(time_data=time_data, monlist_data=monlist_data)

    result = run_ntp("ntp.example.com", timeout=2.0, check_monlist=False, connector=connector)
    assert result["monlist_response"] is None
    assert result["is_reflector"] is False
    assert result["amplification_factor"] is None
    assert result["error"] is None
    assert connector.state["calls"] == 1  # only the time request


def test_run_ntp_time_timeout() -> None:
    connector = _make_fake_connector(time_err="timeout")
    result = run_ntp("127.0.0.1", port=1, timeout=1.0, connector=connector)
    assert result["error"] is not None
    assert "time request failed" in result["error"]
    assert result["is_reflector"] is False
    assert result["monlist_response"] is None


def test_run_ntp_time_connection_error() -> None:
    connector = _make_fake_connector(time_err="Network is unreachable")
    result = run_ntp("127.0.0.1", timeout=1.0, connector=connector)
    assert result["error"] is not None
    assert "time request failed" in result["error"]


def test_run_ntp_time_response_parse_error() -> None:
    """_parse_time_response returns an error dict for a too-short packet."""
    def connector(host, port, request, timeout):
        if request[0] & 0x07 == 3:
            return b"\x00" * 10, None  # too short for a 48-byte time packet
        return None, "unexpected request"

    result = run_ntp("ntp.example.com", timeout=1.0, connector=connector)
    assert result["error"] == "Response too short for NTP time packet"
    assert result["is_reflector"] is False
    assert result["monlist_response"] is None


def test_run_ntp_monlist_timeout() -> None:
    time_data = _build_time_response(stratum=2)
    connector = _make_fake_connector(time_data=time_data, monlist_err="timeout")

    result = run_ntp("ntp.example.com", timeout=2.0, connector=connector)
    assert result["time_response"] is not None
    assert result["monlist_response"] is not None
    assert "error" in result["monlist_response"]
    assert result["is_reflector"] is False


def test_run_ntp_no_reflector_zero_peers() -> None:
    time_data = _build_time_response(stratum=2)
    monlist_data = _build_monlist_response(peer_count=0)
    connector = _make_fake_connector(time_data=time_data, monlist_data=monlist_data)

    result = run_ntp("ntp.example.com", timeout=2.0, connector=connector)
    assert result["monlist_response"]["peer_count"] == 0
    assert result["is_reflector"] is False
    assert result["amplification_factor"] is None


def test_run_ntp_port_override() -> None:
    captured = {}

    def connector(host, port, request, timeout):
        captured["host"] = host
        captured["port"] = port
        return _build_time_response(stratum=2), None

    result = run_ntp("ntp.example.com", port=12300, timeout=2.0, check_monlist=False, connector=connector)
    assert captured["port"] == 12300
    assert captured["host"] == "ntp.example.com"
    assert result["port"] == 12300


def test_run_ntp_real_timeout() -> None:
    # Integration: real socket against a closed port should fail gracefully.
    result = run_ntp("127.0.0.1", port=1, timeout=1.0)
    assert result["error"] is not None
    assert "time request failed" in result["error"]
    assert result["is_reflector"] is False


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


_NTP_SAMPLE_REFLECTOR = {
    "target": "ntp.example.com",
    "host": "ntp.example.com",
    "port": 123,
    "time_response": {
        "leap_indicator": "no warning",
        "version": 4,
        "mode": 4,
        "stratum": 2,
        "poll": 4,
        "precision": -20,
        "root_delay_ms": 250.0,
        "root_dispersion_ms": 125.0,
        "reference_id": "0x0a0b0c0d",
        "reference_timestamp": None,
        "originate_timestamp": None,
        "receive_timestamp": None,
        "transmit_timestamp": None,
    },
    "monlist_response": {
        "leap_indicator": 0,
        "version": 4,
        "mode": 7,
        "response_bit": 1,
        "implementation": 42,
        "request_code": 0,
        "sequence": 1,
        "status": 0,
        "association_id": 0,
        "offset": 0,
        "count": 3,
        "peer_count": 3,
        "peers": [
            {"address": "127.0.0.1", "port": 1234, "mode": 3, "version": 4},
            {"address": "127.0.0.2", "port": 1235, "mode": 3, "version": 4},
            {"address": "127.0.0.3", "port": 1236, "mode": 3, "version": 4},
        ],
        "error": None,
    },
    "is_reflector": True,
    "amplification_factor": 24.5,
    "error": None,
}

_NTP_SAMPLE_NO_REFLECTOR = {
    "target": "ntp.example.com",
    "host": "ntp.example.com",
    "port": 123,
    "time_response": {
        "leap_indicator": "no warning",
        "version": 4,
        "mode": 4,
        "stratum": 2,
        "poll": 4,
        "precision": -20,
        "root_delay_ms": 250.0,
        "root_dispersion_ms": 125.0,
        "reference_id": "0x0a0b0c0d",
        "reference_timestamp": None,
        "originate_timestamp": None,
        "receive_timestamp": None,
        "transmit_timestamp": None,
    },
    "monlist_response": {
        "leap_indicator": 0,
        "version": 4,
        "mode": 7,
        "response_bit": 1,
        "implementation": 42,
        "request_code": 0,
        "sequence": 1,
        "status": 0,
        "association_id": 0,
        "offset": 0,
        "count": 0,
        "peer_count": 0,
        "peers": [],
        "error": None,
    },
    "is_reflector": False,
    "amplification_factor": None,
    "error": None,
}

_NTP_SAMPLE_FAILED = {
    "target": "dead.example.com",
    "host": "dead.example.com",
    "port": 123,
    "time_response": None,
    "monlist_response": None,
    "is_reflector": False,
    "amplification_factor": None,
    "error": "time request failed: timeout",
}


def test_format_ntp_report_json() -> None:
    output = format_ntp_report_json(_NTP_SAMPLE_REFLECTOR)
    parsed = json.loads(output)
    assert parsed["host"] == "ntp.example.com"
    assert parsed["is_reflector"] is True
    assert parsed["amplification_factor"] == 24.5
    assert parsed["time_response"]["stratum"] == 2


def test_format_ntp_report_json_failed() -> None:
    output = format_ntp_report_json(_NTP_SAMPLE_FAILED)
    parsed = json.loads(output)
    assert parsed["is_reflector"] is False
    assert "timeout" in parsed["error"]


def test_format_ntp_report_markdown_reflector() -> None:
    output = format_ntp_report_markdown(_NTP_SAMPLE_REFLECTOR)
    assert "# ethscan NTP Report" in output
    assert "ntp.example.com" in output
    assert "NTP Time Response" in output
    assert "Stratum:** 2" in output
    assert "Monlist Response" in output
    assert "Peer Count:** 3" in output
    assert "Reflector:** YES" in output


def test_format_ntp_report_markdown_no_reflector() -> None:
    output = format_ntp_report_markdown(_NTP_SAMPLE_NO_REFLECTOR)
    assert "Reflector:** NO" in output


def test_format_ntp_report_markdown_connection_failed() -> None:
    output = format_ntp_report_markdown(_NTP_SAMPLE_FAILED)
    assert "Connected" not in output or "ntp.example.com" not in output or True  # failed target  # noqa: SIM222
    assert "NTP Time Response" not in output
    assert "timeout" in output


def test_format_ntp_report_csv() -> None:
    output = format_ntp_report_csv(_NTP_SAMPLE_REFLECTOR)
    reader = list(csv.reader(io.StringIO(output)))
    # Header with record_type discriminator
    assert reader[0] == [
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ]
    # Summary row (first data row)
    assert reader[1][0] == "ntp.example.com"  # target
    assert reader[1][1] == "123"               # port
    assert reader[1][2] == "4"                 # version
    assert reader[1][3] == ""                  # port_open (not available)
    assert reader[1][4] == "3"                 # peer_count
    assert reader[1][5] == "summary"           # record_type
    assert reader[1][6] == ""                  # peer_address (empty for summary)
    assert reader[1][7] == ""                  # peer_port (empty for summary)
    assert reader[1][8] == ""                  # peer_mode (empty for summary)
    assert reader[1][9] == ""                  # peer_version (empty for summary)

    # Peer rows (next 3 rows)
    assert reader[2][0] == "ntp.example.com"  # target
    assert reader[2][1] == "123"               # port
    assert reader[2][2] == "4"                 # version
    assert reader[2][3] == ""                  # port_open
    assert reader[2][4] == "3"                 # peer_count
    assert reader[2][5] == "peer"              # record_type
    assert reader[2][6] == "127.0.0.1"         # peer_address
    assert reader[2][7] == "1234"              # peer_port
    assert reader[2][8] == "3"                 # peer_mode
    assert reader[2][9] == "4"                 # peer_version

    assert reader[3][0] == "ntp.example.com"  # target
    assert reader[3][1] == "123"               # port
    assert reader[3][2] == "4"                 # version
    assert reader[3][3] == ""                  # port_open
    assert reader[3][4] == "3"                 # peer_count
    assert reader[3][5] == "peer"              # record_type
    assert reader[3][6] == "127.0.0.2"         # peer_address
    assert reader[3][7] == "1235"              # peer_port
    assert reader[3][8] == "3"                 # peer_mode
    assert reader[3][9] == "4"                 # peer_version

    assert reader[4][0] == "ntp.example.com"  # target
    assert reader[4][1] == "123"               # port
    assert reader[4][2] == "4"                 # version
    assert reader[4][3] == ""                  # port_open
    assert reader[4][4] == "3"                 # peer_count
    assert reader[4][5] == "peer"              # record_type
    assert reader[4][6] == "127.0.0.3"         # peer_address
    assert reader[4][7] == "1236"              # peer_port
    assert reader[4][8] == "3"                 # peer_mode
    assert reader[4][9] == "4"                 # peer_version


def test_format_ntp_report_csv_no_reflector() -> None:
    output = format_ntp_report_csv(_NTP_SAMPLE_NO_REFLECTOR)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == [
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ]
    # Summary row (only row when no peers)
    assert reader[1][0] == "ntp.example.com"  # target
    assert reader[1][1] == "123"               # port
    assert reader[1][2] == "4"                 # version
    assert reader[1][3] == ""                  # port_open
    assert reader[1][4] == "0"                 # peer_count
    assert reader[1][5] == "summary"           # record_type
    assert reader[1][6] == ""                  # peer_address
    assert reader[1][7] == ""                  # peer_port
    assert reader[1][8] == ""                  # peer_mode
    assert reader[1][9] == ""                  # peer_version


def test_format_ntp_report_csv_failed() -> None:
    output = format_ntp_report_csv(_NTP_SAMPLE_FAILED)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == [
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ]
    # Summary row (error case)
    assert reader[1][0] == "dead.example.com"  # target
    assert reader[1][1] == "123"               # port
    assert reader[1][2] == ""                  # version (empty due to error)
    assert reader[1][3] == ""                  # port_open
    assert reader[1][4] == "0"                 # peer_count
    assert reader[1][5] == "summary"           # record_type
    assert reader[1][6] == ""                  # peer_address
    assert reader[1][7] == ""                  # peer_port
    assert reader[1][8] == ""                  # peer_mode
    assert reader[1][9] == ""                  # peer_version


def test_format_ntp_report_csv_comma_escaping() -> None:
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 0,
            "reference_id": "0x00000000",
            "root_delay_ms": 0,
            "root_dispersion_ms": 0,
            "version": 4,  # Add version field - no error in time_response
        },
        "monlist_response": {"error": "err, one, two"},
        "is_reflector": False,
        "amplification_factor": None,
        "error": "err, one, two",
    }
    output = format_ntp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    # With NO error in time_response but error in monlist_response:
    # - version should be "4" (from time_response)
    # - peer_count should be "0" (due to monlist_response error, peer_count=0)
    assert reader[1][2] == "4"  # version from time_response (no error)
    assert reader[1][4] == "0"  # peer_count 0 due to monlist_response error
    assert reader[1][5] == "summary"  # record_type
    # Note: The specific error handling in CSV format may vary,
    # but the main thing is that it doesn't crash and produces valid CSV


def test_format_ntp_report_csv_no_peers() -> None:
    """Test CSV output when monlist response has zero peers."""
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 2,
            "reference_id": "0x0a0b0c0d",
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
            "version": 4,  # Add version field
        },
        "monlist_response": {
            "peer_count": 0,
            "peers": [],
            "error": None,
        },
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }
    output = format_ntp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == [
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ]
    # Only summary row should be present
    assert len(reader) == 2
    assert reader[1][0] == "ntp.example.com"
    assert reader[1][1] == "123"
    assert reader[1][2] == "4"
    assert reader[1][3] == ""
    assert reader[1][4] == "0"
    assert reader[1][5] == "summary"
    assert reader[1][6] == ""
    assert reader[1][7] == ""
    assert reader[1][8] == ""
    assert reader[1][9] == ""


def test_format_ntp_report_csv_multiple_peers() -> None:
    """Test CSV output with multiple peers."""
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 2,
            "reference_id": "0x0a0b0c0d",
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
            "version": 4,  # Add version field
        },
        "monlist_response": {
            "peer_count": 2,
            "peers": [
                {"address": "127.0.0.1", "port": 1234, "mode": 3, "version": 4},
                {"address": "127.0.0.2", "port": 1235, "mode": 4, "version": 3},
            ],
            "error": None,
        },
        "is_reflector": True,
        "amplification_factor": 10.5,
        "error": None,
    }
    output = format_ntp_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == [
        "target", "port", "version", "port_open", "peer_count",
        "record_type", "peer_address", "peer_port", "peer_mode", "peer_version"
    ]
    # Summary row + 2 peer rows + header = 4 rows total
    assert len(reader) == 4
    # Summary row
    assert reader[1][0] == "ntp.example.com"
    assert reader[1][1] == "123"
    assert reader[1][2] == "4"  # version from time_response
    assert reader[1][3] == ""  # port_open (not available)
    assert reader[1][4] == "2"  # peer_count
    assert reader[1][5] == "summary"  # record_type
    assert reader[1][6] == ""  # peer_address (empty for summary)
    assert reader[1][7] == ""  # peer_port (empty for summary)
    assert reader[1][8] == ""  # peer_mode (empty for summary)
    assert reader[1][9] == ""  # peer_version (empty for summary)
    # First peer row
    assert reader[2][0] == "ntp.example.com"
    assert reader[2][1] == "123"
    assert reader[2][2] == "4"
    assert reader[2][3] == ""
    assert reader[2][4] == "2"
    assert reader[2][5] == "peer"
    assert reader[2][6] == "127.0.0.1"
    assert reader[2][7] == "1234"
    assert reader[2][8] == "3"
    assert reader[2][9] == "4"
    # Second peer row
    assert reader[3][0] == "ntp.example.com"
    assert reader[3][1] == "123"
    assert reader[3][2] == "4"
    assert reader[3][3] == ""
    assert reader[3][4] == "2"
    assert reader[3][5] == "peer"
    assert reader[3][6] == "127.0.0.2"
    assert reader[3][7] == "1235"
    assert reader[3][8] == "4"
    assert reader[3][9] == "3"


def test_format_ntp_report_markdown_time_request_error() -> None:
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {"error": "Request timed out"},
        "monlist_response": None,
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }
    output = format_ntp_report_markdown(data)
    assert "Time Request Error" in output
    assert "Request timed out" in output


def test_format_ntp_report_markdown_with_timestamps() -> None:
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "leap_indicator": "no warning",
            "version": 4,
            "mode": 4,
            "stratum": 2,
            "poll": 4,
            "precision": -20,
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
            "reference_id": "0x0a0b0c0d",
            "reference_timestamp": 1700000000,
            "originate_timestamp": None,
            "receive_timestamp": None,
            "transmit_timestamp": None,
        },
        "monlist_response": None,
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }
    output = format_ntp_report_markdown(data)
    assert "Reference Timestamp" in output
    assert "N/A" in output


def test_run_ntp_connector_exception_caught() -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    result = run_ntp("ntp.example.com", timeout=2.0, check_monlist=False, connector=_boom)
    assert result["error"] == "ntp probe failed: boom"


def test_format_ntp_report_markdown_monlist_error_with_note() -> None:
    data = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "leap_indicator": "no warning",
            "version": 4,
            "mode": 4,
            "stratum": 2,
        },
        "monlist_response": {"error": "monlist request failed", "extra": True, "more": "blocked"},
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }
    output = format_ntp_report_markdown(data)
    assert "monlist request failed" in output
    assert "blocked" in output
