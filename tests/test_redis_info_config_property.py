"""Property tests locking ``redis._parse_info`` and ``redis._parse_config``.

These helpers decode attacker-controlled Redis INFO/CONFIG responses into
``dict[str, str]``. The existing ``test_parse_info``/``test_parse_config`` tests
only exercise fixed examples, so a regression in line splitting, section-header
skipping, first-colon splitting, or CONFIG's even-length/None-handling would pass
them. An independent from-scratch RESP decoder is used to derive expected results,
so the line-rule logic is checked without re-using the module under test.
"""

from __future__ import annotations

import random

import pytest

from ethscan.redis import _parse_config, _parse_info

_PROPERTY_SEED = 20261128


def _encode_resp(value: object) -> bytes:
    """Encode a RESP value from scratch (independent of ethscan.redis)."""
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


def _rand_string(rng: random.Random) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789 .:_/-"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))


def _rand_info_text(rng: random.Random) -> tuple[str, dict[str, str]]:
    """Build a random INFO body and the expected parsed dict (last line wins).

    Lines are constructed with known keys/values plus section headers, blanks,
    no-colon lines, and values that themselves contain a colon (split must be on
    the first colon only). The expected dict is derived from the constructed
    lines using the same skip/split rules, making it independent ground truth.
    """
    pairs: list[tuple[str, str]] = []
    for _ in range(rng.randint(0, 10)):
        key = _rand_string(rng) or "key"
        value = _rand_string(rng)
        pairs.append((key, value))
    lines: list[str] = []
    if rng.random() < 0.3:
        lines.append("# section")
    for key, value in pairs:
        if rng.random() < 0.1:
            lines.append("")  # blank line skipped
        if rng.random() < 0.1:
            lines.append("# " + _rand_string(rng))  # section header skipped
        if rng.random() < 0.05:
            lines.append(_rand_string(rng))  # no colon -> skipped
        lines.append(f"{key}:{value}")
        if rng.random() < 0.1:
            # value itself contains a colon; split must be on the first colon only
            lines.append(f"{key}:{_rand_string(rng)}:{_rand_string(rng)}")
    if rng.random() < 0.3:
        lines.append("# end")
    text = "\r\n".join(lines) + "\r\n"
    expected: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            expected[k.strip()] = v.strip()
    return text, expected


def _rand_config_items(rng: random.Random) -> list[object]:
    """Build a flat [key, value, ...] list of alternating CONFIG pairs."""
    items: list[object] = []
    for _ in range(rng.randint(0, 8)):
        items.append(_rand_string(rng) or "k")
        choice = rng.random()
        if choice < 0.05:
            items.append(None)  # null value -> ""
        elif choice < 0.15:
            items.append(rng.randint(-(10**6), 10**6))  # int value -> str(int)
        else:
            items.append(_rand_string(rng))
    return items


def _decode_resp(data: bytes):
    """Decode exactly one complete RESP value from *data* (from scratch).

    Returns ``(value, consumed_bytes)``. Raises ``ValueError`` if *data* does
    not begin with a complete, well-formed RESP value. Independent of
    ``ethscan.redis._parse_resp``.
    """
    if not data:
        raise ValueError("empty input")
    prefix = data[0:1]
    try:
        idx = data.index(b"\r\n")
    except ValueError:
        raise ValueError("no CRLF terminator") from None
    if prefix == b"+":
        return data[1:idx].decode("utf-8", errors="replace"), idx + 2
    if prefix == b"-":
        return data[1:idx].decode("utf-8", errors="replace"), idx + 2
    if prefix == b":":
        return int(data[1:idx]), idx + 2
    if prefix == b"$":
        length = int(data[1:idx])
        if length == -1:
            return None, idx + 2
        start = idx + 2
        end = start + length
        if len(data) < end + 2:
            raise ValueError("incomplete bulk string")
        return data[start:end].decode("utf-8", errors="replace"), end + 2
    if prefix == b"*":
        count = int(data[1:idx])
        pos = idx + 2
        items: list[object] = []
        for _ in range(count):
            item, consumed = _decode_resp(data[pos:])
            items.append(item)
            pos += consumed
        return items, pos
    raise ValueError(f"unknown RESP prefix {prefix!r}")


def _oracle_parse_info(data: bytes) -> dict[str, str]:
    """Independently derive the INFO dict that ``_parse_info`` must produce."""
    try:
        value, _ = _decode_resp(data)
    except ValueError:
        return {}
    if isinstance(value, str):
        text = value
    elif value is None:
        text = ""
    else:
        text = str(value)
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _oracle_parse_config(data: bytes) -> dict[str, str]:
    """Independently derive the CONFIG dict that ``_parse_config`` must produce."""
    try:
        value, _ = _decode_resp(data)
    except ValueError:
        return {}
    out: dict[str, str] = {}
    if isinstance(value, list) and len(value) % 2 == 0:
        for i in range(0, len(value), 2):
            k = value[i]
            v = value[i + 1]
            if k is not None:
                out[str(k)] = "" if v is None else str(v)
    return out


def test_parse_info_matches_independent_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(5000):
        text, expected = _rand_info_text(rng)
        data = _encode_resp(text)
        assert _parse_info(data) == expected
        assert _oracle_parse_info(data) == expected


def test_parse_config_matches_independent_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(5000):
        items = _rand_config_items(rng)
        data = _encode_resp(items)
        expected: dict[str, str] = {}
        for i in range(0, len(items), 2):
            k = items[i]
            v = items[i + 1]
            if k is not None:
                expected[str(k)] = "" if v is None else str(v)
        assert _parse_config(data) == expected
        assert _oracle_parse_config(data) == expected


def test_parse_info_handles_simple_string_and_null() -> None:
    # A simple string INFO body and a null bulk string both decode cleanly.
    assert _parse_info(b"+redis_version:6.2.0\r\n") == {"redis_version": "6.2.0"}
    assert _parse_info(b"$-1\r\n") == {}


def test_parse_config_handles_odd_length_and_non_list() -> None:
    # Odd-length arrays and non-list responses yield an empty config.
    assert _parse_config(b"*3\r\n$a\r\n1\r\n$b\r\n2\r\n") == {}
    assert _parse_config(b"+OK\r\n") == {}
    assert _parse_config(b":42\r\n") == {}


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"garbage",
        b"x:y",
        b"$5\r\nhel",  # truncated bulk string
        b"*",          # truncated array header
        b"*2\r\n:1\r\n",  # array declaring more items than present
    ],
)
def test_parse_info_and_config_reject_malformed(data: bytes) -> None:
    assert _parse_info(data) == {}
    assert _parse_config(data) == {}


def test_parse_info_known_vector() -> None:
    content = "redis_version:6.2.0\r\nos:Linux\r\nrole:master\r\n"
    bcontent = content.encode("utf-8")
    data = b"$" + str(len(bcontent)).encode("ascii") + b"\r\n" + bcontent + b"\r\n"
    info = _parse_info(data)
    assert info["redis_version"] == "6.2.0"
    assert info["os"] == "Linux"
    assert info["role"] == "master"


def test_parse_config_known_vector() -> None:
    data = b"*4\r\n$4\r\nbind\r\n$7\r\n0.0.0.0\r\n$11\r\nrequirepass\r\n$0\r\n\r\n"
    cfg = _parse_config(data)
    assert cfg["bind"] == "0.0.0.0"
    assert cfg["requirepass"] == ""
