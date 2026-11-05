"""Permanent sweep test: a hostile Memcached answer is reported, never raised.

The memcached command talks to servers that answer with whatever they like,
and the transport itself can fail in a way the module does not name. Every
command answers such an answer with a result and reports the failure through
its own failure field, instead of letting it escape as a traceback.
"""
from __future__ import annotations

from typing import Callable

from ethscan import memcached


#: A target that is never reached: every command below drives its own
#: transport, so the target only has to be well formed.
TARGET = "127.0.0.1"

#: The bodies a hostile server can send.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not memcached at all",
    b"VERSION 1.6.22\r\n",
    b"ERROR\r\n",
    b"CLIENT_ERROR bad command line format\r\n",
    b"SERVER_ERROR out of memory\r\n",
    b"END\r\n",
    b"STAT pid 1234\r\nEND\r\n",
    b"hello world",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
    b"STAT " + b"a" * 1000 + b" " + b"b" * 1000 + b"\r\nEND\r\n",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    """Return a connector that answers every request with *body*."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised_version() -> None:
    """A hostile answer to version is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = memcached.run_memcached(TARGET, connector=_connector_for(body), probes=["version"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_stats() -> None:
    """A hostile answer to stats is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = memcached.run_memcached(TARGET, connector=_connector_for(body), probes=["stats"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_all_probes() -> None:
    """A hostile answer to all probes is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = memcached.run_memcached(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised_version() -> None:
    """A transport failure on version is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = memcached.run_memcached(TARGET, connector=connector, probes=["version"])
    assert isinstance(results, dict)
    assert results.get("error")
    assert "version request failed" in results["error"] or "memcached probe failed" in results["error"]


def test_transport_failure_is_reported_not_raised_stats() -> None:
    """A transport failure on stats is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("network unreachable")

    results = memcached.run_memcached(TARGET, connector=connector, probes=["stats"])
    assert isinstance(results, dict)
    assert results.get("error")
    assert "stats request failed" in results["error"] or "memcached probe failed" in results["error"]


def test_transport_failure_is_reported_not_raised_all_probes() -> None:
    """A transport failure during probes is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise RuntimeError("hostile transport")

    results = memcached.run_memcached(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "memcached probe failed" in results["error"] or "request failed" in results["error"]
