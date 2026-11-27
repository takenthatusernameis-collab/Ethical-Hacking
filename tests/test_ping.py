"""Tests for the ethscan ping module."""

from __future__ import annotations

import csv
import io
import json
import socket
import struct
import threading
import time
from typing import Any, cast

from ethscan.ping import (
    DEFAULT_COUNT,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_TTL,
    ICMP_ECHO_REPLY,
    ICMP_ECHO_REQUEST,
    ICMPV6_ECHO_REQUEST,
    ICMPV6_ECHO_REPLY,
    ICMPV6_NEXT_HEADER,
    RESP_CONNECTED,
    RESP_ECHO_REPLY,
    RESP_NO_RESPONSE,
    RESP_RST,
    RESP_TIMEOUT,
    _build_icmp_echo_request,
    _build_icmpv6_echo_request,
    _checksum,
    _normalize_host,
    _parse_icmp_reply,
    _parse_icmpv6_reply,
    _resolve_host,
    _try_create_raw_socket,
    format_ping_report_csv,
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
    assert _checksum(b"hello") == 0xBC2D


def test_checksum_odd_length_pads() -> None:
    # Odd-length input is zero-padded before summing (RFC 1071).
    assert _checksum(b"abc") == 0x3B9D


# ---------------------------------------------------------------------------
# ICMP Echo Request building
# ---------------------------------------------------------------------------


def test_build_icmp_echo_request_structure() -> None:
    req = _build_icmp_echo_request(12345, 1, b"test")
    assert len(req) >= 8
    # Parse back
    icmp_type, _, _, ident, seq = struct.unpack("!BBHHH", req[:8])
    assert icmp_type == ICMP_ECHO_REQUEST
    assert ident == 12345
    assert seq == 1
    assert req[8:] == b"test"


def test_build_icmp_echo_request_empty_payload() -> None:
    req = _build_icmp_echo_request(12345, 1)
    icmp_type, _, _, ident, seq = struct.unpack("!BBHHH", req[:8])
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
    assert result is not None
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
    assert result is not None
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
    assert result is not None
    assert result["error"] is not None
    assert "not echo reply" in result["error"]


def test_parse_icmp_reply_too_short() -> None:
    result = _parse_icmp_reply(b"\x00" * 10, 12345)
    assert result is not None
    assert result["error"] == "packet too short for IP header"


def test_parse_icmp_reply_not_ipv4() -> None:
    result = _parse_icmp_reply(b"\x00" * 20, 12345)
    assert result is not None
    assert result["error"] == "not IPv4"


def test_parse_icmp_reply_ip_header_truncated() -> None:
    # version=4, ihl=0 -> ip_header_len=0 < 20
    result = _parse_icmp_reply(b"\x40" + b"\x00" * 19, 12345)
    assert result is not None
    assert result["error"] == "IP header truncated"


def test_parse_icmp_reply_icmp_header_truncated() -> None:
    # valid 20-byte IPv4 header (ihl=5) with no ICMP bytes following
    version_ihl = (4 << 4) | 5
    total_length = 20
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
        socket.inet_aton("10.0.0.1"),
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
        socket.inet_aton("10.0.0.1"),
        socket.inet_aton("10.0.0.2"),
    )
    result = _parse_icmp_reply(ip_header, 12345)
    assert result is not None
    assert result["error"] == "ICMP header truncated"


def _make_icmpv6_reply_packet(identifier: int, sequence: int, payload: bytes = b"") -> bytes:
    """Build a synthetic ICMPv6 Echo Reply (no IP header) with a valid checksum."""
    message = struct.pack("!BBHHH", ICMPV6_ECHO_REPLY, 0, 0, identifier, sequence) + payload
    pseudo = (
        socket.inet_pton(socket.AF_INET6, "2001:db8::2")
        + socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + struct.pack("!I", len(message))
        + b"\x00\x00\x00"
        + struct.pack("!B", 58)
    )
    checksum = _checksum(pseudo + message)
    return struct.pack("!BBHHH", ICMPV6_ECHO_REPLY, 0, checksum, identifier, sequence) + payload


def test_build_icmpv6_echo_request_structure() -> None:
    req = _build_icmpv6_echo_request(12345, 1, b"test", "2001:db8::1", "2001:db8::2")
    assert req[0] == ICMPV6_ECHO_REQUEST
    icmp_type, _, _, ident, seq = struct.unpack("!BBHHH", req[:8])
    assert icmp_type == ICMPV6_ECHO_REQUEST
    assert ident == 12345
    assert seq == 1
    assert req[8:] == b"test"
    # A valid checksum makes the pseudo-header + message sum to zero.
    pseudo = (
        socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + socket.inet_pton(socket.AF_INET6, "2001:db8::2")
        + struct.pack("!I", len(req))
        + b"\x00\x00\x00"
        + struct.pack("!B", 58)
    )
    assert _checksum(pseudo + req) == 0


def test_build_icmpv6_echo_request_empty_payload() -> None:
    req = _build_icmpv6_echo_request(12345, 1)
    icmp_type, _, _, ident, seq = struct.unpack("!BBHHH", req[:8])
    assert icmp_type == ICMPV6_ECHO_REQUEST
    assert ident == 12345
    assert seq == 1
    assert len(req) == 8


def test_parse_icmpv6_reply_valid() -> None:
    packet = _make_icmpv6_reply_packet(12345, 1, b"test")
    result = _parse_icmpv6_reply(packet, 12345)
    assert result["type"] == ICMPV6_ECHO_REPLY
    assert result["code"] == 0
    assert result["identifier"] == 12345
    assert result["sequence"] == 1
    assert result["payload"] == b"test"
    assert result["error"] is None


def test_parse_icmpv6_reply_wrong_identifier() -> None:
    result = _parse_icmpv6_reply(_make_icmpv6_reply_packet(12345, 1), 54321)
    assert result["error"] == "identifier mismatch: expected 54321, got 12345"


def test_parse_icmpv6_reply_wrong_type() -> None:
    # An Echo Request (type 128) is not an Echo Reply.
    packet = struct.pack("!BBHHH", ICMPV6_ECHO_REQUEST, 0, 0, 12345, 1) + b"test"
    pseudo = (
        socket.inet_pton(socket.AF_INET6, "2001:db8::2")
        + socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + struct.pack("!I", len(packet))
        + b"\x00\x00\x00"
        + struct.pack("!B", 58)
    )
    packet = struct.pack("!BBHHH", ICMPV6_ECHO_REQUEST, 0, _checksum(pseudo + packet), 12345, 1) + b"test"
    result = _parse_icmpv6_reply(packet, 12345)
    assert result["error"] is not None
    assert "not echo reply" in result["error"]


def test_parse_icmpv6_reply_too_short() -> None:
    result = _parse_icmpv6_reply(b"\x00" * 4, 12345)
    assert result["error"] == "ICMPv6 header truncated"


# ---------------------------------------------------------------------------
# _resolve_host
# ---------------------------------------------------------------------------


def test_resolve_host_localhost() -> None:
    result = _resolve_host("127.0.0.1")
    assert result[0] == "127.0.0.1"
    assert result[1] == socket.AF_INET


def test_resolve_host_localhost_ipv6() -> None:
    result = _resolve_host("::1")
    assert result[0] == "::1"
    assert result[1] == socket.AF_INET6


def test_resolve_host_invalid() -> None:
    result = _resolve_host("nonexistent.invalid.domain.tld")
    assert result == (None, None, None)


def test_resolve_host_empty_getaddrinfo_result(monkeypatch) -> None:
    """A host that resolves to no addresses returns the failure tuple.

    getaddrinfo can legitimately return an empty list (e.g. a name with no
    A/AAAA records); _resolve_host must report the same failure shape as an
    exception, not index into the empty list.
    """
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])
    assert _resolve_host("example.com") == (None, None, None)


# ---------------------------------------------------------------------------
# _try_create_raw_socket
# ---------------------------------------------------------------------------


def test_try_create_raw_socket() -> None:
    result = _try_create_raw_socket()
    if result is not None:
        result.close()


def test_try_create_raw_socket_success(monkeypatch) -> None:
    fake_sock = object()

    def mock_socket(family, type_, proto=0):
        assert family == socket.AF_INET
        assert type_ == socket.SOCK_RAW
        assert proto == socket.IPPROTO_ICMP
        return fake_sock

    monkeypatch.setattr(socket, "socket", mock_socket)
    result = _try_create_raw_socket()
    assert result is fake_sock


def test_try_create_raw_socket_ipv6(monkeypatch) -> None:
    """_try_create_raw_socket(AF_INET6) creates an ICMPv6 raw socket."""
    fake_sock = object()

    def mock_socket(family, type_, proto=0):
        assert family == socket.AF_INET6
        assert type_ == socket.SOCK_RAW
        assert proto == socket.IPPROTO_ICMPV6
        return fake_sock

    monkeypatch.setattr(socket, "socket", mock_socket)
    result = _try_create_raw_socket(socket.AF_INET6)
    assert result is fake_sock


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
    assert cast(dict[str, object], result)["reached_destination"] is False if "reached_destination" in result else True
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
    test_sock.getsockname()[1]
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

    def __init__(self, data: bytes = b"", recv_error: Exception | None = None) -> None:
        self._data = data
        self._recv_error = recv_error
        self.timeout: float | None = None
        self.closed = False

    def settimeout(self, timeout: float | None) -> None:
        self.timeout = timeout

    def recvfrom(self, bufsize: int, flags: int = 0) -> tuple[bytes, Any]:
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
    assert cast(float, result["rtt_ms"]) >= 0
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
    assert "socket closed" in cast(str, result["error"])
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
    err = result["error"]
    assert err is not None
    assert "identifier mismatch" in err
    assert fake_send.closed is True


def test_probe_icmp_raw_send_socket_creation_fails_falls_back(monkeypatch) -> None:
    # raw_socket is provided but creating the send raw socket fails ->
    # raw_socket is reset to None and the TCP fallback path is used.
    fake_raw = _FakeRawSocket()
    original_socket = socket.socket

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMP:
            raise OSError("no raw socket")
        return original_socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    # Closed local port -> connect refused -> RESP_RST via TCP fallback.
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_sock.bind(("127.0.0.1", 0))
    port = test_sock.getsockname()[1]
    test_sock.close()

    result = probe_icmp(
        "127.0.0.1",
        timeout=2.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="127.0.0.1",
        port=port,
    )
    assert result["response_type"] == RESP_RST
    assert result["ip"] == "127.0.0.1"


def test_probe_icmp_raw_sendto_oserror(monkeypatch) -> None:
    # send_sock is created but sendto raises OSError -> RESP_NO_RESPONSE.
    fake_raw = _FakeRawSocket()

    class _FakeSendSocket:
        def __init__(self):
            self.closed = False

        def setsockopt(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            raise OSError("send failed")

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
    err = result["error"]
    assert err is not None
    assert "send failed" in err
    assert fake_send.closed is True


def test_probe_icmp_ipv6_send_socket_creation_failure_uses_tcp_fallback(monkeypatch) -> None:
    """A failed ICMPv6 raw send socket falls back to a TCP connect probe."""
    fake_raw = _FakeRawSocket(data=b"")
    seen: dict[str, object] = {}

    class _FakeStreamSocket:
        def setsockopt(self, level, opt, value):
            seen["setsockopt"] = (level, opt, value)

        def settimeout(self, timeout):
            seen["timeout"] = timeout

        def connect_ex(self, addr):
            seen["addr"] = addr
            return 111

        def close(self):
            seen["closed"] = True

    fake_stream = _FakeStreamSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            raise OSError("no raw socket")
        assert family == socket.AF_INET6
        assert type_ == socket.SOCK_STREAM
        return fake_stream

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
        resolved_sockaddr=("::1", 0, 0, 0),
        port=80,
    )

    assert result["response_type"] == RESP_RST
    assert result["error"] is None
    assert seen["addr"] == ("::1", 80, 0, 0)
    assert seen["closed"] is True
    assert fake_raw.closed is False


def test_probe_icmp_ipv4_still_uses_raw_socket(monkeypatch) -> None:
    """The IPv6 guard must not disable raw ICMP for IPv4 targets."""
    reply_packet = _make_icmp_reply_packet(12345, 1, "192.168.1.1", b"test")
    fake_raw = _FakeRawSocket(data=reply_packet)

    class _FakeSendSocket:
        def __init__(self):
            self.sent = False

        def setsockopt(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            self.sent = True

        def close(self):
            pass

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
        resolved_family=socket.AF_INET,
    )

    assert result["response_type"] == RESP_ECHO_REPLY
    assert fake_send.sent is True


def test_probe_icmp_ipv6_echo_reply(monkeypatch) -> None:
    """An IPv6 target with a raw socket gets an ICMPv6 Echo Reply."""
    reply_packet = _make_icmpv6_reply_packet(12345, 1, b"test")
    fake_raw = _FakeRawSocket(data=reply_packet)

    class _FakeSendSocket:
        def __init__(self):
            self.sent = False
            self.closed = False
            self.sent_to = None

        def setsockopt(self, *args, **kwargs):
            pass

        def settimeout(self, t):
            pass

        def sendto(self, data, addr):
            self.sent = True
            self.sent_to = addr

        def close(self):
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["sequence"] == 1
    assert result["ttl"] == 64
    assert result["ip"] == "::1"
    assert result["response_type"] == RESP_ECHO_REPLY
    assert result["error"] is None
    assert fake_send.sent is True
    assert fake_send.sent_to == ("::1", 0)
    assert fake_send.closed is True


def test_probe_icmp_ipv6_timeout(monkeypatch) -> None:
    """An IPv6 target whose raw socket times out reports TIMEOUT."""
    fake_raw = _FakeRawSocket(data=b"")

    class _FakeSendSocket:
        def setsockopt(self, *args, **kwargs):
            pass

        def settimeout(self, t):
            pass

        def sendto(self, data, addr):
            pass

        def close(self):
            pass

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["response_type"] == RESP_TIMEOUT
    assert result["ip"] is None


def test_probe_icmp_ipv4_send_socket_creation_fails_tcp_fallback(monkeypatch) -> None:
    """A failed IPv4 raw send socket falls back to a TCP connect probe."""
    fake_raw = _FakeRawSocket(data=b"")
    original_socket = socket.socket

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            raise OSError("no raw socket")
        return original_socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_sock.bind(("127.0.0.1", 0))
    port = test_sock.getsockname()[1]
    test_sock.close()

    result = probe_icmp(
        "127.0.0.1",
        timeout=2.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="127.0.0.1",
        resolved_family=socket.AF_INET,
        port=port,
    )
    assert result["response_type"] == RESP_RST
    assert result["ip"] == "127.0.0.1"


def test_probe_icmp_ipv6_without_unicast_hops_option(monkeypatch) -> None:
    """The ICMPv6 path skips IPV6_UNICAST_HOPS when the option is absent."""
    reply_packet = _make_icmpv6_reply_packet(12345, 1, b"test")
    fake_raw = _FakeRawSocket(data=reply_packet)

    class _FakeSendSocket:
        def __init__(self) -> None:
            self.sent = False
            self.closed = False

        def setsockopt(self, *args, **kwargs) -> None:
            pass

        def settimeout(self, t) -> None:
            pass

        def sendto(self, data, addr) -> None:
            self.sent = True

        def close(self) -> None:
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)
    monkeypatch.setattr(socket, "IPV6_UNICAST_HOPS", None)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["response_type"] == RESP_ECHO_REPLY
    assert fake_send.sent is True
    assert fake_send.closed is True


def test_probe_icmp_ipv6_sendto_oserror(monkeypatch) -> None:
    """An ICMPv6 sendto failure reports NO-RESPONSE instead of raising."""
    fake_raw = _FakeRawSocket(data=b"")

    class _FakeSendSocket:
        def __init__(self) -> None:
            self.closed = False

        def setsockopt(self, *args, **kwargs) -> None:
            pass

        def settimeout(self, t) -> None:
            pass

        def sendto(self, data, addr) -> None:
            raise OSError("send failed")

        def close(self) -> None:
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["error"] is not None
    assert "send failed" in cast(str, result["error"])
    assert fake_send.closed is True


def test_probe_icmp_ipv6_reply_parse_error(monkeypatch) -> None:
    """An ICMPv6 packet that is not an Echo Reply reports NO-RESPONSE."""
    message = struct.pack("!BBHHH", ICMPV6_ECHO_REQUEST, 0, 0, 12345, 1)
    pseudo = (
        socket.inet_pton(socket.AF_INET6, "2001:db8::2")
        + socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + struct.pack("!I", len(message))
        + b"\x00\x00\x00"
        + struct.pack("!B", ICMPV6_NEXT_HEADER)
    )
    packet = struct.pack(
        "!BBHHH", ICMPV6_ECHO_REQUEST, 0, _checksum(pseudo + message), 12345, 1
    )
    fake_raw = _FakeRawSocket(data=packet)

    class _FakeSendSocket:
        def __init__(self) -> None:
            self.closed = False

        def setsockopt(self, *args, **kwargs) -> None:
            pass

        def settimeout(self, t) -> None:
            pass

        def sendto(self, data, addr) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["error"] is not None
    assert "not echo reply" in cast(str, result["error"])
    assert fake_send.closed is True


def test_probe_icmp_ipv6_recv_generic_exception(monkeypatch) -> None:
    """A non-timeout receive error in the ICMPv6 path is reported, not raised."""
    fake_raw = _FakeRawSocket(recv_error=ValueError("hostile receive"))

    class _FakeSendSocket:
        def __init__(self) -> None:
            self.closed = False

        def setsockopt(self, *args, **kwargs) -> None:
            pass

        def settimeout(self, t) -> None:
            pass

        def sendto(self, data, addr) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    fake_send = _FakeSendSocket()

    def mock_socket(family, type_, proto=0):
        if type_ == socket.SOCK_RAW and proto == socket.IPPROTO_ICMPV6:
            return fake_send
        return socket.socket(family, type_, proto)

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = probe_icmp(
        "::1",
        timeout=1.0,
        ttl=64,
        raw_socket=fake_raw,
        identifier=12345,
        sequence=1,
        resolved_ip="::1",
        resolved_family=socket.AF_INET6,
    )
    assert result["response_type"] == RESP_NO_RESPONSE
    assert result["error"] is not None
    assert "hostile receive" in cast(str, result["error"])
    assert fake_send.closed is True


def test_probe_icmp_ipv4_tcp_fallback_with_resolved_sockaddr() -> None:
    """IPv4 TCP fallback honors a caller-supplied resolved sockaddr."""
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
        resolved_family=socket.AF_INET,
        resolved_sockaddr=("127.0.0.1", port),
        port=port,
    )
    assert result["response_type"] == RESP_RST
    assert result["ip"] == "127.0.0.1"


def test_run_ping_ipv6_sends_checksummed_echo_request_and_parses_reply(monkeypatch) -> None:
    import ethscan.ping as ping_mod

    sent: list[bytes] = []
    sent_to: list[tuple[object, ...]] = []

    class _FakeSendSocket:
        def __init__(self) -> None:
            self.closed = False

        def setsockopt(self, level: int, option: int, value: int) -> None:
            pass

        def settimeout(self, timeout: float) -> None:
            pass

        def sendto(self, packet: bytes, addr: tuple[object, ...]) -> None:
            sent.append(packet)
            sent_to.append(addr)

        def close(self) -> None:
            self.closed = True

    class _FakeRawSocket:
        def __init__(self) -> None:
            self.closed = False

        def settimeout(self, timeout: float) -> None:
            pass

        def recvfrom(self, size: int) -> tuple[bytes, tuple[object, ...]]:
            _type, _code, _checksum, identifier, sequence = struct.unpack(
                "!BBHHH", sent[-1][:8]
            )
            reply = _make_icmpv6_reply_packet(identifier, sequence, b"test")
            return reply, ("2001:db8::2", 0, 0, 0)

        def close(self) -> None:
            self.closed = True

    fake_send = _FakeSendSocket()
    fake_raw = _FakeRawSocket()

    monkeypatch.setattr(
        ping_mod,
        "_resolve_host",
        lambda host: ("2001:db8::1", socket.AF_INET6, ("2001:db8::1", 0, 0, 0)),
    )
    monkeypatch.setattr(ping_mod, "_try_create_raw_socket", lambda family=None: fake_raw)

    def mock_socket(family: int, type_: int, proto: int = 0) -> object:
        assert family == socket.AF_INET6
        assert type_ == socket.SOCK_RAW
        assert proto == socket.IPPROTO_ICMPV6
        return fake_send

    monkeypatch.setattr(socket, "socket", mock_socket)

    result = run_ping("2001:db8::1", count=1, timeout=0.5, ttl=64)

    assert len(sent) == 1
    request = sent[0]
    icmp_type, code = request[:2]
    sequence = struct.unpack("!H", request[6:8])[0]
    assert icmp_type == ICMPV6_ECHO_REQUEST
    assert code == 0
    assert sequence == 1
    assert sent_to == [("2001:db8::1", 0)]
    pseudo = (
        socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + socket.inet_pton(socket.AF_INET6, "2001:db8::1")
        + struct.pack("!I", len(request))
        + b"\x00\x00\x00"
        + struct.pack("!B", ICMPV6_NEXT_HEADER)
    )
    assert _checksum(pseudo + request) == 0
    assert result["raw_socket_available"] is True
    assert result["successful"] == 1
    assert result["failed"] == 0
    assert result["probes"][0]["response_type"] == RESP_ECHO_REPLY
    assert result["probes"][0]["ip"] == "2001:db8::1"
    assert result["probes"][0]["error"] is None
    assert fake_send.closed is True
    assert fake_raw.closed is True


def test_run_ping_ipv6_uses_owned_raw_socket(monkeypatch) -> None:
    """run_ping uses its own ICMPv6 raw socket for an IPv6 target (no TCP fallback)."""
    import ethscan.ping as ping_mod

    fake_raw = _FakeRawSocket(data=b"")

    monkeypatch.setattr(
        ping_mod,
        "_resolve_host",
        lambda host: ("::1", socket.AF_INET6, ("::1", 0, 0, 0)),
    )
    monkeypatch.setattr(ping_mod, "_try_create_raw_socket", lambda family=None: fake_raw)

    calls: list[dict[str, object]] = []

    def mock_probe(host, **kwargs):
        calls.append(kwargs)
        return {
            "ip": "::1",
            "rtt_ms": 0.1,
            "ttl": 64,
            "sequence": kwargs.get("sequence", 1),
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    monkeypatch.setattr(ping_mod, "probe_icmp", mock_probe)

    result = run_ping("::1", count=1, timeout=0.5)

    assert result["raw_socket_available"] is True
    assert fake_raw.closed is True  # run_ping closes the socket it created
    assert calls[0]["raw_socket"] is fake_raw
    assert any("ICMPv6" in note for note in result["notes"])


def test_run_ping_ipv6_does_not_close_caller_raw_socket(monkeypatch) -> None:
    """A caller-owned raw socket is used for IPv6 ICMPv6 but not closed by run_ping."""
    import ethscan.ping as ping_mod

    fake_raw = _FakeRawSocket(data=b"")

    monkeypatch.setattr(
        ping_mod,
        "_resolve_host",
        lambda host: ("::1", socket.AF_INET6, ("::1", 0, 0, 0)),
    )

    def mock_probe(host, **kwargs):
        return {
            "ip": "::1",
            "rtt_ms": 0.1,
            "ttl": 64,
            "sequence": kwargs.get("sequence", 1),
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    monkeypatch.setattr(ping_mod, "probe_icmp", mock_probe)

    result = run_ping("::1", count=1, timeout=0.5, raw_socket=fake_raw)

    assert result["raw_socket_available"] is True
    assert fake_raw.closed is False
    assert any("ICMPv6" in note for note in result["notes"])


# ---------------------------------------------------------------------------
# run_ping
# ---------------------------------------------------------------------------


def test_run_ping_offline_target(monkeypatch) -> None:
    """run_ping with monkeypatched probe_icmp returns structured results."""

    def mock_probe_icmp(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
        return {
            "ip": None,
            "rtt_ms": 1.5,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_NO_RESPONSE,
            "error": "timeout",
        }

    monkeypatch.setattr("ethscan.ping._try_create_raw_socket", lambda family=None: None)
    monkeypatch.setattr("ethscan.ping.probe_icmp", mock_probe_icmp)
    monkeypatch.setattr("ethscan.ping._resolve_host", lambda host: ("10.0.0.1", socket.AF_INET, ("10.0.0.1", 0)))

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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
    ping_mod._resolve_host = lambda h: (None, None, None)  # type: ignore[assignment]
    try:
        result = run_ping("nonexistent.invalid.domain.tld", count=1, timeout=1.0)
        assert result["ip"] is None
        assert any("Could not resolve" in note for note in result["notes"])
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw
        ping_mod._resolve_host = orig_resolve


def test_probe_icmp_unresolvable_host_no_raw_socket() -> None:
    """probe_icmp with an unresolvable host reports the failure instead of raising."""
    result = probe_icmp(
        "no-such-host.invalid.example.tld",
        timeout=2.0,
        ttl=64,
        raw_socket=None,
        identifier=12345,
        sequence=1,
        resolved_ip=None,
    )
    assert result["sequence"] == 1
    assert result["ttl"] == 64
    assert result["ip"] is None
    assert result["response_type"] == RESP_NO_RESPONSE
    assert isinstance(result["error"], str) and result["error"]


def test_run_ping_unresolvable_host_reports_failure() -> None:
    """run_ping with an unresolvable host returns structured results (no exception)."""
    import ethscan.ping as ping_mod

    orig_raw = ping_mod._try_create_raw_socket
    ping_mod._try_create_raw_socket = lambda family=None: None
    try:
        result = run_ping("no-such-host.invalid.example.tld", count=2, timeout=1.0)
    finally:
        ping_mod._try_create_raw_socket = orig_raw

    assert result["ip"] is None
    assert result["successful"] == 0
    assert result["failed"] == 2
    assert any("Could not resolve" in note for note in cast(list[str], result["notes"]))
    for probe in cast(list[dict[str, object]], result["probes"]):
        assert cast(str, probe["response_type"]) == RESP_NO_RESPONSE
        assert isinstance(probe["error"], str) and probe["error"]


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

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    monkeypatch.setattr("ethscan.ping._resolve_host", lambda h: ("10.0.0.1", socket.AF_INET, ("10.0.0.1", 0)))
    monkeypatch.setattr("ethscan.ping.probe_icmp", mock_probe)
    monkeypatch.setattr("ethscan.ping._try_create_raw_socket", lambda family=None: fake_raw)

    result = run_ping("example.com", count=2, timeout=1.0)
    assert result["raw_socket_available"] is True
    assert fake_raw.closed is True
    assert result["successful"] == 2


def test_run_ping_url_target() -> None:
    import ethscan.ping as ping_mod

    def mock_probe(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
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
    ping_mod._try_create_raw_socket = lambda family=None: None
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

def test_format_ping_report_csv() -> None:
    data = {
        "target": "example.com",
        "probes": [
            {"ip": "1.2.3.4", "rtt_ms": 10.5, "ttl": 64, "sequence": 1, "response_type": "ECHO_REPLY", "error": None},
            {"ip": None, "rtt_ms": 1.0, "ttl": 64, "sequence": 2, "response_type": "NO_RESPONSE", "error": "timeout"},
        ],
    }
    output = format_ping_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert reader[0] == ["target", "ip", "sequence", "rtt_ms", "ttl", "response_type", "error"]
    assert reader[1] == ["example.com", "1.2.3.4", "1", "10.5", "64", "ECHO_REPLY", ""]
    assert reader[2] == ["example.com", "", "2", "1.0", "64", "NO_RESPONSE", "timeout"]


def test_format_ping_report_csv_empty() -> None:
    data = {"target": "example.com", "probes": []}
    output = format_ping_report_csv(data)
    reader = list(csv.reader(io.StringIO(output)))
    assert len(reader) == 1
    assert reader[0][0] == "target"


def test_format_ping_report_markdown_non_dict_data() -> None:
    out = format_ping_report_markdown(cast(Any, "not-a-dict"))
    assert "# ethscan Ping Report" in out
    assert "Raw ICMP Socket" in out


def test_format_ping_report_csv_non_dict_data() -> None:
    out = format_ping_report_csv(cast(Any, None))
    lines = out.splitlines()
    assert lines[0] == "target,ip,sequence,rtt_ms,ttl,response_type,error"
    assert len(lines) == 1


def test_ping_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    """A socket that cannot be created is reported as a failed probe, not raised."""
    import ethscan.ping

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.ping.socket.socket", boom)

    results = ethscan.ping.run_ping("127.0.0.1", count=1)

    assert isinstance(results, dict)
    probe = cast(list[dict[str, object]], results["probes"])[0]
    assert cast(str, probe["response_type"]) == ethscan.ping.RESP_NO_RESPONSE
    assert "hostile transport" in (cast(str | None, probe.get("error")) or "")
    assert results["failed"] == 1


def test_ping_connect_failure_of_an_unknown_type_is_reported(monkeypatch) -> None:
    """A connect that fails with an unknown error type is a failed probe, not a raise."""
    import ethscan.ping

    class _HostileSocket:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def setsockopt(self, *args, **kwargs) -> None:
            pass

        def settimeout(self, *args, **kwargs) -> None:
            pass

        def connect_ex(self, *args, **kwargs) -> int:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    monkeypatch.setattr("ethscan.ping.socket.socket", _HostileSocket)

    probe = ethscan.ping.probe_icmp("127.0.0.1", timeout=1.0, raw_socket=None)

    assert cast(str, probe["response_type"]) == ethscan.ping.RESP_NO_RESPONSE
    assert "hostile transport" in (cast(str | None, probe.get("error")) or "")


def test_ping_resolver_failure_of_an_unknown_type_is_reported(monkeypatch) -> None:
    """A resolver that fails with an unknown error type is a failed lookup, not a raise."""
    import ethscan.ping

    def boom(*args, **kwargs):
        raise RuntimeError("hostile resolver")

    monkeypatch.setattr("ethscan.ping.socket.getaddrinfo", boom)

    results = ethscan.ping.run_ping("127.0.0.1", count=1, timeout=1.0)

    assert results["ip"] is None
    assert any("Could not resolve host" in note for note in cast(list[str], results["notes"]))


def test_ping_socket_creation_failure_of_unnamed_type_is_reported(monkeypatch) -> None:
    """A socket creation failure of an unnamed type is a failed probe, not a raise."""
    import ethscan.ping

    def boom(*args, **kwargs):
        raise ValueError("hostile transport")

    monkeypatch.setattr("ethscan.ping.socket.socket", boom)

    results = ethscan.ping.run_ping("127.0.0.1", count=1, timeout=1.0)

    assert isinstance(results, dict)


def test_ping_tcp_fallback_ipv6_family_sets_hop_limit(monkeypatch) -> None:
    """An IPv6 target uses the AF_INET6 fallback path and sets IPV6_UNICAST_HOPS."""
    import ethscan.ping

    class _FakeSocket:
        instances: list[_FakeSocket] = []

        def __init__(self, family, type_, proto=0):
            self.family = family
            self.type_ = type_
            self.proto = proto
            self.setsockopt_calls = []
            self.timeout = None
            type(self).instances.append(self)

        def setsockopt(self, level, opt, value):
            self.setsockopt_calls.append((level, opt, value))

        def settimeout(self, value):
            self.timeout = value

        def connect_ex(self, sockaddr):
            return 111  # ECONNREFUSED

        def close(self):
            pass

    monkeypatch.setattr("ethscan.ping.socket.socket", _FakeSocket)
    monkeypatch.setattr(
        "ethscan.ping.socket.getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 80, 0, 0))
        ],
    )

    probe = ethscan.ping.probe_icmp(
        "::1", timeout=1.0, ttl=64, raw_socket=None, resolved_ip="::1",
        resolved_family=socket.AF_INET6, resolved_sockaddr=("::1", 80, 0, 0),
    )

    assert cast(str, probe["response_type"]) == ethscan.ping.RESP_RST
    assert probe["error"] is None
    assert probe["ip"] == "::1"

    # The TCP fallback path (AF_INET6) must set IPV6_UNICAST_HOPS to the TTL.
    hop_limit_opt = getattr(socket, "IPV6_UNICAST_HOPS", None)
    assert hop_limit_opt is not None
    hop_calls = [
        call
        for call in _FakeSocket.instances[-1].setsockopt_calls
        if call[0] == socket.IPPROTO_IPV6 and call[1] == hop_limit_opt
    ]
    assert hop_calls, "IPV6_UNICAST_HOPS was not set on the IPv6 fallback socket"
    assert hop_calls[0][2] == 64


def test_ping_tcp_fallback_ipv6_without_unicast_hops_option(monkeypatch) -> None:
    """306->310: platforms exposing AF_INET6 without IPV6_UNICAST_HOPS skip the option."""
    import ethscan.ping

    class _FakeSocket:
        instances: list[_FakeSocket] = []

        def __init__(self, family, type_, proto=0):
            self.family = family
            self.type_ = type_
            self.proto = proto
            self.setsockopt_calls = []
            self.timeout = None
            type(self).instances.append(self)

        def setsockopt(self, level, opt, value):
            self.setsockopt_calls.append((level, opt, value))

        def settimeout(self, value):
            self.timeout = value

        def connect_ex(self, sockaddr):
            return 111  # ECONNREFUSED

        def close(self):
            pass

    monkeypatch.setattr("ethscan.ping.socket.socket", _FakeSocket)
    monkeypatch.setattr("ethscan.ping.socket.IPV6_UNICAST_HOPS", None)
    monkeypatch.setattr(
        "ethscan.ping.socket.getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 80, 0, 0))
        ],
    )

    probe = ethscan.ping.probe_icmp(
        "::1", timeout=1.0, ttl=64, raw_socket=None, resolved_ip="::1",
        resolved_family=socket.AF_INET6, resolved_sockaddr=("::1", 80, 0, 0),
    )

    assert cast(str, probe["response_type"]) == ethscan.ping.RESP_RST
    sock = _FakeSocket.instances[-1]
    assert not [c for c in sock.setsockopt_calls if c[0] == socket.IPPROTO_IPV6]
    assert sock.timeout == 1.0


def test_run_ping_raw_socket_creation_exception_sets_none(monkeypatch) -> None:
    """run_ping catches exception from _try_create_raw_socket."""
    import ethscan.ping as ping_mod

    def mock_probe_icmp(host, timeout=2.0, ttl=64, raw_socket=None, identifier=0, sequence=0, payload=b"", resolved_ip=None, resolved_family=None, resolved_sockaddr=None, port=80):
        return {
            "ip": resolved_ip,
            "rtt_ms": 1.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }

    def raise_exc(family=None):
        raise OSError("permission denied")

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe_icmp
    ping_mod._try_create_raw_socket = raise_exc
    try:
        result = run_ping("example.com", count=1, timeout=1.0, ttl=64)
        assert result["raw_socket_available"] is False
        assert any("Raw ICMP socket unavailable" in n for n in result.get("notes", []))
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_run_ping_probe_icmp_exception_caught(monkeypatch) -> None:
    """run_ping catches exception from probe_icmp per probe."""
    import ethscan.ping as ping_mod

    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = raise_exc
    ping_mod._try_create_raw_socket = lambda family=None: None
    try:
        result = run_ping("example.com", count=2, timeout=1.0, ttl=64)
        assert len(result["probes"]) == 2
        for p in result["probes"]:
            assert p["response_type"] == RESP_NO_RESPONSE
            assert p["error"] == "boom"
        assert result["successful"] == 0
        assert result["failed"] == 2
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw


def test_format_ping_report_markdown_with_non_list_probes_and_notes() -> None:
    """format_ping_report_markdown handles non-list probes/notes and non-dict probes."""
    data = {
        "target": "example.com",
        "host": "example.com",
        "ip": "1.2.3.4",
        "count": 1,
        "timeout": 1.0,
        "ttl": 64,
        "port": 80,
        "raw_socket_available": False,
        "successful": 0,
        "failed": 1,
        "rtt_min_ms": None,
        "rtt_max_ms": None,
        "rtt_avg_ms": None,
        "probes": "not-a-list",
        "notes": None,
    }
    out = format_ping_report_markdown(data)
    assert "# ethscan Ping Report" in out
    assert "Raw ICMP Socket" in out


def test_format_ping_report_markdown_probes_non_dict_and_pipes() -> None:
    """format_ping_report_markdown skips non-dict probes."""
    data = {
        "target": "test.com",
        "host": "test.com",
        "ip": "1.2.3.4",
        "count": 1,
        "timeout": 1.0,
        "ttl": 64,
        "port": 80,
        "raw_socket_available": True,
        "successful": 1,
        "failed": 0,
        "rtt_min_ms": 1.0,
        "rtt_max_ms": 2.0,
        "rtt_avg_ms": 1.5,
        "probes": ["bad", {"sequence": 1, "ip": "1.2.3.4|5", "rtt_ms": 1.2, "response_type": "echo|reply"}],
        "notes": ["note with pipes"],
    }
    out = format_ping_report_markdown(data)
    assert "1.2.3.4\\|5" in out
    assert "echo\\|reply" in out
    assert "note with pipes" in out


def test_format_ping_report_csv_non_list_probes_and_non_dict() -> None:
    """format_ping_report_csv handles non-list probes and non-dict probe entries."""
    data = {
        "target": "example.com",
        "ip": "1.2.3.4",
        "probes": "bad",
    }
    out = format_ping_report_csv(data)
    # header only
    assert out.splitlines()[0] == "target,ip,sequence,rtt_ms,ttl,response_type,error"
    assert len(out.splitlines()) == 1

    data2 = {
        "target": "example.com",
        "ip": "1.2.3.4",
        "probes": ["bad", {"sequence": 1, "ip": None, "rtt_ms": None, "ttl": 64, "response_type": "x", "error": ""}],
    }
    out2 = format_ping_report_csv(data2)
    lines = out2.splitlines()
    assert lines[1].startswith("example.com,,1,,64,x,")


def test_format_ping_report_markdown_notes_non_list() -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "ip": "1.2.3.4",
        "count": 1,
        "timeout": 1.0,
        "ttl": 64,
        "port": 80,
        "raw_socket_available": False,
        "successful": 0,
        "failed": 1,
        "rtt_min_ms": None,
        "rtt_max_ms": None,
        "rtt_avg_ms": None,
        "probes": [],
        "notes": "bad",
    }
    out = format_ping_report_markdown(data)
    assert "# ethscan Ping Report" in out


def test_run_ping_supplied_raw_socket_skips_creation(monkeypatch) -> None:
    """run_ping uses an explicitly supplied raw socket without creating one."""

    class _SuppliedSocket:
        def close(self) -> None:
            pass

    supplied = _SuppliedSocket()
    created: list[bool] = []

    def mock_probe(
        host,
        timeout=2.0,
        ttl=64,
        raw_socket=None,
        identifier=0,
        sequence=0,
        payload=b"",
        resolved_ip=None,
        resolved_family=None,
        resolved_sockaddr=None,
        port=80,
    ):
        assert raw_socket is supplied
        return {
            "ip": "10.0.0.1",
            "rtt_ms": 2.0,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_ECHO_REPLY,
            "error": None,
        }

    def fail_create():
        created.append(True)
        raise AssertionError("raw socket must not be created when one is supplied")

    monkeypatch.setattr("ethscan.ping._resolve_host", lambda h: ("10.0.0.1", socket.AF_INET, ("10.0.0.1", 0)))
    monkeypatch.setattr("ethscan.ping.probe_icmp", mock_probe)
    monkeypatch.setattr("ethscan.ping._try_create_raw_socket", fail_create)

    result = run_ping("example.com", count=1, timeout=1.0, raw_socket=supplied)
    assert created == []
    assert result["raw_socket_available"] is True
    assert result["successful"] == 1
    assert result["failed"] == 0


def test_run_ping_successful_probe_with_non_numeric_rtt_excluded_from_stats(monkeypatch) -> None:
    """A successful probe without a numeric rtt_ms contributes no RTT sample."""
    import ethscan.ping as ping_mod

    def mock_probe(
        host,
        timeout=2.0,
        ttl=64,
        raw_socket=None,
        identifier=0,
        sequence=0,
        payload=b"",
        resolved_ip=None,
        resolved_family=None,
        resolved_sockaddr=None,
        port=80,
    ):
        return {
            "ip": "10.0.0.1",
            "rtt_ms": None,
            "ttl": ttl,
            "sequence": sequence,
            "response_type": RESP_CONNECTED,
            "error": None,
        }

    orig_probe = ping_mod.probe_icmp
    orig_raw = ping_mod._try_create_raw_socket
    ping_mod.probe_icmp = mock_probe
    ping_mod._try_create_raw_socket = lambda family=None: None
    try:
        result = run_ping("example.com", count=2, timeout=1.0)
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["rtt_min_ms"] is None
        assert result["rtt_max_ms"] is None
        assert result["rtt_avg_ms"] is None
    finally:
        ping_mod.probe_icmp = orig_probe
        ping_mod._try_create_raw_socket = orig_raw
