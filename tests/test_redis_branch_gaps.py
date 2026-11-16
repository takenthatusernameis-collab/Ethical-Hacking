"""Focused branch-coverage tests for ethscan.redis.

Closes reachable partial branches identified in branch-coverage analysis of
ethscan/redis.py.

Covered in this file (reachable):
- 250->247: a CONFIG GET array entry whose key bulk string is null is
  skipped instead of being used as a key.
"""
from __future__ import annotations

from ethscan.redis import _parse_config


def test_parse_config_nil_key_is_skipped() -> None:
    # RESP array of four items: [nil, "foo", "bar", "baz"]. The nil key takes
    # 250->247 (continue), and the following pair is still recorded.
    config = _parse_config(b"*4\r\n$-1\r\n$3\r\nfoo\r\n$3\r\nbar\r\n$3\r\nbaz\r\n")
    assert config == {"bar": "baz"}