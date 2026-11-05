"""Permanent sweep test: a hostile MongoDB answer is reported, never raised."""
from __future__ import annotations

from typing import Callable

from ethscan import mongodb


TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not mongodb at all",
    b"\x00" * 16,
    b"hello world",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
    b"\x10\x00\x00\x00",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised_buildinfo() -> None:
    for body in HOSTILE_BODIES:
        results = mongodb.run_mongodb(TARGET, connector=_connector_for(body), probes=["buildInfo"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_all_probes() -> None:
    for body in HOSTILE_BODIES:
        results = mongodb.run_mongodb(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised_all_probes() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = mongodb.run_mongodb(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
