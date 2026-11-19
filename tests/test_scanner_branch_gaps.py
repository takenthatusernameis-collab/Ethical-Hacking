"""Focused branch-coverage tests for ethscan/scanner.py.

Reproduced with: python -m coverage run --branch --source=ethscan.scanner -m pytest
tests/test_scanner.py tests/test_scanner_hostile_sweep.py tests/test_scanner_formatter_hostile_sweep.py
tests/test_scanner_branch_gaps.py -q
then: python -m coverage report --show-missing --include='ethscan/scanner.py'
Final state: 127 stmts, 0 miss, 52 branch, 0 BrPart (100%).

Reachable partial branches closed by tests in this file:
- 22->24: a successful TCP connect returns (port, True). Prior suites only ever
  exercised the failure path (monkeypatched create_connection) or closed ports;
  the success return at line 24 was never reached.
- 94->95: an empty port token (e.g. ``"80,"``) raises PortSpecError. The
  whitespace test only exercised non-empty tokens after stripping, so the
  `if not part:` guard at line 94 was never true.

No source (ethscan/) changes; purely test additions, fully reversible.
"""
from __future__ import annotations

import socket
import threading

import pytest

from ethscan.scanner import PortSpecError, parse_port_range, scan_port


def test_scan_port_open_local_listener() -> None:
    """Covers 22->24: a successful TCP connect returns (port, True)."""
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
    try:
        result = scan_port("127.0.0.1", port, timeout=1.0)
        assert result == (port, True)
    finally:
        sock.close()
        thread.join(timeout=1.0)


def test_parse_port_range_empty_token() -> None:
    """Covers 94->95: a trailing/empty token raises PortSpecError."""
    with pytest.raises(PortSpecError, match="Empty port token"):
        parse_port_range("80,")