"""Property tests locking the RFC 1071 Internet checksum.

``ping._checksum`` and ``osdetect._checksum`` build the checksum for raw
ICMP/TCP-SYN packets; a wrong value produces a malformed packet that a target
silently drops. Both functions are byte-for-byte identical, yet the previous
``test_checksum_known`` tests only asserted the result was an ``int`` in range,
so correctness was never actually verified. These tests compare both functions
against an independent stdlib-only RFC 1071 oracle and the defining round-trip
property (a buffer that carries its own checksum sums to zero).
"""

from __future__ import annotations

import random
import struct
from collections.abc import Callable

import pytest

from ethscan.osdetect import _checksum as osdetect_checksum
from ethscan.ping import _checksum as ping_checksum

_CHECKSUM_IMPLS: tuple[Callable[[bytes], int], ...] = (
    ping_checksum,
    osdetect_checksum,
)
_PROPERTY_SEED = 20261127


def _ref_checksum(data: bytes) -> int:
    """Independent RFC 1071 oracle using a different summation/folding path."""
    if len(data) % 2:
        data = data + b"\x00"
    words = struct.unpack("!%dH" % (len(data) // 2), data)
    total = sum(words)
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


@pytest.mark.parametrize("checksum", _CHECKSUM_IMPLS)
def test_checksum_matches_rfc1071_oracle(checksum: Callable[[bytes], int]) -> None:
    rng = random.Random(_PROPERTY_SEED)
    for _ in range(2000):
        length = rng.randint(0, 2048)
        data = bytes(rng.getrandbits(8) for _ in range(length))
        assert checksum(data) == _ref_checksum(data)


@pytest.mark.parametrize("checksum", _CHECKSUM_IMPLS)
def test_checksum_round_trip_is_zero(checksum: Callable[[bytes], int]) -> None:
    # Defining property: appending the checksum as the final 16-bit word makes
    # the whole buffer sum to zero. Even-length buffers keep words aligned.
    rng = random.Random(_PROPERTY_SEED + 1)
    for _ in range(2000):
        length = rng.randint(0, 1024) * 2
        data = bytes(rng.getrandbits(8) for _ in range(length))
        full = data + struct.pack("!H", checksum(data))
        assert checksum(full) == 0


@pytest.mark.parametrize("checksum", _CHECKSUM_IMPLS)
def test_checksum_known_vectors(checksum: Callable[[bytes], int]) -> None:
    assert checksum(b"") == 0xFFFF
    assert checksum(b"hello") == 0xBC2D
    assert checksum(b"abc") == 0x3B9D  # odd length, zero-padded
    assert checksum(b"abcd") == 0x3B39
    assert checksum(b"\xff\xff\xff\xff") == 0x0000