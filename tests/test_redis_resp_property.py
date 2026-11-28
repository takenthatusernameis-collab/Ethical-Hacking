"""Property tests locking ``redis._parse_resp`` (the RESP response parser).

``_parse_resp`` decodes untrusted bytes read from a (possibly hostile or
malformed) Redis-protocol service, so a regression in length handling, nesting,
or boundary consumption could mis-parse a response, loop forever, or silently
truncate attacker-controlled data. The existing ``test_parse_resp_*`` tests only
exercise a handful of fixed examples, so an off-by-one in ``consumed_bytes``, a
broken nested-array walk, or a wrongly-accepted truncated buffer would still pass
them.

These tests use an *independent* encoder built from scratch (it does not call
``_build_resp_array``): a random RESP value is encoded, then ``_parse_resp`` must
reproduce exactly that value and report ``consumed_bytes == len(encoded)``. Two
further invariants are checked: trailing bytes after a complete value are left
unconsumed, and every strict prefix of a null-free encoding is reported
incomplete (``(None, 0)``).
"""

from __future__ import annotations

import random

import pytest

from ethscan.redis import _build_resp_array, _parse_resp

_PROPERTY_SEED = 20261128


def _encode_resp(value: object) -> bytes:
    """Encode a RESP value from scratch (independent of the module under test)."""
    if value is None:
        return b"$-1\r\n"
    if isinstance(value, bool):  # not generated; guard against accidental use
        raise AssertionError("bool is not a RESP value")
    if isinstance(value, int):
        return b":" + str(value).encode("ascii") + b"\r\n"
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return b"$" + str(len(raw)).encode("ascii") + b"\r\n" + raw + b"\r\n"
    if isinstance(value, list):
        out = b"*" + str(len(value)).encode("ascii") + b"\r\n"
        for item in value:
            out += _encode_resp(item)
        return out
    raise AssertionError(f"unsupported RESP value: {value!r}")


def _rand_value(rng: random.Random, depth: int = 0, allow_null: bool = True) -> object:
    kinds = ["int", "str"]
    if allow_null:
        kinds.append("null")
    if depth < 3:
        kinds.append("array")
    kind = rng.choice(kinds)
    if kind == "int":
        return rng.randint(-(10**6), 10**6)
    if kind == "str":
        alphabet = "hello\r\n\t world!@#"
        return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 16)))
    if kind == "null":
        return None
    return [_rand_value(rng, depth + 1, allow_null) for _ in range(rng.randint(0, 4))]


def _contains_null(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return any(_contains_null(item) for item in value)
    return False


def test_parse_resp_roundtrip_matches_encoder_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(5000):
        value = _rand_value(rng)
        data = _encode_resp(value)
        parsed, consumed = _parse_resp(data)
        assert parsed == value
        assert consumed == len(data)


def test_parse_resp_consumes_exact_prefix() -> None:
    # A complete value followed by trailing bytes must consume only the value.
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(3000):
        value = _rand_value(rng)
        data = _encode_resp(value)
        parsed, consumed = _parse_resp(data + b"TRAILING-BYTES")
        assert parsed == value
        assert consumed == len(data)


def test_parse_resp_truncated_is_incomplete() -> None:
    # Every strict prefix of a null-free encoding is an incomplete buffer.
    # (``$-1`` without its trailing CRLF is handled by a documented defensive
    # branch, so null-free values are used to keep this invariant exact.)
    rng = random.Random(_PROPERTY_SEED + 2)
    checked = 0
    for _ in range(2000):
        value = _rand_value(rng, allow_null=False)
        if _contains_null(value):
            continue
        data = _encode_resp(value)
        for cut in range(1, len(data)):
            parsed, consumed = _parse_resp(data[:cut])
            assert parsed is None
            assert consumed == 0
        checked += 1
    assert checked > 0


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"x",
        b"unknown prefix",
        b"+",  # simple string with no CRLF
        b":",  # integer with no CRLF
        b"$",  # bulk string with no CRLF
        b"$5",  # bulk string length but no CRLF
        b"$5\r\nhel",  # bulk string shorter than declared
        b"*",  # array with no CRLF
        b"*2\r\n:1\r\n",  # array declaring more items than present
        b":notanint\r\n",  # non-numeric integer falls back to a string
    ],
)
def test_parse_resp_invalid_or_incomplete_inputs(data: bytes) -> None:
    parsed, consumed = _parse_resp(data)
    if data == b":notanint\r\n":
        # Documented fallback: a non-numeric integer is returned as its text.
        assert parsed == "notanint"
        assert consumed == len(data)
    else:
        assert parsed is None
        assert consumed == 0


def test_parse_resp_known_vectors() -> None:
    assert _parse_resp(b"+OK\r\n") == ("OK", 5)
    assert _parse_resp(b"-ERR nope\r\n") == ("ERR nope", 11)
    assert _parse_resp(b":42\r\n") == (42, 5)
    assert _parse_resp(b"$5\r\nhello\r\n") == ("hello", 11)
    assert _parse_resp(b"$-1\r\n") == (None, 5)
    assert _parse_resp(b"*0\r\n") == ([], 4)
    ping = _build_resp_array("PING")
    assert _parse_resp(ping) == (["PING"], len(ping))
    info = _build_resp_array("INFO", "server")
    assert _parse_resp(info) == (["INFO", "server"], len(info))


def test_build_resp_array_roundtrips_through_parser() -> None:
    rng = random.Random(_PROPERTY_SEED + 3)
    for _ in range(2000):
        args = [
            "".join(rng.choice("abcXYZ019 _-.") for _ in range(rng.randint(0, 12)))
            for _ in range(rng.randint(0, 5))
        ]
        data = _build_resp_array(*args)
        parsed, consumed = _parse_resp(data)
        assert parsed == args
        assert consumed == len(data)