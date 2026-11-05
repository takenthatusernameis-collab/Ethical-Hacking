"""Permanent sweep test: a hostile NetBIOS answer is reported, never raised.

Covers the public entry point ``run_netbios`` which takes a hostile transport
answer. Every body a hostile NetBIOS server can send yields a result dict with
an ``error`` key and never raises; a connector that blows up is reported the
same way.
"""
from __future__ import annotations

from typing import Callable

from ethscan import netbios

TARGET = "127.0.0.1"

#: Bodies a hostile NetBIOS server can send: empty, non-NetBIOS text, truncated
#: packets (shorter than the 12-byte NBNS header), a parseable query echo, and
#: the full byte range.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not netbios at all",
    b"\x00" * 9,
    b"\x00" * 11,  # one byte short of the 12-byte NBNS header
    b"\x00" * 12,
    b"\x00" * 47,  # 47 bytes: still short of a meaningful NBSTAT RDATA
    b"\x02\x01\x00\x00\x00\x00\x01\x00\x00",
    b"hello world",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = netbios.run_netbios(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_short_hostile_answer_is_reported_with_error() -> None:
    # Bodies shorter than a full NBNS header / meaningful response must yield a
    # truthy top-level error, never a traceback.
    for body in (b"", b"not netbios at all", b"\x00" * 9, b"\x00" * 11, b"\x00\xff\xfe\xfd"):
        results = netbios.run_netbios(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert results.get("error")


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = netbios.run_netbios(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "node status request failed" in results["error"]


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise RuntimeError("hostile transport")

    results = netbios.run_netbios(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "node status request failed" in results["error"]