"""Focused branch-coverage tests for ethscan.mysql.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/mysql.py over tests/test_mysql.py and
tests/test_mysql_hostile_sweep.py.

Covered in this file (reachable):
- 58->73: _normalize_target("[::1") bracketed host with no closing bracket
"""
from __future__ import annotations

from ethscan.mysql import DEFAULT_PORT, _normalize_target


def test_normalize_target_bracket_without_close() -> None:
    # 58->73: "[::1" starts with "[" but has no closing "]", so
    # close == -1 and the bracket-port branch is skipped; the host is
    # returned verbatim.
    host, port = _normalize_target("[::1")
    assert host == "[::1"
    assert port == DEFAULT_PORT
