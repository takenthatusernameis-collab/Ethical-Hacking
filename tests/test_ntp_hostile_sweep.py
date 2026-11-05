"""Permanent sweep test: a hostile NTP answer is reported, never raised.

Covers the public entry point ``run_ntp`` which takes a hostile transport
answer. Every body a hostile NTP server can send yields a result dict with
an ``error`` key and never raises; a connector that blows up is reported the
same way.
"""
from __future__ import annotations

from typing import Callable

from ethscan import ntp

TARGET = "127.0.0.1"

#: Bodies a hostile NTP server can send: empty, non-NTP text, truncated
#: packets (shorter than the 48-byte time packet / 12-byte control packet),
#: a parseable time response, and the full byte range.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not ntp at all",
    b"\x00" * 9,
    b"\x00" * 47,  # one byte short of a 48-byte time packet
    b"\x1c\x02\x04\xf4\x00\x00\x40\x00\x00\x00\x20\x09" + b"\x00" * 36,  # 48-byte time-like packet
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = ntp.run_ntp(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_short_hostile_answer_is_reported_with_error() -> None:
    # Bodies shorter than a 48-byte NTP time packet must yield a truthy
    # top-level error, never a traceback.
    for body in (b"", b"not ntp at all", b"\x00" * 9, b"\x00" * 47, b"\x00\xff\xfe\xfd"):
        results = ntp.run_ntp(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert results.get("error")


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = ntp.run_ntp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "ntp probe failed" in results["error"]


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise RuntimeError("hostile transport")

    results = ntp.run_ntp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "ntp probe failed" in results["error"]
