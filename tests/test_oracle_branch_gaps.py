"""Focused branch-coverage tests for ethscan.oracle.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/oracle.py.

Covered in this file (reachable):
- 429->449: an Accept packet (type 0x02) that carries no version payload
  leaves ``version_data["version"]`` falsy.
"""
from __future__ import annotations

import struct

from ethscan.oracle import run_oracle


def _tns_accept_without_version() -> bytes:
    """Build an 8-byte TNS Accept header with an empty payload."""
    return struct.pack("!HHBBH", 8, 0x0000, 0x02, 0x00, 0x0000)


def test_run_oracle_accept_without_version() -> None:
    # 429->449: a truncated Accept response has no version, so the version
    # assignment branch is skipped and the parse error is surfaced as a finding.
    def connector(
        host: str, port: int, request: bytes, timeout: float
    ) -> tuple[bytes | None, str | None]:
        return _tns_accept_without_version(), None

    results = run_oracle(
        "localhost",
        port=1521,
        timeout=1.0,
        probes=["version"],
        connector=connector,
    )
    assert results["accessible"] is True
    assert results["version"] is None
    assert results["error"] is None
    assert any("Accept payload too short" in f for f in results["findings"])