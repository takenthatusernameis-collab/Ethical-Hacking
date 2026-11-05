"""Permanent sweep test: a hostile NetBIOS answer is reported, never raised."""
from __future__ import annotations

from typing import Callable

from ethscan import netbios

TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not netbios at all",
    b"\x00" * 9,
    b"\x00" * 11,  # one byte short of the 12-byte header
    b"\x00" * 12,
    b"\x00" * 47,
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
