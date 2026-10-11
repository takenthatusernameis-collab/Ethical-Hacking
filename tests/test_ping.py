"""Tests for the ethscan ping module."""

import json
import socket
import struct
import threading
import time

from ethscan.ping import (
    DEFAULT_COUNT,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_TTL,
    ICMP_ECHO_REPLY,
    ICMP_ECHO_REQUEST,
    RESP_CONNECTED,
    RESP_ECHO_REPLY,
    RESP_NO_RESPONSE,
    RESP_RST,
    RESP_TIMEOUT,
    _build_icmp_echo_request,
    _checksum,
    _normalize_host,
    _parse_icmp_reply,
    _resolve_host,
    _try_create_raw_socket,
    format_ping_report_json,
    format_ping_report_markdown,
    probe_icmp,
    run_ping,
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
# ICMP Echo Request building
# ---------------------------------------------------------------------------


def test_build_icmp_echo_request_structure() -> None:
    req = _build_icmp_echo_request(12345, 1, b"test")
    assert len(req) >= 8
    # Parse back
    icmp_type, code, checksum, ident, seq = struct.unpack("!BBHHH", req[:8])
    assert icmp_type == ICMP_ECHO_REQUEST
    assert code == 0
    assert ident == 12345
    assert seq == 1
    assert req[8:] == b"test"


def test_build_icmp_echo_request_empty_payload() -> None:
    req = _build_icmp_echo_request(12345, 1)
    icmp_type, code, checksum, ident, seq = struct.unpack("!BBHHH", req[:8])
    assert icmp_type == ICMP_ECHO_REQUEST
    assert ident == 12345
    assert seq == 1
    assert len(req) == 8


# ---------------------------------------------------------------------------
# ICMP Reply parsing
# ---------------------------------------------------------------------------


def _make_icmp_reply_packet(identifier: int, sequence: int, src_ip: str = "10.0.0.1", payload: bytes = b"") -> bytes:
    """Build a synthetic ICMP Echo Reply packet for testing."""
    # IP header (minimal)
    version_ihl = (4 << 4) | 5
    total_length = 20 + 8 + len(payload)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        socket.IPPROTO_ICMP,
        0,
        socket.inet_aton(src_ip),
        socket.inet_aton("10.0.0.2"),
    )
    ip_checksum = _checksum(ip_header)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        socket.IPPROTO_ICMP,
        ip_checksum,
        socket.inet_aton(src_ip),
        socket.inet_aton("10.0.0.2"),
    )

    # ICMP header
    icmp_header = struct.pack("!BBHHH", ICMP_ECHO_REPLY, 0, 0, identifier, sequence)
    icmp_checksum = _checksum(icmp_header + payload)
    icmp_header = struct.pack("!BBHHH", ICMP_ECHO_REPLY, 0, icmp_checksum, identifier, sequence)

    return ip_header + icmp_header + payload


def test_parse_icmp_reply_valid() -> None:
    packet = _make_icmp_reply_packet(12345, 1, "192.168.1.1", b"test")
    result = _parse_icmp_reply(packet, 12345)
    assert result["type"] == ICMP_ECHO_REPLY
    assert result["code"] == 0
    assert result["identifier"] == 12345
    assert result["sequence"] == 1
    assert result["src_ip"] == "192.168.1.1"
    assert result["payload"] == b"test"
    assert result["error"] is None


def test_parse_icmp_reply_wrong_identifier() -> None:
    packet = _make_icmp_reply_packet(12345, 1, "192.168.1.1")
    result = _parse_icmp_reply(packet, 54321)
    assert result["error"] == "identifier mismatch: expected 54321, got 12345"


def test_parse_icmp_reply_wrong_type() -> None:
    # Build a Time Exceeded packet instead
    version_ihl = (4 << 4) | 5
    total_length = 20 + 8
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        socket.IPPROTO_ICMP,
        0,
        socket.inet_aton("192.168.1.1"),
        socket.inet_aton("10.0.0.2"),
    )
    ip_checksum = _checksum(ip_header)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        0,
        0,
        64,
        socket.IPPROTO_ICMP,
        ip_checksum,
        socket.inet_aton("192.168.1.1"),
        socket.inet_aton("10.0.0.2"),
    )

    icmp_header = struct.pack("!BBHHH", 11, 0, 0, 0, 0)  # Type 11 = Time Exceeded
    icmp_checksum = _checksum(icmp_header)
    icmp_header = struct.pack("!BBHHH", 11, 0, icmp_checksum, 0, 0)

    packet = ip_header + icmp_header
    result = _parse_icmp_reply(packet, 12345)
    assert "not echo reply" in result["error"]


def test_parse_icmp_reply_too_short() -> None:
    result = _parse_icmp_reply(b"\x00" * 10, 12345)
    assert result["error"] == "packet too short for IP header"


def test_parse_icmp_reply_not_ipv4() -> None:
    result = _parse_icmp_reply(b"\x00" * 20, 12345)
    assert result["error"] == "not IPv4"


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
# _try_create_raw_socket
# ---------------------------------------------------------------------------


def test_try_create_raw_socket() -> None:
    result = _try_create_raw_socket()
    if result is not None:
        result.close()


# ---------------------------------------------------------------------------
# probe_icmp – fallback mode (no raw socket)
# ---------------------------------------------------------------------------


def test_probe_icmp_offline_no_raw_socket() -> None:
    """Fallback mode against an unroutable address should time out."""
    result = probe_icmp(
        "192.0.2.1",
        timeout=1.0,
        ttl=64,
        raw_socket=None,
        identifier=12345,
        sequence=1,
        resolved_ip="192.0.2.1",
    )
    assert result["sequence"] == 1
    assert result["ttl"] == 64
    assert result["reached_destination"] is False if "reached_destination" in result else True
    assert result["response_type"] in (RESP_NO_RESPONSE, RESP_TIMEOUT)


def test_probe_icmp_loopback_open_no_raw_socket() -> None:
    """Fallback mode: connect to an open local port should report connected."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]

    ready = threading.Event()

    def _serve() -> None:
        ready.set()
        try:
            conn, _ = sock.accept()
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    ready.wait(timeout=2.0)
    time.sleep(0.1)  # Small delay to ensure server is ready
    try:
        result = probe_icmp(
            "127.0.0.1",
            timeout=2.0,
            ttl=64,
            raw_socket=None,
            identifier=12345,
            sequence=1,
            resolved_ip="127.0.0.1",
            port=port,
        )
        assert result["response_type"] == RESP_CONNECTED
        assert result["ip"] == "127.0.0.1"
    finally:
        sock.close()


def test_probe_icmp_loopback_closed_no_raw_socket() -> None:
    """Fallback mode: connect to a closed port should report RST."""
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_sock.bind(("127.0.0.1", 0))
    port = test_sock.getsockname()[1]
    test_sock.close()

    result = probe_icmp(
        "127.0.0.1",
        timeout=2.0,
        ttl=64,
        raw_socket=None,
        identifier=12345,
        sequence=1,
        resolved_ip="127.0.0.1",
    )
    assert result["response_type"] == RESP_RST
    assert result["ip"] == "127.0.0.1"


# ---------------------------------------------------------------------------
# probe_icmp – raw socket mode (with mocked raw socket)
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
        self._data = b""
        return data, ("0.0.0.0", 0)

    def close(self) -> None:
        self.closed = True


def test_probe_icmp_raw_socket_echo_reply(monkeypatch) -> None:
    reply_packet = _make_icmp_reply_packet(12345, 1, "192.168.1.1", b"test")
    fake_raw = _FakeRawSocket(data=reply_packet)

    class _FakeSendSocket:
        def __init__(self):
            self.sent = False
            self.closed = False
        def setsockopt(self, *args, **kwargs):
            pass
        def settimeout(self, t):
            pass
        def sendto(self, data, addr):
            self.sent = True
        def close(self):
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMP:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "10.0.0.1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="10.0.0.1",
    )
    assert result["sequence"] == 1
    assert result["ttl"] == 64
    assert result["ip"] == "192.168.1.1"
    assert result["response_type"] == RESP_ECHO_REPLY
    assert result["error"] is None
    assert result["rtt_ms"] >= 0
    assert fake_send.sent is True
    assert fake_send.closed is True


def test_probe_icmp_raw_socket_timeout(monkeypatch) -> None:
    fake_raw = _FakeRawSocket(data=b"")

    class _FakeSendSocket:
        def __init__(self):
            self.closed = False
        def setsockopt(self, *args, **kwargs):
            pass
        def settimeout(self, t):
            pass
        def sendto(self, data, addr):
            pass
        def close(self):
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMP:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "10.0.0.1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="10.0.0.1",
    )
    assert result["response_type"] == RESP_TIMEOUT
    assert result["ip"] is None
    assert fake_send.closed is True


def test_probe_icmp_raw_socket_oserror(monkeypatch) -> None:
    fake_raw = _FakeRawSocket(recv_error=OSError("socket closed"))

    class _FakeSendSocket:
        def __init__(self):
            self.closed = False
        def setsockopt(self, *args, **kwargs):
            pass
        def settimeout(self, t):
            pass
        def sendto(self, data, addr):
            pass
        def close(self):
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMP:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "10.0.0.1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="10.0.0.1",
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert "socket closed" in result["error"]
    assert fake_send.closed is True


def test_probe_icmp_raw_socket_wrong_id(monkeypatch) -> None:
    reply_packet = _make_icmp_reply_packet(54321, 1, "192.168.1.1")
    fake_raw = _FakeRawSocket(data=reply_packet)

    class _FakeSendSocket:
        def __init__(self):
            self.closed = False
        def setsockopt(self, *args, **kwargs):
            pass
        def settimeout(self, t):
            pass
        def sendto(self, data, addr):
            pass
        def close(self):
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMP:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "10.0.0.1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="10.0.0.1",
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert "identifier mismatch" in result["error"]
    assert fake_send.closed is True


# ---------------------------------------------------------------------------
# run_ping
# ---------------------------------------------------------------------------


def test_run_ping_offline_target(monkeypatch) -> None:
    """run_ping with monkeypatched probe_icmp returns structured results."""

    def mock_probe_icmp(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        return {
            "ip": None,
            "rtt_ms": 1.5,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_NO_RESPONSE,
            "error": "timeout",
        }

    monkeypatch.setattr("ethscan.ping._try_create_raw_socket", lambda: None)
    monkeypatch.setattr("ethscan.ping.probe_icmp", mock_probe_icmp)
    monkeypatch.setattr("ethscan.ping._resolve_host", lambda host: "10.0.0.1")

    result = run_ping("example.com", count=3, timeout=1.0, ttl=64)
    assert result["target"] == "example.com"
    assert result["host"] == "example.com"
    assert result["ip"] == "10.0.0.1"
    assert result["count"] == 3
    assert result["timeout"] == 1.0
    assert result["ttl"] == 64
    assert result["port"] == DEFAULT_PORT
    assert len(result["probes"]) == 3
    assert result["successful"] == 0
    assert result["failed"] == 3
    assert result["raw_socket_available"] is False
    assert isinstance(result["notes"], list)


def test_run_ping_defaults() -> None:
    import ethscan.ping as ping_mod

    called = []

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        called.append((host, timeout, ttl, identifier, sequence))
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    try:
        result = run_ping("example.com")
        assert result["count"] == DEFAULT_COUNT
        assert result["timeout"] == DEFAULT_TIMEOUT
        assert result["ttl"] == DEFAULT_TTL
        assert result["port"] == DEFAULT_PORT
        assert len(called) == DEFAULT_COUNT
        assert called[0][1] == DEFAULT_TIMEOUT
        assert called[0][2] == DEFAULT_TTL
        assert called[0][3] != 0  # identifier set
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_run_ping_custom_params_passed() -> None:
    import ethscan.ping as ping_mod

    called = []

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        called.append((timeout, ttl, sequence))
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    try:
        run_ping("example.com", count=2, timeout=5.0, ttl=128, port=443)
        assert called[0][0] == 5.0
        assert called[0][1] == 128
        assert len(called) == 2
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_run_ping_successful_probes_rtt_stats() -> None:
    import ethscan.ping as ping_mod

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        return {
            "ip": "10.0.0.1",
            "rtt_ms": float(sequence * 10),  # 10, 20, 30
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    try:
        result = run_ping("example.com", count=3, timeout=1.0)
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["rtt_min_ms"] == 10.0
        assert result["rtt_max_ms"] == 30.0
        assert result["rtt_avg_ms"] == 20.0
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_run_ping_mixed_results() -> None:
    import ethscan.ping as ping_mod

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        if sequence % 2 == 1:
            return {
                "ip": "10.0.0.1",
                "rtt_ms": 10.0,
                "ttl": ttl,
                "sequence": sequence,
                "response_type": RESP_ECHO_REPLY,
                "error": None,
            }
        return {
            "ip": None,
            "rtt_ms": 100.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_TIMEOUT,
            "error": "timeout",
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    try:
        result = run_ping("example.com", count=4, timeout=1.0)
        assert result["successful"] == 2
        assert result["failed"] == 2
        assert result["rtt_min_ms"] == 10.0
        assert result["rtt_max_ms"] == 10.0
        assert result["rtt_avg_ms"] == 10.0
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_run_ping_unresolvable_host() -> None:
    import ethscan.ping as ping_mod

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        return {
            "ip": None,
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_NO_RESPONSE,
            "error": "failed",
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    orig_resolve = ping_mod._resolve_host
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    ping_mod._resolve_host = lambda h: None
    try:
        result = run_ping("nonexistent.invalid.domain.tld", count=1, timeout=1.0)
        assert result["ip"] is None
        assert any("Could not resolve" in note for note in result["notes"])
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw
        ping_mod._resolve_host = orig_resolve


def test_run_ping_raw_socket_available(monkeypatch) -> None:
    class _TrueRawSocket:
        closed = False

        def settimeout(self, t):
            pass

        def recvfrom(self, n):
            raise socket.timeout()

        def close(self):
            self.closed = True

    fake_raw = _TrueRawSocket()

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    monkeypatch.setattr("ethscan.ping._resolve_host", lambda h: "10.0.0.1")
    monkeypatch.setattr("ethscan.ping.probe_icmp", mock_probe)
    monkeypatch.setattr("ethscan.ping._try_create_raw_socket", lambda: fake_raw)

    result = run_ping("example.com", count=2, timeout=1.0)
    assert result["raw_socket_available"] is True
    assert fake_raw.closed is True
    assert result["successful"] == 2


def test_run_ping_url_target() -> None:
    import ethscan.ping as ping_mod

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, port=80):
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda: None
    try:
        result = run_ping("https://example.com", count=1)
        assert result["host"] == "example.com"
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


_SAMPLE_DATA = {
    "target": "example.com",
    "host": "example.com",
    "ip": "93.184.216.34",
    "count": 4,
    "timeout": 2.0,
    "ttl": 64,
    "port": 80,
    "raw_socket_available": False,
    "probes": [
        {
            "ip": "93.184.216.34",
            "rtt_ms": 12.34,
            "ttl": 64,
            "sequence": 1,
            "response_type": RESP_CONNECTED,
            "error": None,
        },
        {
            "ip": "93.184.216.34",
            "rtt_ms": 15.67,
            "ttl": 64,
            "sequence": 2,
            "response_type": RESP_CONNECTED,
            "error": None,
        },
        {
            "ip": "93.184.216.34",
            "rtt_ms": 10.11,
            "ttl": 64,
            "sequence": 3,
            "response_type": RESP_CONNECTED,
            "error": None,
        },
        {
            "ip": None,
            "rtt_ms": 2000.0,
            "ttl": 64,
            "sequence": 4,
            "response_type": RESP_TIMEOUT,
            "error": "timeout",
        },
    ],
    "successful": 3,
    "failed": 1,
    "rtt_min_ms": 10.11,
    "rtt_max_ms": 15.67,
    "rtt_avg_ms": 12.71,
    "notes": ["Raw ICMP socket unavailable; running in TCP connect fallback mode on port 80", "3/4 probes successful"],
}


def test_format_ping_report_json() -> None:
    output = format_ping_report_json(_SAMPLE_DATA)
    parsed = json.loads(output)
    assert parsed["target"] == "example.com"
    assert parsed["successful"] == 3
    assert parsed["failed"] == 1
    assert len(parsed["probes"]) == 4
    assert parsed["probes"][0]["response_type"] == RESP_CONNECTED


def test_format_ping_report_markdown() -> None:
    output = format_ping_report_markdown(_SAMPLE_DATA)
    assert "Ping Report" in output
    assert "example.com" in output
    assert "93.184.216.34" in output
    assert "Probe Results" in output
    assert "CONNECTED" in output
    assert "TIMEOUT" in output
    assert "Notes" in output
    assert "TCP connect fallback mode" in output


def test_format_ping_report_markdown_no_ip() -> None:
    data = dict(_SAMPLE_DATA)
    data["ip"] = None
    data["probes"] = []
    data["successful"] = 0
    data["failed"] = 4
    data["rtt_min_ms"] = None
    data["rtt_max_ms"] = None
    data["rtt_avg_ms"] = None
    data["notes"] = ["Could not resolve host"]
    output = format_ping_report_markdown(data)
    assert "Resolved IP" not in output
    assert "Could not resolve host" in output


def test_format_ping_report_markdown_pipe_escape() -> None:
    data = dict(_SAMPLE_DATA)
    data["probes"] = [
        {
            "ip": "192.168.1|1",
            "rtt_ms": 1.0,
            "ttl": 64,
            "sequence": 1,
            "response_type": "NO-RESPONSE",
            "error": None,
        }
    ]
    data["successful"] = 0
    data["failed"] = 1
    data["rtt_min_ms"] = None
    data["rtt_max_ms"] = None
    data["rtt_avg_ms"] = None
    data["notes"] = []
    output = format_ping_report_markdown(data)
    assert "\\|" in output


def test_format_ping_report_markdown_raw_socket_available() -> None:
    data = dict(_SAMPLE_DATA)
    data["raw_socket_available"] = True
    data["notes"] = ["2/2 probes successful"]
    output = format_ping_report_markdown(data)
    assert "available" in output
    assert "fallback" not in output.lower() or "TCP connect fallback" not in output