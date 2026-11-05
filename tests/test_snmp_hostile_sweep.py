"""Permanent sweep test: a hostile SNMP answer is reported, never raised."""
from __future__ import annotations

from typing import Callable

from ethscan import snmp

TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not snmp at all",
    b"\x00" * 9,
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = snmp.run_snmp(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert results.get("error")


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = snmp.run_snmp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
