"""Property tests locking ``redis._parse_info`` and ``redis._parse_config``.

Both parsers decode untrusted Redis INFO / CONFIG GET responses into dicts.
These tests check them against independent line-oracle implementations.
"""

from __future__ import annotations

import random

import pytest

from ethscan.redis import _parse_config, _parse_info

_PROPERTY_SEED = 20261128


def _build_info_bytes(rng: random.Random) -> tuple[bytes, dict[str, str]]:
    lines = []
    expected: dict[str, str] = {}
    # section headers
    lines.append("# Server")
    for _ in range(rng.randint(0, 6)):
        key = f"key{rng.randint(0, 5)}"
        value = "".join(rng.choice("ab:cd ") for _ in range(rng.randint(0, 8)))
        lines.append(f"{key}:{value}")
        expected[key.strip()] = value.strip()
    # blank lines
    lines.insert(1, "")
    text = "\r\n".join(lines) + "\r\n"
    raw = text.encode("utf-8")
    data = b"$" + str(len(raw)).encode("ascii") + b"\r\n" + raw + b"\r\n"
    return data, expected


def _build_config_bytes(rng: random.Random) -> tuple[bytes, dict[str, str]]:
    n = rng.randint(0, 6)
    pairs: list[tuple[str, str | None]] = []
    expected: dict[str, str] = {}
    for i in range(n):
        key = f"k{i}"
        if rng.random() < 0.3:
            val = None
        else:
            val = "".join(rng.choice("ab ") for _ in range(rng.randint(0, 5)))
        pairs.append((key, val))
        if key is not None:
            expected[str(key)] = "" if val is None else str(val)
    # build RESP array
    out = b"*" + str(2 * len(pairs)).encode("ascii") + b"\r\n"
    for k, v in pairs:
        if k is None:
            out += b"$-1\r\n"
        else:
            raw = k.encode("utf-8")
            out += b"$" + str(len(raw)).encode("ascii") + b"\r\n" + raw + b"\r\n"
        if v is None:
            out += b"$-1\r\n"
        else:
            raw = v.encode("utf-8")
            out += b"$" + str(len(raw)).encode("ascii") + b"\r\n" + raw + b"\r\n"
    return out, expected


def test_parse_info_matches_line_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(3000):
        data, expected = _build_info_bytes(rng)
        assert _parse_info(data) == expected


def test_parse_config_matches_pair_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(3000):
        data, expected = _build_config_bytes(rng)
        assert _parse_config(data) == expected


def test_parse_info_malformed_returns_empty_or_partial() -> None:
    # Must not raise on hostile inputs
    for data in (b"", b"x", b"$-1\r\n", b"+OK\r\n", b"-ERR x\r\n", None):
        try:
            _parse_info(data)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            pytest.fail("_parse_info raised")


def test_parse_config_malformed_returns_empty_or_partial() -> None:
    for data in (b"", b"x", b"*0\r\n", b"+OK\r\n", b"-ERR x\r\n", None):
        try:
            _parse_config(data)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            pytest.fail("_parse_config raised")
