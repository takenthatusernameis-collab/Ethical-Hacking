"""Property-based tests for ethscan.redis._parse_info / _parse_config."""
import random


from ethscan.redis import _build_resp_array, _parse_config, _parse_info, _parse_resp


_SEED = 20261128
_INFO_KEYS = ["redis_version", "os", "role", "connected_clients", "used_memory", "uptime_in_seconds"]
_INFO_VALS = ["6.2.0", "Linux", "master", "42", "1024", "100", "# comment value", "a:b", "x\r\ny"]


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


def _encode_info_bulk(info: dict[str, str]) -> bytes:
    lines = []
    for k, v in info.items():
        lines.append(f"{k}:{v}")
    text = "\r\n".join(lines) + ("\r\n" if lines else "")
    bcontent = text.encode("utf-8")
    return b"$" + str(len(bcontent)).encode("ascii") + b"\r\n" + bcontent + b"\r\n"


def test_parse_info_roundtrip_matches_oracle():
    rng = random.Random(_SEED)
    for _ in range(3000):
        n = rng.randint(0, 8)
        info = {}
        for _ in range(n):
            info[rng.choice(_INFO_KEYS)] = rng.choice(_INFO_VALS)
        data = _encode_info_bulk(info)
        resp, _ = _parse_resp(data)
        text = resp if isinstance(resp, str) else (str(resp) if resp is not None else "")
        assert _parse_info(data) == _info_oracle(text)


def test_parse_info_section_headers_and_empty():
    raw = "# Server\r\nredis_version:7.0.0\r\nos:Linux\r\n\r\n# Clients\r\nconnected_clients:3\r\n"
    bcontent = raw.encode("utf-8")
    data = b"$" + str(len(bcontent)).encode("ascii") + b"\r\n" + bcontent + b"\r\n"
    assert _parse_info(data) == {"redis_version": "7.0.0", "os": "Linux", "connected_clients": "3"}
    empty = b"$0\r\n\r\n"
    assert _parse_info(empty) == {}


def test_parse_info_non_bulk_and_error():
    assert _parse_info(b"+OK\r\n") == {}
    assert _parse_info(b"-ERR no such key\r\n") == {}
    assert _parse_info(b"") == {}


def test_parse_config_roundtrip_matches_oracle():
    rng = random.Random(_SEED + 1)
    for _ in range(3000):
        n = rng.randint(0, 6)
        pairs = []
        for _ in range(n):
            k = rng.choice(["bind", "requirepass", "dir", "dbfilename", "maxmemory"])
            v = rng.choice(["0.0.0.0", "", "/data", "dump.rdb", "100mb", None])
            pairs.append((k, v))
        # build RESP array of bulk strings
        flat = []
        for k, v in pairs:
            flat.append(k)
            flat.append("" if v is None else v)
        data = _build_resp_array(*flat)
        got = _parse_config(data)
        # oracle
        expected: dict[str, str] = {}
        if len(flat) % 2 == 0:
            for i in range(0, len(flat), 2):
                kk = flat[i]
                vv = flat[i + 1]
                expected[str(kk)] = "" if vv is None else str(vv)
        assert got == expected


def test_parse_config_odd_length_ignored():
    data = _build_resp_array("a", "b", "c")
    assert _parse_config(data) == {}


def test_parse_config_none_value_becomes_empty():
    data = b"*4\r\n$4\r\nbind\r\n$7\r\n0.0.0.0\r\n$11\r\nrequirepass\r\n$-1\r\n"
    cfg = _parse_config(data)
    assert cfg == {"bind": "0.0.0.0", "requirepass": ""}


def test_parse_config_non_list():
    assert _parse_config(b"+OK\r\n") == {}
    assert _parse_config(b"") == {}
