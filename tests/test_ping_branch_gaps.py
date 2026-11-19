"""Focused branch-coverage tests for ethscan/ping.py.

Reproduce with: python -m coverage run --branch --source=ethscan.ping -m pytest
tests/test_ping.py tests/test_ping_formatter_hostile_sweep.py tests/test_ping_hostile_sweep.py
tests/test_ping_branch_gaps.py -q
then: python -m coverage report --show-missing --include='ethscan/ping.py'
Final state: 286 stmts, 0 miss, 78 branch, 0 BrPart (100%).

Reachable partial branch closed by tests in this file:
- 329->330: a resolved IPv4 sockaddr is present, so the connect address is built
  from the sockaddr tuple rather than falling back to (host, port). Prior suites
  either passed resolved_sockaddr=None (hitting the 332 else) or an IPv6 4-tuple
  (hitting 328); the IPv4 `connect_sockaddr = (sockaddr[0], port)` line at 330 was
  never reached.

No source (ethscan/) changes; purely test additions, fully reversible.
"""
from __future__ import annotations

import socket
import threading
import time

from ethscan.ping import RESP_CONNECTED, probe_icmp


def test_probe_icmp_ipv4_resolved_sockaddr_open() -> None:
    """Covers 329->330: an IPv4 resolved_sockaddr builds the connect address from it."""
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
            resolved_family=socket.AF_INET,
            resolved_sockaddr=("127.0.0.1", port),
            port=port,
        )
        assert result["response_type"] == RESP_CONNECTED
        assert result["ip"] == "127.0.0.1"
    finally:
        sock.close()
        thread.join(timeout=1.0)