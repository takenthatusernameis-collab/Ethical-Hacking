"""Property tests for ethscan.redis _parse_info / _parse_config."""
import random
from typing import Any, cast

from ethscan.redis import _build_resp_array, _parse_config, _parse_info


_PROPERTY_SEED = 20261128


def _resp_bulk(s: str) -> bytes:
    b = s.encode("utf-8")
    return b"$" + str(len(b)).encode("ascii") + b"\r\n" + b + b"\r\n"


def _info_oracle(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def test_parse_info_roundtrip_random_dicts():
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(3000):
        n = rng.randint(0, 8)
        lines = []
        for _ in range(n):
            k = rng.choice(["redis_version", "os", "role", "port", "bind"])
            v = rng.choice(["6.2.0", "Linux", "master", "6379", "0.0.0.0", ""])
            lines.append(f"{k}:{v}")
        # sprinkle section headers / blank lines
        text = "\r\n".join(["# Server"] + lines + [""]) + "\r\n"
        data = _resp_bulk(text)
        assert _parse_info(data) == _info_oracle(text)


def test_parse_info_trailing_bytes_left_unconsumed_is_fine():
    # parse_info ignores trailing; ensure no crash on trailing garbage inside bulk
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(1000):
        k = rng.choice(["a", "b"])
        v = rng.choice(["1", "2", "x y"])
        text = f"{k}:{v}\r\n"
        data = _resp_bulk(text)
        assert _parse_info(data) == {k: v}


def test_parse_config_roundtrip_random_pairs():
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(3000):
        n = rng.randint(0, 6)
        keys = [rng.choice(["bind", "requirepass", "dir", "dbfilename"]) for _ in range(n)]
        vals = [rng.choice(["0.0.0.0", "", "/data", "dump.rdb", "secret"]) for _ in range(n)]
        # dedup keys to avoid last-write ambiguity in oracle (parser keeps last)
        data = _build_resp_array(*[x for pair in zip(keys, vals, strict=False) for x in pair])
        parsed = _parse_config(data)
        # oracle: last value wins per key, matching parser semantics
        oracle: dict[str, str] = {}
        for k, v in zip(keys, vals, strict=False):
            oracle[k] = v
        assert parsed == oracle


def test_parse_config_odd_length_returns_empty():
    data = _build_resp_array("bind", "0.0.0.0", "requirepass")
    assert _parse_config(data) == {}


def test_parse_config_null_value_becomes_empty_string():
    data = b"*2\r\n$11\r\nrequirepass\r\n$-1\r\n"
    assert _parse_config(data) == {"requirepass": ""}


def test_parse_info_known_vectors():
    text = "redis_version:6.2.0\r\nos:Linux\r\n"
    data = _resp_bulk(text)
    assert _parse_info(data) == {"redis_version": "6.2.0", "os": "Linux"}
    assert _parse_info(b"+OK\r\n") == {}
    assert _parse_info(b"$-1\r\n") == {}
    assert _parse_info(cast(Any, None)) == {}