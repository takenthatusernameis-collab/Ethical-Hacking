"""Property tests locking ``vuln.version_in_range`` (CVE version-range match).

``version_in_range`` is the security-critical comparison that decides whether a
detected service version falls inside a built-in CVE range (see
``vuln.SERVICE_VULNS`` and ``cve._lookup_cve_id``). A regression in component
parsing, zero-padding, or bound inclusivity would silently mis-classify a
vulnerable version as safe (a false negative) or a safe version as vulnerable
(a false positive). The existing ``test_version_in_range*`` tests only exercise a
handful of fixed vectors, so an off-by-one in an inclusive/exclusive bound or a
length-sensitive comparison of ``1.3`` vs ``1.3.0`` could still slip through.

These tests compare ``version_in_range`` against an *independently* coded oracle
(a from-scratch manual digit scanner plus an explicit three-way compare; it does
not reuse ``_version_tuple``/``_pad_versions``) over randomized versions and
range specs, and over every real ``SERVICE_VULNS`` entry. Further invariants are
locked directly: zero-padding is numeric (not length-sensitive), non-numeric
input never matches, and an over-long numeric component is treated as no
version.
"""

from __future__ import annotations

import random

import pytest

from ethscan.vuln import SERVICE_VULNS, version_in_range

_PROPERTY_SEED = 20261128


def _oracle_tuple(value: object) -> list[int]:
    """Parse a version into a list of ints with a manual digit scan.

    Independent of ``vuln._version_tuple`` (which uses ``re.findall``): a run of
    digits is accumulated by hand and any non-digit flushes the current run.
    """
    out: list[int] = []
    cur = 0
    has = False
    for ch in str(value):
        if ch.isdigit():
            cur = cur * 10 + (ord(ch) - 48)
            has = True
        elif has:
            out.append(cur)
            cur = 0
            has = False
    if has:
        out.append(cur)
    return out


def _oracle_cmp(left: list[int], right: list[int]) -> int:
    """Three-way compare after zero-extending the shorter list."""
    length = max(len(left), len(right))
    a = left + [0] * (length - len(left))
    b = right + [0] * (length - len(right))
    return (a > b) - (a < b)


def _oracle(version: str, spec: dict[str, object]) -> bool:
    parsed = _oracle_tuple(version)
    if not parsed:
        return False
    if "version_min" in spec:
        c = _oracle_cmp(parsed, _oracle_tuple(spec["version_min"]))
        if spec.get("min_inclusive", True):
            if c < 0:
                return False
        elif c <= 0:
            return False
    if "version_max" in spec:
        c = _oracle_cmp(parsed, _oracle_tuple(spec["version_max"]))
        if spec.get("max_inclusive", True):
            if c > 0:
                return False
        elif c >= 0:
            return False
    return True


def _rand_version(rng: random.Random) -> str:
    parts = [str(rng.randint(0, 20)) for _ in range(rng.randint(1, 4))]
    sep = rng.choice([".", ".", ".", "-", "_", ""])
    text = sep.join(parts)
    if rng.random() < 0.2:
        text += rng.choice(["p1", "p2", "rc1", "a", "b", "x9", ""])
    if rng.random() < 0.1:
        text = "v" + text
    return text


def _rand_spec(rng: random.Random) -> dict[str, object]:
    spec: dict[str, object] = {}
    if rng.random() < 0.8:
        spec["version_min"] = _rand_version(rng)
        if rng.random() < 0.5:
            spec["min_inclusive"] = rng.random() < 0.5
    if rng.random() < 0.8:
        spec["version_max"] = _rand_version(rng)
        if rng.random() < 0.5:
            spec["max_inclusive"] = rng.random() < 0.5
    return spec


def test_version_in_range_matches_independent_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(20000):
        version = _rand_version(rng)
        spec = _rand_spec(rng)
        assert version_in_range(version, spec) == _oracle(version, spec), (
            f"version={version!r} spec={spec!r}"
        )


def test_version_in_range_matches_oracle_on_every_db_entry() -> None:
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(20000):
        version = _rand_version(rng)
        for entry in SERVICE_VULNS:
            assert version_in_range(version, entry) == _oracle(version, entry), (
                f"version={version!r} id={entry['id']}"
            )


def test_version_in_range_padding_is_numeric_not_length_sensitive() -> None:
    # 1.3, 1.3.0 and 1.3.0.0 are the same version for both bounds.
    for alias in ("1.3", "1.3.0", "1.3.0.0"):
        assert version_in_range(alias, {"version_min": "1.3", "min_inclusive": True})
        assert version_in_range(alias, {"version_max": "1.3", "max_inclusive": True})
        assert not version_in_range(alias, {"version_min": "1.3", "min_inclusive": False})
        assert not version_in_range(alias, {"version_max": "1.3", "max_inclusive": False})
    # A shorter version is strictly below a longer one with a non-zero tail.
    assert version_in_range("1.3", {"version_min": "1.3.0.1", "min_inclusive": True}) is False
    assert version_in_range("1.3.0.1", {"version_min": "1.3", "min_inclusive": True})


def test_version_in_range_non_numeric_never_matches() -> None:
    rng = random.Random(_PROPERTY_SEED + 2)
    alphabet = "abcXYZ-_. pP"
    for _ in range(5000):
        junk = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        # Only strings with no digit run at all are "no version".
        if _oracle_tuple(junk):
            continue
        assert version_in_range(junk, {"version_max": "9.9"}) is False
        assert version_in_range(junk, {"version_min": "0.0"}) is False


def test_version_in_range_overlong_component_is_no_version() -> None:
    huge = "9" * 5000  # exceeds CPython's int<->str digit limit
    assert version_in_range(huge, {"version_max": "9.9"}) is False
    assert version_in_range(huge, {"version_min": "1.0"}) is False
    # A long run embedded after a valid prefix still poisons the whole version.
    assert version_in_range(f"1.2.{huge}", {"version_max": "9.9"}) is False


@pytest.mark.parametrize(
    ("version", "spec", "expected"),
    [
        ("7.2", {"version_max": "7.3", "max_inclusive": False}, True),
        ("7.3", {"version_max": "7.3", "max_inclusive": False}, False),
        ("7.3", {"version_max": "7.3", "max_inclusive": True}, True),
        ("7.2", {"version_min": "7.3", "min_inclusive": True}, False),
        ("7.3", {"version_min": "7.3", "min_inclusive": False}, False),
        ("7.4", {"version_min": "7.3", "min_inclusive": False}, True),
        ("2.3.4", {"version_min": "2.3.4", "version_max": "2.3.4"}, True),
        ("2.3.5", {"version_min": "2.3.4", "version_max": "2.3.4"}, False),
        ("1.10", {"version_max": "1.9", "max_inclusive": True}, False),
        ("1.9", {"version_max": "1.10", "max_inclusive": True}, True),
    ],
)
def test_version_in_range_known_vectors(
    version: str, spec: dict[str, object], expected: bool
) -> None:
    assert version_in_range(version, spec) is expected
    assert _oracle(version, spec) is expected