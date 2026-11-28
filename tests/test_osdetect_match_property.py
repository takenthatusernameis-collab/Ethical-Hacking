"""Property tests locking ``osdetect._match_os_from_banner`` / ``_match_os_from_ttl``.

These pure helpers decide which OS families are reported from a banner or an
observed TTL. A regression in the pattern search or the range check would
silently report the wrong OS. The existing tests only cover a handful of fixed
examples, so these tests lock the behaviour against an independent oracle.
"""

from __future__ import annotations

import random
import re

from typing import cast

from ethscan.osdetect import OS_SIGNATURES, _match_os_from_banner, _match_os_from_ttl

_PROPERTY_SEED = 20261128


def _oracle_banner(banner: str) -> list[str]:
    out: list[str] = []
    for entry in OS_SIGNATURES:
        for pattern, _label in cast(list[tuple[re.Pattern[str], str]], entry["patterns"]):
            if pattern.search(banner):
                out.append(cast(str, entry["name"]))
                break
    return out


def _oracle_ttl(ttl: int) -> list[str]:
    out: list[str] = []
    for entry in OS_SIGNATURES:
        low, high = cast(tuple[int, int], entry["ttl_range"])
        if low <= ttl <= high:
            out.append(cast(str, entry["name"]))
    return out


def test_match_os_from_banner_matches_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED)
    banners = ["", "Linux 5.4", "Windows Server 2019", "SunOS 5.10", "FreeBSD 12", "Apache/2.4"]
    for _ in range(5000):
        b = rng.choice(banners) + " " + "".join(chr(rng.randrange(32, 127)) for _ in range(rng.randrange(0, 20)))
        assert _match_os_from_banner(b) == _oracle_banner(b)


def test_match_os_from_ttl_matches_oracle() -> None:
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(5000):
        ttl = rng.randrange(-5, 300)
        assert _match_os_from_ttl(ttl) == _oracle_ttl(ttl)


def test_match_os_from_ttl_boundary_values() -> None:
    for ttl in (-1, 0, 1, 64, 128, 255, 256, 1000):
        assert _match_os_from_ttl(ttl) == _oracle_ttl(ttl)


def test_match_os_banner_empty_returns_empty() -> None:
    assert _match_os_from_banner("") == []


def test_os_signatures_names_unique() -> None:
    names = [e["name"] for e in OS_SIGNATURES]
    assert len(names) == len(set(names))
