"""Permanent sweep test: a hostile Redis answer is reported, never raised.

The redis command talks to servers that answer with whatever they like,
and the transport itself can fail in a way the module does not name. Every
command answers such an answer with a result and reports the failure through
its own failure field, instead of letting it escape as a traceback.
"""
from __future__ import annotations

from typing import Callable


from ethscan import redis


#: A target that is never reached: every command below drives its own
#: transport, so the target only has to be well formed.
TARGET = "127.0.0.1"

#: The bodies a hostile server can send.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not resp at all",
    b"+OK\r\n",
    b"-ERR unknown command\r\n",
    b":123\r\n",
    b"$-1\r\n",
    b"$0\r\n\r\n",
    b"*0\r\n",
    b"*2\r\n$1\r\na\r\n",
    b"*1\r\n$-1\r\n",
    b"*2\r\n$3\r\nfoo\r\n:1\r\n",
    b"hello world",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
    b"*1000\r\n" + b"$1\r\na\r\n" * 50,
)


BODY_IDS = [f"body{index}" for index in range(len(HOSTILE_BODIES))]


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    """Return a connector that answers every request with *body*."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised_ping() -> None:
    """A hostile answer to PING is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = redis.run_redis(TARGET, connector=_connector_for(body), probes=["ping"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_info() -> None:
    """A hostile answer to INFO is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = redis.run_redis(TARGET, connector=_connector_for(body), probes=["info"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_config() -> None:
    """A hostile answer to CONFIG is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = redis.run_redis(TARGET, connector=_connector_for(body), probes=["config"])
        assert isinstance(results, dict)
        assert "error" in results


def test_hostile_answer_is_reported_not_raised_all_probes() -> None:
    """A hostile answer to all probes is reported, never raised."""
    for body in HOSTILE_BODIES:
        results = redis.run_redis(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised_ping() -> None:
    """A transport failure on PING is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = redis.run_redis(TARGET, connector=connector, probes=["ping"])
    assert isinstance(results, dict)
    assert results.get("error")
    assert "ping request failed" in results["error"] or "redis probe failed" in results["error"]


def test_transport_failure_is_reported_not_raised_info() -> None:
    """A transport failure on INFO is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("network unreachable")

    results = redis.run_redis(TARGET, connector=connector, probes=["info"])
    assert isinstance(results, dict)
    assert results.get("error")
    assert "info request failed" in results["error"] or "redis probe failed" in results["error"]


def test_transport_failure_is_reported_not_raised_config() -> None:
    """A transport failure on CONFIG is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise ConnectionError("host unreachable")

    results = redis.run_redis(TARGET, connector=connector, probes=["config"])
    assert isinstance(results, dict)
    assert results.get("error")
    assert "config request failed" in results["error"] or "redis probe failed" in results["error"]


def test_transport_failure_is_reported_not_raised_all_probes() -> None:
    """A transport failure during probes is reported through the module's error field."""

    def connector(host: str, port: int, request: bytes, timeout: float):
        raise RuntimeError("hostile transport")

    results = redis.run_redis(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
    assert "redis probe failed" in results["error"] or "request failed" in results["error"]
