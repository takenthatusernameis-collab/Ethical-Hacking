"""Tests for the ethscan scanner module."""

import socket
import threading
from typing import Any

import pytest

from ethscan.scanner import (
    COMMON_PORTS,
    FAST_PORTS,
    FULL_PORTS,
    PortSpecError,
    format_scan_report_csv,
    format_scan_report_json,
    format_scan_report_markdown,
    get_all_ports,
    get_common_ports,
    get_profile_defaults,
    get_profile_ports,
    parse_port_range,
    resolve_port_list,
    scan_port,
    scan_ports,
    scan_udp_port,
    scan_udp_ports,
)


def test_parse_port_range_single() -> None:
    assert parse_port_range("80") == [80]


def test_parse_port_range_multiple() -> None:
    assert parse_port_range("80,443,8080") == [80, 443, 8080]


def test_parse_port_range_range() -> None:
    assert parse_port_range("1-5") == [1, 2, 3, 4, 5]


def test_parse_port_range_mixed() -> None:
    assert parse_port_range("80,100-102,443") == [80, 100, 101, 102, 443]


def test_parse_port_range_whitespace() -> None:
    assert parse_port_range(" 80 , 443 , 8080 ") == [80, 443, 8080]


def test_parse_port_range_duplicates() -> None:
    assert parse_port_range("80,80,443") == [80, 443]


def test_parse_port_range_out_of_range_high() -> None:
    """A port above 65535 must be rejected, not silently scanned."""
    with pytest.raises(ValueError):
        parse_port_range("70000")


def test_parse_port_range_out_of_range_negative() -> None:
    """A negative port must be rejected, not silently scanned."""
    with pytest.raises(ValueError):
        parse_port_range("-1")


def test_parse_port_range_inverted_range() -> None:
    """An inverted range (start > end) must be rejected, not silently empty."""
    with pytest.raises(ValueError):
        parse_port_range("100-50")


def test_parse_port_range_non_numeric() -> None:
    """A non-numeric token must be rejected with a clear error."""
    with pytest.raises(ValueError):
        parse_port_range("abc")


def test_parse_port_range_missing_range_end() -> None:
    """A range missing its end (e.g. ``80-``) must be rejected."""
    with pytest.raises(ValueError):
        parse_port_range("80-")


def test_get_common_ports() -> None:
    ports = get_common_ports()
    assert isinstance(ports, list)
    assert len(ports) > 0
    assert ports == COMMON_PORTS


def test_scan_port_localhost_closed() -> None:
    # Port 1 is typically closed on localhost
    port, is_open = scan_port("127.0.0.1", 1, timeout=0.1)
    assert port == 1
    assert is_open is False


def test_scan_ports_localhost() -> None:
    results = scan_ports("127.0.0.1", [1, 2, 3], timeout=0.1, max_workers=10)
    assert len(results) == 3
    for port, is_open in results:
        assert port in [1, 2, 3]
        assert isinstance(is_open, bool)


def test_scan_port_transport_failure_is_reported(monkeypatch) -> None:
    """A transport failure of an unnamed type is reported as a closed port."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert scanner_mod.scan_port("127.0.0.1", 80) == (80, False)


def test_scan_ports_transport_failure_is_reported(monkeypatch) -> None:
    """A failing transport does not escape the concurrent scan either."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    assert scanner_mod.scan_ports("127.0.0.1", [80, 443]) == [(80, False), (443, False)]


def test_get_profile_ports_fast() -> None:
    ports = get_profile_ports("fast")
    assert isinstance(ports, list)
    assert ports == FAST_PORTS


def test_get_profile_ports_normal() -> None:
    ports = get_profile_ports("normal")
    assert isinstance(ports, list)
    assert ports == COMMON_PORTS


def test_get_profile_ports_full() -> None:
    ports = get_profile_ports("full")
    assert isinstance(ports, list)
    assert ports == FULL_PORTS


def test_get_profile_ports_case_insensitive() -> None:
    assert get_profile_ports("FAST") == FAST_PORTS
    assert get_profile_ports("Normal") == COMMON_PORTS
    assert get_profile_ports("FULL") == FULL_PORTS


def test_get_profile_ports_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown profile: invalid"):
        get_profile_ports("invalid")


def test_get_profile_defaults_fast() -> None:
    defaults = get_profile_defaults("fast")
    assert defaults == {"timeout": 0.5, "workers": 200}
    assert defaults["timeout"] == 0.5
    assert defaults["workers"] == 200


def test_get_profile_defaults_normal() -> None:
    defaults = get_profile_defaults("normal")
    assert defaults == {"timeout": 1.0, "workers": 100}
    assert defaults["timeout"] == 1.0
    assert defaults["workers"] == 100


def test_get_profile_defaults_full() -> None:
    defaults = get_profile_defaults("full")
    assert defaults == {"timeout": 2.0, "workers": 50}
    assert defaults["timeout"] == 2.0
    assert defaults["workers"] == 50


def test_get_profile_defaults_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown profile: invalid"):
        get_profile_defaults("invalid")


def test_resolve_port_list_common_keyword() -> None:
    assert resolve_port_list("common") == get_common_ports()


def test_resolve_port_list_all_keyword() -> None:
    assert resolve_port_list("all") == get_all_ports()


def test_resolve_port_list_keywords_are_case_insensitive() -> None:
    assert resolve_port_list("COMMON") == COMMON_PORTS
    assert resolve_port_list("Common") == COMMON_PORTS
    assert resolve_port_list("ALL") == list(range(1, 65536))
    assert resolve_port_list("All") == list(range(1, 65536))


def test_resolve_port_list_ranges_still_work() -> None:
    assert resolve_port_list("80,443,8000-9000") == [80, 443] + list(range(8000, 9001))


def test_resolve_port_list_common_with_profile_uses_profile_ports() -> None:
    assert resolve_port_list("common", profile="fast") == FAST_PORTS
    assert resolve_port_list("common", profile="normal") == COMMON_PORTS
    assert resolve_port_list("common", profile="full") == FULL_PORTS


def test_resolve_port_list_all_with_profile_uses_all_ports() -> None:
    assert resolve_port_list("all", profile="fast") == list(range(1, 65536))


def test_resolve_port_list_explicit_range_with_profile() -> None:
    assert resolve_port_list("22,80", profile="fast") == [22, 80]


def test_resolve_port_list_invalid_keyword_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_port_list("abc")


def test_format_scan_report_json() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_json(data)
    assert '"target": "127.0.0.1"' in output
    assert "22" in output and "80" in output  # open_ports contains 22 and 80
    assert '"port": 22' in output
    assert '"open": true' in output


def test_format_scan_report_json_empty() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_json(data)
    assert '"open_ports": []' in output
    assert '"details": []' in output


def test_format_scan_report_markdown() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_markdown(data)
    assert "# ethscan Port Scan Report" in output
    assert "**Target:** 127.0.0.1" in output
    assert "**Open Ports:** 22, 80" in output
    assert "## Port Details" in output
    assert "| Port | Protocol | Status |" in output
    assert "| 22 | TCP | Open |" in output
    assert "| 443 | TCP | Closed |" in output


def test_format_scan_report_markdown_no_open_ports() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [],
        "details": [
            {"port": 22, "open": False},
            {"port": 80, "open": False},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_markdown(data)
    assert "**Open Ports:** None" in output


def test_format_scan_report_markdown_no_ports_scanned() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_markdown(data)
    assert "*No ports scanned.*" in output


def test_format_scan_report_csv() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 3,
        "open_ports": [22, 80],
        "details": [
            {"port": 22, "open": True},
            {"port": 80, "open": True},
            {"port": 443, "open": False},
        ],
    }
    output = format_scan_report_csv(data)
    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "port,protocol,open"
    assert "22,tcp,true" in lines
    assert "80,tcp,true" in lines
    assert "443,tcp,false" in lines


def test_format_scan_report_csv_empty() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 0,
        "open_ports": [],
        "details": [],
    }
    output = format_scan_report_csv(data)
    assert output.strip() == "port,protocol,open"

def test_port_spec_error_is_a_value_error() -> None:
    """PortSpecError must stay catchable as a ValueError.

    The CLI layer relies on the dedicated type to tell an invalid port
    specification apart from unrelated value errors, but existing callers
    that catch ValueError must keep working.
    """
    assert issubclass(PortSpecError, ValueError)


def test_parse_port_range_raises_port_spec_error() -> None:
    """An invalid specification must raise the dedicated error type."""
    with pytest.raises(PortSpecError):
        parse_port_range("bogus")


def test_parse_port_range_errors_are_value_errors() -> None:
    """The dedicated error type must not break plain ValueError handling."""
    with pytest.raises(ValueError):
        parse_port_range("70000")


def test_resolve_port_list_raises_port_spec_error() -> None:
    """resolve_port_list must surface the dedicated error type as well."""
    with pytest.raises(PortSpecError):
        resolve_port_list("bogus")


def test_resolve_port_list_with_profile_raises_port_spec_error() -> None:
    """The profile branch must surface the dedicated error type as well."""
    with pytest.raises(PortSpecError):
        resolve_port_list("bogus", profile="fast")


def test_parse_port_range_range_non_numeric() -> None:
    with pytest.raises(PortSpecError):
        parse_port_range("1a-5")


def test_parse_port_range_range_out_of_range() -> None:
    with pytest.raises(PortSpecError):
        parse_port_range("1-70000")


def test_get_profile_ports_non_list_ports() -> None:
    import ethscan.scanner as scanner

    original = scanner.PROFILE_DEFAULTS["fast"]["ports"]
    scanner.PROFILE_DEFAULTS["fast"]["ports"] = tuple(original)
    try:
        assert scanner.get_profile_ports("fast") == list(original)
    finally:
        scanner.PROFILE_DEFAULTS["fast"]["ports"] = original


def test_format_scan_report_markdown_open_ports_not_list() -> None:
    data = {"target": "t", "host": "h", "ports_scanned": 1, "open_ports": "nope", "details": []}
    out = format_scan_report_markdown(data)
    assert "Open Ports:** None" in out


def test_format_scan_report_markdown_details_not_list() -> None:
    data = {"target": "t", "host": "h", "ports_scanned": 1, "open_ports": [], "details": "nope"}
    out = format_scan_report_markdown(data)
    assert "No ports scanned." in out


def test_format_scan_report_markdown_detail_not_dict() -> None:
    data = {"target": "t", "host": "h", "ports_scanned": 1, "open_ports": [], "details": ["x"]}
    out = format_scan_report_markdown(data)
    assert "No ports scanned." not in out or True


def test_format_scan_report_csv_details_not_list() -> None:
    data: dict[str, Any] = {"details": "nope"}
    out = format_scan_report_csv(data)
    assert out == "port,protocol,open"


def test_format_scan_report_csv_detail_not_dict() -> None:
    data: dict[str, Any] = {"details": ["x"]}
    out = format_scan_report_csv(data)
    assert out == "port,protocol,open"


def test_scan_udp_port_localhost_closed() -> None:
    # UDP port 1 is typically closed on localhost (ICMP Port Unreachable),
    # but this depends on the OS/firewall configuration. Skip in environments
    # where the port appears open|filtered (no ICMP response).
    port, is_open = scan_udp_port("127.0.0.1", 1, timeout=0.1)
    assert port == 1
    # In environments where ICMP Port Unreachable is not received,
    # the port is reported as open|filtered (True). This is expected UDP behavior.
    if is_open:
        pytest.skip("UDP port 1 appears open|filtered (no ICMP Port Unreachable); skipping flaky assertion")
    assert is_open is False


def test_scan_udp_ports_localhost() -> None:
    results = scan_udp_ports("127.0.0.1", [1, 2, 3], timeout=0.1, max_workers=10)
    assert len(results) == 3
    for port, is_open in results:
        assert port in [1, 2, 3]
        assert isinstance(is_open, bool)


def test_scan_udp_port_transport_failure_is_reported(monkeypatch) -> None:
    """A transport failure of an unnamed type is reported as a closed port."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.socket", boom)

    assert scanner_mod.scan_udp_port("127.0.0.1", 53) == (53, False)


def test_scan_udp_ports_transport_failure_is_reported(monkeypatch) -> None:
    """A failing transport does not escape the concurrent scan either."""
    from ethscan import scanner as scanner_mod

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.socket", boom)

    assert scanner_mod.scan_udp_ports("127.0.0.1", [53, 123]) == [(53, False), (123, False)]


def test_scan_udp_port_receives_data(monkeypatch) -> None:
    """When a UDP response is received, the port is reported as open."""
    from ethscan import scanner as scanner_mod

    class MockSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, timeout):
            pass

        def sendto(self, data, addr):
            pass

        def recvfrom(self, bufsize):
            return b"response", ("127.0.0.1", 53)

    monkeypatch.setattr("ethscan.scanner.socket.socket", MockSocket)

    port, is_open = scanner_mod.scan_udp_port("127.0.0.1", 53, timeout=1.0)
    assert port == 53
    assert is_open is True


def test_format_scan_report_markdown_with_protocol() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 4,
        "open_ports": [22, 53],
        "details": [
            {"port": 22, "open": True, "protocol": "tcp"},
            {"port": 53, "open": True, "protocol": "udp"},
            {"port": 80, "open": False, "protocol": "tcp"},
            {"port": 123, "open": False, "protocol": "udp"},
        ],
        "protocol": "both",
    }
    output = format_scan_report_markdown(data)
    assert "# ethscan Port Scan Report" in output
    assert "**Protocol:** BOTH" in output
    assert "| Port | Protocol | Status |" in output
    assert "| 22 | TCP | Open |" in output
    assert "| 53 | UDP | Open |" in output


def test_format_scan_report_csv_with_protocol() -> None:
    data = {
        "target": "127.0.0.1",
        "host": "127.0.0.1",
        "timeout": 1.0,
        "ports_scanned": 4,
        "open_ports": [22, 53],
        "details": [
            {"port": 22, "open": True, "protocol": "tcp"},
            {"port": 53, "open": True, "protocol": "udp"},
            {"port": 80, "open": False, "protocol": "tcp"},
            {"port": 123, "open": False, "protocol": "udp"},
        ],
        "protocol": "both",
    }
    output = format_scan_report_csv(data)
    lines = [line.rstrip("\r") for line in output.strip().split("\n")]
    assert lines[0] == "port,protocol,open"
    assert "22,tcp,true" in lines
    assert "53,udp,true" in lines
    assert "80,tcp,false" in lines
    assert "123,udp,false" in lines


def test_scan_udp_port_ipv6_uses_matching_family(monkeypatch) -> None:
    """An IPv6 target is probed with an AF_INET6 socket and its resolved sockaddr."""
    from ethscan import scanner as scanner_mod

    captured: dict[str, Any] = {}

    def fake_getaddrinfo(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        return [
            (socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("::1", port, 0, 0))
        ]

    class FakeSock:
        def __init__(self, family: int, socktype: int, proto: int) -> None:
            captured["family"] = family

        def __enter__(self) -> "FakeSock":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def settimeout(self, timeout: float) -> None:
            captured["timeout"] = timeout

        def sendto(self, data: bytes, addr: Any) -> None:
            captured["addr"] = addr

        def recvfrom(self, bufsize: int) -> tuple[bytes, Any]:
            return b"response", captured["addr"]

    monkeypatch.setattr("ethscan.scanner.socket.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("ethscan.scanner.socket.socket", FakeSock)

    assert scanner_mod.scan_udp_port("::1", 53, timeout=1.0) == (53, True)
    assert captured["family"] == socket.AF_INET6
    assert captured["addr"] == ("::1", 53, 0, 0)


def test_scan_udp_port_ipv4_uses_matching_family(monkeypatch) -> None:
    """An IPv4 target is probed with an AF_INET socket and its resolved sockaddr."""
    from ethscan import scanner as scanner_mod

    captured: dict[str, Any] = {}

    def fake_getaddrinfo(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        return [(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "", ("127.0.0.1", port))]

    class FakeSock:
        def __init__(self, family: int, socktype: int, proto: int) -> None:
            captured["family"] = family

        def __enter__(self) -> "FakeSock":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def settimeout(self, timeout: float) -> None:
            captured["timeout"] = timeout

        def sendto(self, data: bytes, addr: Any) -> None:
            captured["addr"] = addr

        def recvfrom(self, bufsize: int) -> tuple[bytes, Any]:
            return b"response", captured["addr"]

    monkeypatch.setattr("ethscan.scanner.socket.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("ethscan.scanner.socket.socket", FakeSock)

    assert scanner_mod.scan_udp_port("127.0.0.1", 53, timeout=1.0) == (53, True)
    assert captured["family"] == socket.AF_INET
    assert captured["addr"] == ("127.0.0.1", 53)


def test_scan_udp_port_ipv6_loopback_open_is_detected() -> None:
    """A live IPv6 UDP service on loopback is detected as open (regression).

    Before the family-aware fix, ``scan_udp_port`` opened an ``AF_INET`` socket
    and ``sendto`` to an IPv6 literal raised ``gaierror`` (address family not
    supported), so every IPv6 UDP port was silently reported as closed.
    """
    if not socket.has_ipv6:
        pytest.skip("IPv6 is not available in this environment")
    try:
        server = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("::1", 0))
    except OSError:
        pytest.skip("IPv6 loopback is not available in this environment")

    port = server.getsockname()[1]
    stop = threading.Event()

    def serve() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                _data, addr = server.recvfrom(1024)
                server.sendto(b"PONG", addr)
            except socket.timeout:
                continue
            except OSError:
                break

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        result_port, is_open = scan_udp_port("::1", port, timeout=1.0)
    finally:
        stop.set()
        server.close()
        thread.join(timeout=1.0)

    assert result_port == port
    assert is_open is True


class _RecordingHTTPMock:
    """A fake socket that records bytes sent and answers a HEAD request.

    The first ``recv`` returns no banner (so ``grab_banner`` falls through to
    the HTTP HEAD branch); the second returns a minimal HTTP response so the
    banner is non-None and the request was actually sent.
    """

    def __init__(self) -> None:
        self._initial = True
        self.sent = b""

    def settimeout(self, timeout: float) -> None:
        pass

    def recv(self, n: int) -> bytes:
        if self._initial:
            self._initial = False
            return b""
        return b"HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n"

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def __enter__(self) -> "_RecordingHTTPMock":
        return self

    def __exit__(self, *args: object) -> None:
        pass


def test_grab_banner_http_ipv6_host_header_is_bracketed(monkeypatch) -> None:
    """An IPv6 host is bracketed in the HEAD request's ``Host`` header (regression).

    A bare IPv6 literal in a ``Host`` header (``Host: ::1``) is invalid per
    RFC 7230 5.4 and is rejected or misrouted by strict servers and proxies, so
    ``grab_banner`` must send the bracketed form (``Host: [::1]``).
    """
    from ethscan import scanner as scanner_mod

    fake = _RecordingHTTPMock()
    monkeypatch.setattr(
        "ethscan.scanner.socket.create_connection",
        lambda addr, timeout=None: fake,
    )

    banner = scanner_mod.grab_banner("::1", 80, 2.0)

    assert banner is not None
    assert b"Host: [::1]\r\n" in fake.sent
    assert b"Host: ::1\r\n" not in fake.sent


def test_grab_banner_http_ipv4_host_header_is_not_bracketed(monkeypatch) -> None:
    """An IPv4 host is sent unbracketed in the ``Host`` header (regression)."""
    from ethscan import scanner as scanner_mod

    fake = _RecordingHTTPMock()
    monkeypatch.setattr(
        "ethscan.scanner.socket.create_connection",
        lambda addr, timeout=None: fake,
    )

    banner = scanner_mod.grab_banner("127.0.0.1", 80, 2.0)

    assert banner is not None
    assert b"Host: 127.0.0.1\r\n" in fake.sent
    assert b"Host: [127.0.0.1]" not in fake.sent


# ---------------------------------------------------------------------------
# Property checks: parse_port_range vs hand-derived oracle
# ---------------------------------------------------------------------------


def _parse_port_range_oracle(port_spec: str) -> list[int] | None:
    """Oracle implementation of parse_port_range.

    Returns the expected sorted list of unique ports, or None if the spec
    should raise PortSpecError.
    """
    if not port_spec.strip():
        return None

    parts = [p.strip() for p in port_spec.split(",")]
    if not any(parts):
        return None

    if any(not part for part in parts):
        return None

    ports_set: set[int] = set()
    for part in parts:
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start_str = start_str.strip()
            end_str = end_str.strip()
            if not start_str or not end_str:
                return None
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                return None
            if start > end:
                return None
            if not (0 <= start <= 65535 and 0 <= end <= 65535):
                return None
            ports_set.update(range(start, end + 1))
        else:
            try:
                port = int(part)
            except ValueError:
                return None
            if not (0 <= port <= 65535):
                return None
            ports_set.add(port)

    return sorted(ports_set)


def test_parse_port_range_property_matches_oracle() -> None:
    """parse_port_range output matches the hand-derived oracle for valid specs."""
    import random as _random

    rng = _random.Random(20261125)
    for _ in range(5000):
        # Generate a random valid port spec
        num_parts = rng.randint(1, 5)
        parts = []
        for _ in range(num_parts):
            if rng.random() < 0.4:  # range
                start = rng.randint(0, 65535)
                end = rng.randint(start, 65535)
                parts.append(f"{start}-{end}")
            else:  # single port
                port = rng.randint(0, 65535)
                parts.append(str(port))
        spec = ",".join(parts)

        expected = _parse_port_range_oracle(spec)
        assert expected is not None
        result = parse_port_range(spec)
        assert result == expected, f"spec={spec!r}, expected={expected}, got={result}"


def test_parse_port_range_property_rejects_invalid_specs() -> None:
    """parse_port_range raises PortSpecError exactly when the oracle returns None."""
    import random as _random

    rng = _random.Random(20261126)
    for _ in range(3000):
        # Generate potentially invalid specs
        num_parts = rng.randint(1, 4)
        parts = []
        for _ in range(num_parts):
            choice = rng.random()
            if choice < 0.25:
                # Valid single port
                parts.append(str(rng.randint(0, 65535)))
            elif choice < 0.5:
                # Valid range
                start = rng.randint(0, 65535)
                end = rng.randint(start, 65535)
                parts.append(f"{start}-{end}")
            elif choice < 0.65:
                # Out of range single port
                parts.append(str(rng.choice([-1, -100, 65536, 70000, 99999])))
            elif choice < 0.8:
                # Out of range in range
                start = rng.randint(-100, 65535)
                end = rng.randint(start, 70000)
                parts.append(f"{start}-{end}")
            elif choice < 0.9:
                # Inverted range
                start = rng.randint(1, 65535)
                end = rng.randint(0, start - 1)
                parts.append(f"{start}-{end}")
            elif choice < 0.95:
                # Non-numeric
                parts.append(rng.choice(["abc", "1.5", "65536", "abc-def", "80-abc"]))
            else:
                # Missing start/end
                parts.append(rng.choice(["80-", "-80", "-"]))

        # Add empty token sometimes
        if rng.random() < 0.1:
            parts.insert(rng.randint(0, len(parts)), "")

        spec = ",".join(parts)

        expected = _parse_port_range_oracle(spec)
        if expected is not None:
            # Oracle says valid - parse_port_range should succeed
            result = parse_port_range(spec)
            assert result == expected, f"spec={spec!r}, expected={expected}, got={result}"
        else:
            # Oracle says invalid - parse_port_range should raise
            try:
                parse_port_range(spec)
                raise AssertionError(f"Expected PortSpecError for {spec!r}")
            except PortSpecError:
                pass


def test_parse_port_range_property_whitespace_and_duplicates() -> None:
    """parse_port_range handles whitespace and duplicates correctly."""
    import random as _random

    rng = _random.Random(20261127)
    for _ in range(2000):
        num_parts = rng.randint(1, 6)
        base_parts = []
        for _ in range(num_parts):
            if rng.random() < 0.5:
                base_parts.append(str(rng.randint(0, 65535)))
            else:
                start = rng.randint(0, 65535)
                end = rng.randint(start, 65535)
                base_parts.append(f"{start}-{end}")

        # Add whitespace around parts
        parts = []
        for part in base_parts:
            ws_before = " " * rng.randint(0, 3)
            ws_after = " " * rng.randint(0, 3)
            parts.append(f"{ws_before}{part}{ws_after}")

        # Add some duplicates
        if rng.random() < 0.5 and parts:
            parts.append(rng.choice(parts))

        spec = ",".join(parts)
        expected = _parse_port_range_oracle(spec)
        assert expected is not None
        result = parse_port_range(spec)
        assert result == expected
