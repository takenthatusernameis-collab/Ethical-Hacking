"""Tests for the ethscan trace module."""

import json
import socket
import threading

from ethscan.trace import (
    DEFAULT_PORT,
    ICMP_DEST_UNREACH,
    ICMP_TIME_EXCEEDED,
    PORT_UNREACHABLE_CODE,
    RESP_CONNECTED,
    RESP_NO_RESPONSE,
    RESP_PORT_UNREACHABLE,
    RESP_RST,
    RESP_TIME_EXCEEDED,
    RESP_TIMEOUT,
    _build_ip_header,
    _checksum,
    _icmp_response_label,
    _normalize_host,
    _no_response_result,
    _resolve_host,
    _try_create_raw_socket,
    build_icmp_packet,
    format_trace_report_json,
    format_trace_report_markdown,
    parse_icmp_response,
    probe_ttl,
    run_trace,
)


# ---------------------------------------------------------------------------
# Host normalization
# ---------------------------------------------------------------------------


def test_normalize_host_bare() -> None:
    assert _normalize_host("example.com") == "example.com"


def test_normalize_host_uppercase() -> None:
    assert _normalize_host("Example.COM") == "example.com"


def test_normalize_host_https_url() -> None:
    assert _normalize_host("https://example.com/path") == "example.com"


def test_normalize_host_strips_whitespace() -> None:
    assert _normalize_host("  example.com  ") == "example.com"


def test_normalize_host_with_port() -> None:
    assert _normalize_host("http://example.com:8080") == "example.com"


def test_normalize_host_ip_address() -> None:
    assert _normalize_host("192.168.1.1") == "192.168.1.1"


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


def test_checksum_empty() -> None:
    assert _checksum(b"") == 0xFFFF


def test_checksum_known() -> None:
    result = _checksum(b"hello")
    assert isinstance(result, int)
    assert 0 <= result <= 0xFFFF


def test_checksum_odd_length_pads() -> None:
    result = _checksum(b"abc")
    assert isinstance(result, int)
    assert 0 <= result <= 0xFFFF


# ---------------------------------------------------------------------------
# IP header building
# ---------------------------------------------------------------------------


def test_build_ip_header_length() -> None:
    header = _build_ip_header(
        socket.inet_aton("10.0.0.1"),
        socket.inet_aton("10.0.0.2"),
        socket.IPPROTO_TCP,
        b"\x00" * 20,
    )
    assert len(header) == 20


def test_build_ip_header_version_ihl() -> None:
    header = _build_ip_header(
        socket.inet_aton("10.0.0.1"),
        socket.inet_aton("10.0.0.2"),
        socket.IPPROTO_TCP,
        b"",
    )
    version = (header[0] >> 4) & 0x0F
    ihl = header[0] & 0x0F
    assert version == 4
    assert ihl == 5


def test_build_ip_header_protocol() -> None:
    header = _build_ip_header(
        socket.inet_aton("10.0.0.1"),
        socket.inet_aton("10.0.0.2"),
        socket.IPPROTO_ICMP,
        b"",
    )
    assert header[9] == socket.IPPROTO_ICMP


def test_build_ip_header_addresses() -> None:
    src = socket.inet_aton("10.0.0.1")
    dst = socket.inet_aton("10.0.0.2")
    header = _build_ip_header(src, dst, socket.IPPROTO_TCP, b"")
    assert header[12:16] == src
    assert header[16:20] == dst


# ---------------------------------------------------------------------------
# build_icmp_packet
# ---------------------------------------------------------------------------


def test_build_icmp_packet_time_exceeded_structure() -> None:
    packet = build_icmp_packet(
        ICMP_TIME_EXCEEDED, 0, "192.168.1.1", "10.0.0.1"
    )
    assert len(packet) > 20
    parsed = parse_icmp_response(packet)
    assert parsed["type"] == ICMP_TIME_EXCEEDED
    assert parsed["code"] == 0
    assert parsed["hop_ip"] == "192.168.1.1"
    assert parsed["destination_ip"] == "10.0.0.1"


def test_build_icmp_packet_port_unreachable_structure() -> None:
    packet = build_icmp_packet(
        ICMP_DEST_UNREACH,
        PORT_UNREACHABLE_CODE,
        "203.0.113.5",
        "10.0.0.1",
        orig_src_port=54321,
        orig_dst_port=443,
    )
    parsed = parse_icmp_response(packet)
    assert parsed["type"] == ICMP_DEST_UNREACH
    assert parsed["code"] == PORT_UNREACHABLE_CODE
    assert parsed["hop_ip"] == "203.0.113.5"
    assert parsed["destination_ip"] == "10.0.0.1"
    assert parsed["original_src_port"] == 54321
    assert parsed["original_dst_port"] == 443


# ---------------------------------------------------------------------------
# parse_icmp_response
# ---------------------------------------------------------------------------


def test_parse_icmp_response_too_short() -> None:
    result = parse_icmp_response(b"\x00" * 10)
    assert result["type"] == -1
    assert result["error"] == "packet too short for IP header"


def test_parse_icmp_response_not_ipv4() -> None:
    result = parse_icmp_response(b"\x00" * 20)
    assert result["error"] == "not IPv4"


def test_parse_icmp_response_icmp_truncated() -> None:
    # IP header with IHL=5 (20 bytes) but no ICMP data
    ip_header = _build_ip_header(
        socket.inet_aton("10.0.0.1"),
        socket.inet_aton("10.0.0.2"),
        socket.IPPROTO_ICMP,
        b"",
    )
    result = parse_icmp_response(ip_header)
    assert result["error"] == "ICMP header truncated"
    assert result["hop_ip"] == "10.0.0.1"


def test_parse_icmp_response_time_exceeded() -> None:
    packet = build_icmp_packet(
        ICMP_TIME_EXCEEDED, 0, "192.168.1.1", "10.0.0.1"
    )
    result = parse_icmp_response(packet)
    assert result["type"] == ICMP_TIME_EXCEEDED
    assert result["code"] == 0
    assert result["hop_ip"] == "192.168.1.1"
    assert result["destination_ip"] == "10.0.0.1"
    assert result["original_src_port"] == 12345
    assert result["original_dst_port"] == 80


def test_parse_icmp_response_port_unreachable() -> None:
    packet = build_icmp_packet(
        ICMP_DEST_UNREACH,
        PORT_UNREACHABLE_CODE,
        "203.0.113.5",
        "10.0.0.1",
        orig_src_port=54321,
        orig_dst_port=443,
    )
    result = parse_icmp_response(packet)
    assert result["type"] == ICMP_DEST_UNREACH
    assert result["code"] == PORT_UNREACHABLE_CODE
    assert result["hop_ip"] == "203.0.113.5"
    assert result["destination_ip"] == "10.0.0.1"
    assert result["original_src_port"] == 54321
    assert result["original_dst_port"] == 443


def test_parse_icmp_response_dest_unreach_non_port_code() -> None:
    packet = build_icmp_packet(ICMP_DEST_UNREACH, 0, "203.0.113.5", "10.0.0.1")
    result = parse_icmp_response(packet)
    assert result["type"] == ICMP_DEST_UNREACH
    assert result["code"] == 0
    assert "destination_ip" in result


# ---------------------------------------------------------------------------
# _icmp_response_label
# ---------------------------------------------------------------------------


def test_icmp_response_label_time_exceeded() -> None:
    assert _icmp_response_label({"type": ICMP_TIME_EXCEEDED, "code": 0}) == RESP_TIME_EXCEEDED


def test_icmp_response_label_port_unreachable() -> None:
    assert (
        _icmp_response_label({"type": ICMP_DEST_UNREACH, "code": PORT_UNREACHABLE_CODE})
        == RESP_PORT_UNREACHABLE
    )


def test_icmp_response_label_unknown_type() -> None:
    assert _icmp_response_label({"type": 99, "code": 0}) == RESP_NO_RESPONSE


def test_icmp_response_label_dest_unreach_wrong_code() -> None:
    assert (
        _icmp_response_label({"type": ICMP_DEST_UNREACH, "code": 0})
        == RESP_NO_RESPONSE
    )


# ---------------------------------------------------------------------------
# _resolve_host
# ---------------------------------------------------------------------------


def test_resolve_host_localhost() -> None:
    result = _resolve_host("127.0.0.1")
    assert result == "127.0.0.1"


def test_resolve_host_invalid() -> None:
    result = _resolve_host("nonexistent.invalid.domain.tld")
    assert result is None


# ---------------------------------------------------------------------------
# _no_response_result
# ---------------------------------------------------------------------------


def test_no_response_result() -> None:
    result = _no_response_result(5, 123.45)
    assert result["hop"] == 5
    assert result["ttl"] == 5
    assert result["ip"] is None
    assert result["host"] == "*"
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["rtt_ms"] == 123.45
    assert result["reached_destination"] is False
    assert result["error_code"] is None


# ---------------------------------------------------------------------------
# _try_create_raw_socket
# ---------------------------------------------------------------------------


def test_try_create_raw_socket() -> None:
    result = _try_create_raw_socket()
    # In CI / sandbox, raw sockets usually unavailable without root
    if result is not None:
        result.close()


# ---------------------------------------------------------------------------
# probe_ttl – fallback mode (no raw socket)
# ---------------------------------------------------------------------------


def test_probe_ttl_offline_no_raw_socket() -> None:
    """Fallback mode against an unroutable address should time out."""
    result = probe_ttl(
        "192.0.2.1",
        DEFAULT_PORT,
        ttl=1,
        timeout=1.0,
        raw_socket=None,
        resolved_ip="192.0.2.1",
    )
    assert result["hop"] == 1
    assert result["ttl"] == 1
    assert result["reached_destination"] is False
    assert result["response_type"] in (RESP_NO_RESPONSE, RESP_TIMEOUT)


def test_probe_ttl_loopback_open_no_raw_socket() -> None:
    """Fallback mode: connect to an open local port should report connected."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]

    def _serve() -> None:
        try:
            conn, _ = sock.accept()
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    try:
        result = probe_ttl(
            "127.0.0.1",
            port,
            ttl=1,
            timeout=2.0,
            raw_socket=None,
            resolved_ip="127.0.0.1",
        )
        assert result["connected"] if "connected" in result else True
        assert result["response_type"] == RESP_CONNECTED
        assert result["reached_destination"] is True
        assert result["ip"] == "127.0.0.1"
    finally:
        sock.close()


def test_probe_ttl_loopback_closed_no_raw_socket() -> None:
    """Fallback mode: connect to a closed port should report RST."""
    # Bind then immediately release to get a known-closed port
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_sock.bind(("127.0.0.1", 0))
    port = test_sock.getsockname()[1]
    test_sock.close()

    result = probe_ttl(
        "127.0.0.1",
        port,
        ttl=1,
        timeout=2.0,
        raw_socket=None,
        resolved_ip="127.0.0.1",
    )
    assert result["response_type"] == RESP_RST
    assert result["reached_destination"] is True


# ---------------------------------------------------------------------------
# probe_ttl – raw socket mode (with mocked raw socket)
# ---------------------------------------------------------------------------


class _FakeRawSocket:
    """Minimal fake raw socket that returns pre-set data from recvfrom."""

    def __init__(self, data: bytes = b"", recv_error: Exception = None) -> None:
        self._data = data
        self._recv_error = recv_error
        self.timeout = None
        self.closed = False

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def recvfrom(self, bufsize: int):
        if self._recv_error is not None:
            raise self._recv_error
        if not self._data:
            raise socket.timeout()
        data = self._data
        self._data = b""  # single-shot
        return data, ("0.0.0.0", 0)

    def close(self) -> None:
        self.closed = True


def test_probe_ttl_raw_socket_time_exceeded() -> None:
    icmp_packet = build_icmp_packet(
        ICMP_TIME_EXCEEDED, 0, "192.168.1.1", "10.0.0.1"
    )
    fake_raw = _FakeRawSocket(data=icmp_packet)
    result = probe_ttl(
        "10.0.0.1",
        DEFAULT_PORT,
        ttl=3,
        timeout=1.0,
        raw_socket=fake_raw,
    )
    assert result["hop"] == 3
    assert result["ttl"] == 3
    assert result["ip"] == "192.168.1.1"
    assert result["response_type"] == RESP_TIME_EXCEEDED
    assert result["reached_destination"] is False
    assert result["error_code"] is None
    assert result["rtt_ms"] >= 0


def test_probe_ttl_raw_socket_port_unreachable() -> None:
    icmp_packet = build_icmp_packet(
        ICMP_DEST_UNREACH,
        PORT_UNREACHABLE_CODE,
        "203.0.113.5",
        "10.0.0.1",
    )
    fake_raw = _FakeRawSocket(data=icmp_packet)
    result = probe_ttl(
        "10.0.0.1",
        443,
        ttl=5,
        timeout=1.0,
        raw_socket=fake_raw,
    )
    assert result["ip"] == "203.0.113.5"
    assert result["response_type"] == RESP_PORT_UNREACHABLE
    assert result["reached_destination"] is True


def test_probe_ttl_raw_socket_timeout() -> None:
    fake_raw = _FakeRawSocket(data=b"")  # empty data -> recvfrom raises timeout
    result = probe_ttl(
        "10.0.0.1",
        DEFAULT_PORT,
        ttl=2,
        timeout=1.0,
        raw_socket=fake_raw,
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["reached_destination"] is False
    assert result["ip"] is None


def test_probe_ttl_raw_socket_oserror() -> None:
    fake_raw = _FakeRawSocket(recv_error=OSError("socket closed"))
    result = probe_ttl(
        "10.0.0.1",
        DEFAULT_PORT,
        ttl=2,
        timeout=1.0,
        raw_socket=fake_raw,
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["reached_destination"] is False


# ---------------------------------------------------------------------------
# run_trace
# ---------------------------------------------------------------------------


def test_run_trace_offline_target(monkeypatch) -> None:
    """run_trace with monkeypatched probe_ttl returns structured results."""

    def mock_probe_ttl(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        return {
            "hop": ttl,
            "ttl": ttl,
            "ip": None,
            "host": "*",
            "response_type": RESP_NO_RESPONSE,
            "rtt_ms": 1.5,
            "reached_destination": False,
            "error_code": None,
        }

    monkeypatch.setattr("ethscan.trace._try_create_raw_socket", lambda: None)
    monkeypatch.setattr("ethscan.trace.probe_ttl", mock_probe_ttl)
    monkeypatch.setattr("ethscan.trace._resolve_host", lambda host: "10.0.0.1")

    result = run_trace("example.com", max_hops=3, timeout=1.0, probes_per_hop=1)
    assert result["target"] == "example.com"
    assert result["host"] == "example.com"
    assert result["ip"] == "10.0.0.1"
    assert result["port"] == DEFAULT_PORT
    assert result["max_hops"] == 3
    assert result["hop_count"] == 3
    assert len(result["hops"]) == 3
    assert result["destination_reached"] is False
    assert result["raw_socket_available"] is False
    assert isinstance(result["notes"], list)


def test_run_trace_default_port() -> None:
    import ethscan.trace as trace_mod

    called_port = []

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        called_port.append(port)
        return _no_response_result(ttl, 1.0)

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    try:
        result = run_trace("example.com", max_hops=1, probes_per_hop=1)
        assert called_port[0] == DEFAULT_PORT
        assert result["port"] == DEFAULT_PORT
        assert result["max_hops"] == 1
        assert result["probes_per_hop"] == 1
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw


def test_run_trace_max_hops_capped() -> None:
    import ethscan.trace as trace_mod

    call_count = [0]

    def mock_probe(*args, **kwargs):
        call_count[0] += 1
        return _no_response_result(kwargs.get("ttl", 1), 1.0)

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    try:
        result = run_trace("example.com", max_hops=200, probes_per_hop=1)
        assert result["max_hops"] == 128
        assert result["hop_count"] == 128
        assert call_count[0] == 128
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw


def test_run_trace_destination_reached_stops_early() -> None:
    import ethscan.trace as trace_mod

    call_count = [0]

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        call_count[0] += 1
        reached = ttl >= 3
        return {
            "hop": ttl,
            "ttl": ttl,
            "ip": "10.0.0.1" if reached else None,
            "host": "10.0.0.1" if reached else "*",
            "response_type": RESP_PORT_UNREACHABLE if reached else RESP_NO_RESPONSE,
            "rtt_ms": 1.0,
            "reached_destination": reached,
            "error_code": None,
        }

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    try:
        result = run_trace("example.com", max_hops=10, probes_per_hop=1, timeout=1.0)
        assert result["destination_reached"] is True
        assert result["hop_count"] == 3
        assert call_count[0] == 3
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw


def test_run_trace_probes_per_hop() -> None:
    import ethscan.trace as trace_mod

    call_count = [0]

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        call_count[0] += 1
        return _no_response_result(ttl, 1.0)

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    try:
        result = run_trace("example.com", max_hops=2, probes_per_hop=3, timeout=1.0)
        assert result["probes_per_hop"] == 3
        assert call_count[0] == 6  # 2 hops * 3 probes
        # Verify RTT averaging exists in hop entries
        for hop in result["hops"]:
            assert "rtt_avg_ms" in hop
            assert "probes" in hop
            assert len(hop["probes"]) == 3
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw


def test_run_trace_url_target() -> None:
    import ethscan.trace as trace_mod

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        return _no_response_result(ttl, 1.0)

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    try:
        result = run_trace("https://example.com", max_hops=1, probes_per_hop=1)
        assert result["host"] == "example.com"
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw


def test_run_trace_unresolvable_host() -> None:
    import ethscan.trace as trace_mod

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        return _no_response_result(ttl, 1.0)

    orig_probe = trace_mod.probe_ttl
    orig_raw = trace_mod._try_create_raw_socket
    orig_resolve = trace_mod._resolve_host
    trace_mod.probe_ttl = mock_probe
    trace_mod._try_create_raw_socket = lambda: None
    trace_mod._resolve_host = lambda h: None
    try:
        result = run_trace("nonexistent.invalid.domain.tld", max_hops=1, probes_per_hop=1)
        assert result["ip"] is None
        assert any("Could not resolve" in note for note in result["notes"])
    finally:
        trace_mod.probe_ttl = orig_probe
        trace_mod._try_create_raw_socket = orig_raw
        trace_mod._resolve_host = orig_resolve


def test_run_trace_raw_socket_available(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.trace._resolve_host", lambda h: "10.0.0.1")

    class _TrueRawSocket:
        closed = False

        def settimeout(self, t):
            pass

        def recvfrom(self, n):
            raise socket.timeout()

        def close(self):
            self.closed = True

    fake_raw = _TrueRawSocket()

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        return {
            "hop": ttl,
            "ttl": ttl,
            "ip": "10.0.0.2" if ttl >= 3 else None,
            "host": "10.0.0.2" if ttl >= 3 else "*",
            "response_type": RESP_PORT_UNREACHABLE if ttl >= 3 else RESP_TIME_EXCEEDED,
            "rtt_ms": 1.0,
            "reached_destination": ttl >= 3,
            "error_code": None,
        }

    monkeypatch.setattr("ethscan.trace.probe_ttl", mock_probe)
    monkeypatch.setattr("ethscan.trace._try_create_raw_socket", lambda: fake_raw)

    result = run_trace("example.com", port=443, max_hops=5, probes_per_hop=1)
    assert result["raw_socket_available"] is True
    assert fake_raw.closed is True
    assert result["destination_reached"] is True
    assert result["hop_count"] == 3


def test_run_trace_custom_port_passed(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.trace._resolve_host", lambda h: "10.0.0.1")

    called_port = []

    def mock_probe(host, port, ttl, timeout=3.0, raw_socket=None, resolved_ip=None):
        called_port.append(port)
        return _no_response_result(ttl, 1.0)

    monkeypatch.setattr("ethscan.trace.probe_ttl", mock_probe)
    monkeypatch.setattr("ethscan.trace._try_create_raw_socket", lambda: None)

    run_trace("example.com", port=8080, max_hops=1, probes_per_hop=1)
    assert called_port[0] == 8080


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


_SAMPLE_DATA = {
    "target": "example.com",
    "host": "example.com",
    "ip": "93.184.216.34",
    "port": 80,
    "max_hops": 30,
    "timeout": 3.0,
    "probes_per_hop": 3,
    "raw_socket_available": False,
    "hops": [
        {
            "hop": 1,
            "ttl": 1,
            "ip": "192.168.1.1",
            "host": "192.168.1.1",
            "response_type": RESP_TIME_EXCEEDED,
            "rtt_ms": 1.23,
            "rtt_avg_ms": 1.45,
            "probes": [
                {
                    "hop": 1, "ttl": 1, "ip": "192.168.1.1",
                    "host": "192.168.1.1", "response_type": RESP_TIME_EXCEEDED,
                    "rtt_ms": 1.23, "reached_destination": False, "error_code": None,
                },
                {
                    "hop": 1, "ttl": 1, "ip": "192.168.1.1",
                    "host": "192.168.1.1", "response_type": RESP_TIME_EXCEEDED,
                    "rtt_ms": 1.45, "reached_destination": False, "error_code": None,
                },
                {
                    "hop": 1, "ttl": 1, "ip": "192.168.1.1",
                    "host": "192.168.1.1", "response_type": RESP_TIME_EXCEEDED,
                    "rtt_ms": 1.67, "reached_destination": False, "error_code": None,
                },
            ],
            "reached_destination": False,
            "error_code": None,
        },
        {
            "hop": 2,
            "ttl": 2,
            "ip": "10.0.0.1",
            "host": "10.0.0.1",
            "response_type": RESP_PORT_UNREACHABLE,
            "rtt_ms": 5.0,
            "rtt_avg_ms": 5.0,
            "probes": [
                {
                    "hop": 2, "ttl": 2, "ip": "10.0.0.1",
                    "host": "10.0.0.1", "response_type": RESP_PORT_UNREACHABLE,
                    "rtt_ms": 5.0, "reached_destination": True, "error_code": None,
                },
            ],
            "reached_destination": True,
            "error_code": None,
        },
    ],
    "hop_count": 2,
    "destination_reached": True,
    "notes": ["Destination reached at hop 2"],
}


def test_format_trace_report_json() -> None:
    output = format_trace_report_json(_SAMPLE_DATA)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["destination_reached"] is True
    assert len(parsed["hops"]) == 2
    assert parsed["hops"][0]["ip"] == "192.168.1.1"


def test_format_trace_report_markdown() -> None:
    output = format_trace_report_markdown(_SAMPLE_DATA)
    assert "TCP Traceroute Report" in output
    assert "example.com" in output
    assert "93.184.216.34" in output
    assert "Hop Table" in output
    assert "192.168.1.1" in output
    assert "TIME_EXCEEDED" in output
    assert "PORT_UNREACHABLE" in output
    assert "Hop Details" in output
    assert "Notes" in output
    assert "Destination reached at hop 2" in output


def test_format_trace_report_markdown_no_hops() -> None:
    data = dict(_SAMPLE_DATA)
    data["hops"] = []
    data["hop_count"] = 0
    data["destination_reached"] = False
    data["notes"] = ["No response received"]
    output = format_trace_report_markdown(data)
    assert "No hops recorded" in output
    assert "No response received" in output


def test_format_trace_report_markdown_pipe_escape() -> None:
    data = dict(_SAMPLE_DATA)
    data["hops"] = [
        {
            "hop": 1,
            "ttl": 1,
            "ip": "192.168.1|1",
            "host": "192.168.1|1",
            "response_type": "NO-RESPONSE",
            "rtt_ms": 1.0,
            "rtt_avg_ms": 1.0,
            "probes": [
                {
                    "hop": 1, "ttl": 1, "ip": "192.168.1|1",
                    "host": "192.168.1|1", "response_type": "NO-RESPONSE",
                    "rtt_ms": 1.0, "reached_destination": False, "error_code": None,
                }
            ],
            "reached_destination": False,
            "error_code": None,
        }
    ]
    data["destination_reached"] = False
    data["hop_count"] = 1
    data["notes"] = []
    output = format_trace_report_markdown(data)
    assert "\\|" in output


def test_format_trace_report_markdown_no_resolved_ip() -> None:
    data = dict(_SAMPLE_DATA)
    data["ip"] = None
    data["hops"] = []
    data["hop_count"] = 0
    data["destination_reached"] = False
    data["notes"] = ["Could not resolve host"]
    output = format_trace_report_markdown(data)
    assert "Resolved IP" not in output
    assert "Could not resolve host" in output


def test_format_trace_report_json_no_resolved_ip() -> None:
    data = dict(_SAMPLE_DATA)
    data["ip"] = None
    output = format_trace_report_json(data)
    parsed = json.loads(output)
    assert parsed["ip"] is None


def test_format_trace_report_markdown_rtt_avg() -> None:
    output = format_trace_report_markdown(_SAMPLE_DATA)
    # Hop 1 has rtt_avg_ms=1.45, hop 2 has rtt_avg_ms=5.0
    assert "1.45" in output
    assert "5.0" in output


def test_format_trace_report_markdown_no_probes_per_hop() -> None:
    """Test markdown formatter when a hop has no probe details."""
    data = dict(_SAMPLE_DATA)
    data["hops"] = [
        {
            "hop": 1,
            "ttl": 1,
            "ip": None,
            "host": "*",
            "response_type": RESP_NO_RESPONSE,
            "rtt_ms": None,
            "rtt_avg_ms": None,
            "probes": [],
            "reached_destination": False,
            "error_code": None,
        }
    ]
    data["destination_reached"] = False
    data["hop_count"] = 1
    data["notes"] = []
    output = format_trace_report_markdown(data)
    assert "N/A" in output or "No probes" in output
