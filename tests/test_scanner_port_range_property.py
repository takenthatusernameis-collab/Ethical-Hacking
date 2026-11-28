"""Property tests locking ``scanner.parse_port_range``.

``parse_port_range`` decides exactly which TCP/UDP ports a scan will touch, so
an off-by-one in range expansion, a missed de-duplication, a broken sort, or a
silently-accepted invalid token (out-of-range / inverted / non-numeric) would
make the scanner probe the wrong ports or hide a malformed specification. The
previous ``test_parse_port_range_*`` tests only exercised a handful of fixed
examples, so a regression in any of those behaviours would still pass them.

These tests use an *independent* oracle: valid specifications are built from a
known set of ports (so the expected answer is known by construction, not by
re-running the parser), then ``parse_port_range`` must reproduce exactly that
set, sorted and de-duplicated. Invalid specifications must raise
``PortSpecError`` (a ``ValueError`` subclass).
"""

from __future__ import annotations

import random

import pytest

from ethscan.scanner import MAX_PORT, PortSpecError, parse_port_range

_PROPERTY_SEED = 20261128


def _serialize_spec(rng: random.Random, ports: set[int]) -> str:
    """Render ``ports`` as a port spec using randomised, still-valid formatting.

    Consecutive runs are randomly collapsed into ``start-end`` ranges; the
    tokens are then optionally duplicated and padded with whitespace. The
    resulting spec is guaranteed to denote exactly ``ports``.
    """
    ordered = sorted(ports)
    tokens: list[str] = []
    idx = 0
    while idx < len(ordered):
        if (
            rng.random() < 0.5
            and idx + 1 < len(ordered)
            and ordered[idx + 1] == ordered[idx] + 1
        ):
            end = idx
            while (
                end + 1 < len(ordered)
                and ordered[end + 1] == ordered[end] + 1
                and rng.random() < 0.7
            ):
                end += 1
            tokens.append(f"{ordered[idx]}-{ordered[end]}")
            idx = end + 1
        else:
            tokens.append(str(ordered[idx]))
            idx += 1
    if tokens and rng.random() < 0.5:
        tokens.append(tokens[0])  # duplicate token; set semantics absorb it
    spec = ",".join(tokens)
    if rng.random() < 0.5:
        spec = " " + spec.replace(",", " , ") + " "
    return spec


def test_parse_port_range_matches_constructed_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(5000):
        count = rng.randint(1, 8)
        ports = {rng.randint(0, MAX_PORT) for _ in range(count)}
        spec = _serialize_spec(rng, ports)
        assert parse_port_range(spec) == sorted(ports)


def test_parse_port_range_full_closed_range_endpoints() -> None:
    # The inclusive endpoints 0 and 65535 are the valid boundaries; one past
    # either end must be rejected (never silently scanned).
    assert parse_port_range("0") == [0]
    assert parse_port_range("65535") == [65535]
    assert parse_port_range("0-0") == [0]
    assert parse_port_range("65535-65535") == [65535]
    assert parse_port_range("0-65535") == list(range(0, MAX_PORT + 1))


@pytest.mark.parametrize(
    "spec",
    [
        "-1",
        "65536",
        "70000",
        "100-50",
        "80-",
        "-",
        "abc",
        "",
        "  ",
        "80,,443",
        ",80",
        "1-2-3",
        "1-65536",
        "65536-70000",
        "0-65536",
        "1--2",
        "1,2,,3",
    ],
)
def test_parse_port_range_rejects_invalid_specs(spec: str) -> None:
    with pytest.raises(PortSpecError):
        parse_port_range(spec)


def test_parse_port_range_rejection_is_valueerror() -> None:
    # Callers catch ValueError; PortSpecError must stay a ValueError subclass.
    assert issubclass(PortSpecError, ValueError)
    with pytest.raises(ValueError):
        parse_port_range("65536")


def test_parse_port_range_known_vectors() -> None:
    assert parse_port_range("80") == [80]
    assert parse_port_range("80,443,8080") == [80, 443, 8080]
    assert parse_port_range("1-5") == [1, 2, 3, 4, 5]
    assert parse_port_range("80,100-102,443") == [80, 100, 101, 102, 443]
    assert parse_port_range(" 80 , 443 , 8080 ") == [80, 443, 8080]
    assert parse_port_range("80,80,443") == [80, 443]
    assert parse_port_range("1-3,2-4") == [1, 2, 3, 4]