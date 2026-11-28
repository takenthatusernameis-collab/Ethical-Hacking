"""Property-based tests for ethscan.validate._ports_to_ranges.

``_ports_to_ranges`` renders a list of ports as compact range strings
(``80,443,8000-8002``): it int-coerces every element (returning ``""`` on the
first ``TypeError``/``ValueError``), sorts ascending, collapses consecutive
runs into ``start-end``, emits lone ports as ``start``, and joins with
``", "``. Duplicates are kept (not deduplicated), floats are truncated, and
booleans coerce to 0/1. The existing tests only cover a few fixed examples, so
these lock the behaviour -- including the duplicate-run and non-convertible
fallback edges -- against an INDEPENDENT from-scratch oracle that does not call
any ethscan helper.
"""
import random

from ethscan.validate import _ports_to_ranges

_SEED = 20261128

_HOSTILE_ELEMENTS = [
    -10, -1, 0, 1, 80, 443, 8000, 65535, 70000, 10**20, -10**20,  # ints
    "80", "443", "0", "65535",                                    # numeric strings
    "1.5", "notaport", "", "   ", "+80", " 80 ",                  # strings
    None, True, False, 1.5, 2.0, 0.0, -3.7,                       # None/bool/float
]


def _oracle(ports: list) -> str:
    """Independent recomputation of the spec (stdlib only, no ethscan calls)."""
    if not ports:
        return ""
    ints: list[int] = []
    for p in ports:
        try:
            ints.append(int(p))
        except (TypeError, ValueError):
            return ""
    ints.sort()
    runs: list[str] = []
    start = prev = ints[0]
    for port in ints[1:]:
        if port == prev + 1:
            prev = port
        else:
            runs.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = port
    runs.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(runs)


def _gen_ports(rng: random.Random) -> list:
    n = rng.randint(0, 14)
    return [rng.choice(_HOSTILE_ELEMENTS) for _ in range(n)]


def test_ports_to_ranges_matches_oracle_random() -> None:
    rng = random.Random(_SEED)
    for _ in range(30000):
        ports = _gen_ports(rng)
        assert _ports_to_ranges(ports) == _oracle(ports), ports


def test_ports_to_ranges_empty() -> None:
    assert _ports_to_ranges([]) == ""


def test_ports_to_ranges_single() -> None:
    assert _ports_to_ranges([80]) == "80"


def test_ports_to_ranges_multiple_single() -> None:
    assert _ports_to_ranges([80, 443]) == "80, 443"


def test_ports_to_ranges_contiguous() -> None:
    assert _ports_to_ranges([8000, 8001, 8002]) == "8000-8002"


def test_ports_to_ranges_mixed() -> None:
    assert _ports_to_ranges([22, 80, 443, 8000, 8001, 8002]) == (
        "22, 80, 443, 8000-8002"
    )


def test_ports_to_ranges_sorted_input() -> None:
    assert _ports_to_ranges([8000, 8001, 8002, 80]) == "80, 8000-8002"


def test_ports_to_ranges_non_consecutive_break() -> None:
    assert _ports_to_ranges([1, 2, 10]) == "1-2, 10"


def test_ports_to_ranges_duplicates_are_kept() -> None:
    # Duplicates are not deduplicated: a repeated port starts a new run.
    assert _ports_to_ranges([80, 80]) == "80, 80"
    assert _ports_to_ranges([80, 80, 81]) == "80, 80-81"
    assert _ports_to_ranges([5, 5, 5]) == "5, 5, 5"


def test_ports_to_ranges_non_convertible_returns_empty() -> None:
    # Any element that fails int() coercion invalidates the whole list.
    assert _ports_to_ranges(["abc"]) == ""
    assert _ports_to_ranges([None, 1]) == ""
    assert _ports_to_ranges([1, "notaport", 2]) == ""
    assert _ports_to_ranges(["1.5"]) == ""
    assert _ports_to_ranges(["", "   "]) == ""


def test_ports_to_ranges_float_truncation() -> None:
    # int() truncates floats toward zero; numeric strings must be pure digits.
    assert _ports_to_ranges([1.5]) == "1"
    assert _ports_to_ranges([1.9, 2.1]) == "1-2"
    assert _ports_to_ranges([-3.7]) == "-3"


def test_ports_to_ranges_bool_coercion() -> None:
    assert _ports_to_ranges([True, False]) == "0-1"
    assert _ports_to_ranges([False, True]) == "0-1"


def test_ports_to_ranges_negative_and_huge() -> None:
    assert _ports_to_ranges([-5, -4]) == "-5--4"
    assert _ports_to_ranges([-2, 0, 1]) == "-2, 0-1"
    assert _ports_to_ranges([10**20]) == "100000000000000000000"
