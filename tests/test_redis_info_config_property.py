"""Property tests for redis._parse_info and redis._parse_config."""
import random

from ethscan.redis import _parse_config, _parse_info, _build_resp_array


_PROPERTY_SEED = 20261128


def _bulk(data: bytes) -> bytes:
    return b"$" + str(len(data)).encode("ascii") + b"\r\n" + data + b"\r\n"


def test_parse_info_matches_line_oracle():
    rng = random.Random(_PROPERTY_SEED)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    for _ in range(3000):
        n_lines = rng.randint(0, 12)
        lines = []
        expected = {}
        for _ in range(n_lines):
            choice = rng.randint(0, 4)
            if choice == 0:
                # section header
                lines.append("# " + "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 6))))
            elif choice == 1:
                # blank line
                lines.append("")
            elif choice == 2:
                # line without colon -> skipped
                key = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 6)))
                lines.append(key)
            else:
                key = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 8)))
                value = "".join(rng.choice(alphabet + " ") for _ in range(rng.randint(0, 10)))
                # possibly surrounding spaces
                raw_key = " " + key + " " if rng.random() < 0.3 else key
                raw_val = " " + value + " " if rng.random() < 0.3 else value
                lines.append(f"{raw_key}:{raw_val}")
                expected[key.strip()] = value.strip()
        content = "\r\n".join(lines)
        if lines:
            content += "\r\n"
        bcontent = content.encode("utf-8")
        data = _bulk(bcontent)
        got = _parse_info(data)
        assert got == expected, (content, got, expected)


def test_parse_info_truncated_or_malformed_is_empty_or_partial_safe():
    # malformed inputs must never raise
    for data in (b"", b"$-1\r\n", b"+OK\r\n", b"-ERR x\r\n", b"*0\r\n", b"\r\n", b":\r\n"):
        _parse_info(data)


def test_parse_config_matches_pair_oracle():
    rng = random.Random(_PROPERTY_SEED + 1)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    for _ in range(3000):
        n_pairs = rng.randint(0, 8)
        args = []
        expected = {}
        # randomly make odd count sometimes
        odd = rng.random() < 0.2
        total = n_pairs * 2 + (1 if odd else 0)
        for _i in range(total):
            token = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 6)))
            args.append(token)
        # rebuild expected from pairs
        expected = {}
        for i in range(0, len(args) - 1, 2):
            k = args[i]
            v = args[i + 1]
            expected[str(k)] = str(v)
        if odd:
            # odd length -> empty dict
            expected = {}
        data = _build_resp_array(*args) if args else b"*0\r\n"
        got = _parse_config(data)
        assert got == expected, (args, got, expected)


def test_parse_config_null_value_becomes_empty_string():
    data = b"*2\r\n$4\r\nbind\r\n$-1\r\n"
    assert _parse_config(data) == {"bind": ""}


def test_parse_config_known_vectors():
    data = b"*4\r\n$4\r\nbind\r\n$7\r\n0.0.0.0\r\n$11\r\nrequirepass\r\n$0\r\n\r\n"
    assert _parse_config(data) == {"bind": "0.0.0.0", "requirepass": ""}