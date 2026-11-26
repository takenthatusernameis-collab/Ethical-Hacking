"""Property-based oracle test for ``ethscan.dns.run_dns`` record-type filtering.

``run_dns`` accepts a caller-supplied list of record types and must:

* keep only the supported types (``A``, ``AAAA``, ``MX``, ``NS``, ``TXT``,
  ``CNAME``, ``SOA``), matched case-insensitively;
* preserve the caller's input order;
* collapse duplicates that differ only by case (the result is keyed by the
  upper-cased type, so a repeated type yields a single key);
* drop unknown types entirely.

The filtering is a pure function of the input list, so it is checked against
an independent stdlib-only oracle over an explicit edge-case matrix plus a
seeded random matrix. The resolvers are monkeypatched so the test performs no
network I/O and is fully deterministic.
"""

from __future__ import annotations

import random
from typing import Any, cast

import pytest

from ethscan.dns import DEFAULT_DNS_TYPES, run_dns

ALL_SUPPORTED = frozenset({"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"})

# Tokens the random matrix draws from: valid types in mixed case, unknown
# types, an empty string and a non-type token.
_TOKEN_POOL = [
    "A", "a", "AAAA", "aaaa", "MX", "mx", "NS", "ns", "TXT", "txt",
    "CNAME", "cname", "SOA", "soa", "INVALID", "bogus", "", "Aaaa",
]


def _oracle_filter(types: list[str]) -> list[str]:
    """Independent oracle: supported types, upper-cased, order-preserving, deduped."""
    seen: dict[str, None] = {}
    for rtype in types:
        upper = rtype.upper()
        if upper in ALL_SUPPORTED:
            seen.setdefault(upper, None)
    return list(seen)


@pytest.fixture
def _patched_resolvers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the network resolvers with deterministic stubs."""

    def fake_a(domain: str, timeout: float = 2.0) -> list[str]:
        return ["93.184.216.34"]

    def fake_aaaa(domain: str, timeout: float = 2.0) -> list[str]:
        return ["2606:2800::1"]

    def fake_dnspython(domain: str, record_type: str, timeout: float = 2.0) -> list[str]:
        return [f"{record_type}-value"]

    monkeypatch.setattr("ethscan.dns.resolve_a_records", fake_a)
    monkeypatch.setattr("ethscan.dns.resolve_aaaa_records", fake_aaaa)
    monkeypatch.setattr("ethscan.dns.resolve_with_dnspython", fake_dnspython)
    monkeypatch.setattr("ethscan.dns.DNS_AVAILABLE", True)


@pytest.mark.parametrize(
    "types",
    [
        ["A"],
        ["a"],
        ["aaaa", "a"],
        ["A", "a"],
        ["A", "A", "AAAA"],
        ["txt", "TXT", "Txt"],
        ["A", "INVALID"],
        ["INVALID"],
        [],
        ["MX", "NS", "TXT"],
        ["cname", "soa"],
        ["", "A", ""],
        list(ALL_SUPPORTED),
    ],
    ids=lambda t: ",".join(t) if t else "<empty>",
)
def test_run_dns_filtering_matches_oracle(
    _patched_resolvers: None, types: list[str]
) -> None:
    """Filtering must match the oracle for an explicit edge-case matrix."""
    result = cast(dict[str, Any], run_dns("example.com", record_types=types, timeout=0.1))

    records = cast(dict[str, list[str]], result["records"])
    assert list(records.keys()) == _oracle_filter(types)
    # The report echoes the caller's requested types verbatim (not the filtered set).
    assert result["record_types_queried"] == types


def test_run_dns_filtering_default_types(_patched_resolvers: None) -> None:
    """``record_types=None`` uses DEFAULT_DNS_TYPES and filters it the same way."""
    result = cast(dict[str, Any], run_dns("example.com", record_types=None, timeout=0.1))

    records = cast(dict[str, list[str]], result["records"])
    assert list(records.keys()) == _oracle_filter(DEFAULT_DNS_TYPES)
    assert result["record_types_queried"] == DEFAULT_DNS_TYPES


def test_run_dns_filtering_random_matrix(_patched_resolvers: None) -> None:
    """Seeded property test: filtering matches the oracle across random inputs."""
    rng = random.Random(20261126)
    for _ in range(500):
        length = rng.randint(0, 6)
        types = [rng.choice(_TOKEN_POOL) for _ in range(length)]

        result = cast(
            dict[str, Any],
            run_dns("example.com", record_types=types, timeout=0.1),
        )
        records = cast(dict[str, list[str]], result["records"])
        assert list(records.keys()) == _oracle_filter(types), (
            f"filtering mismatch for {types!r}: "
            f"got {list(records.keys())}, expected {_oracle_filter(types)}"
        )
        assert result["record_types_queried"] == types


def test_run_dns_filtering_preserves_order_with_workers(
    _patched_resolvers: None,
) -> None:
    """Concurrent resolution (workers > 1) must still preserve input order."""
    types = ["soa", "a", "TXT", "mx", "AAAA", "cname", "ns"]
    result = cast(
        dict[str, Any],
        run_dns("example.com", record_types=types, timeout=0.1, workers=4),
    )
    records = cast(dict[str, list[str]], result["records"])
    assert list(records.keys()) == _oracle_filter(types)