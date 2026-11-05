"""Permanent sweep test: a hostile SSH answer is reported, never raised.

Covers the public entry point ``run_ssh`` which takes a hostile transport
answer through its ``connector`` seam. Every body a hostile SSH server can
send yields a result dict with an ``error`` key and never raises; a connector
that blows up is reported the same way.
"""
from __future__ import annotations

from typing import Callable

from ethscan import ssh

TARGET = "127.0.0.1"

#: Bodies a hostile SSH server can send: empty, non-SSH text, truncated
#: packets, garbage bytes, and the full byte range. A body that does not
#: start with ``SSH-`` fails the banner exchange and yields a truthy error.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not ssh at all",
    b"\x00" * 9,
    b"\x00\xff\xfe\xfd",
    b"hello world",
    bytes(range(256)),
    b"\x1bSSH-2.0-fake\r\n",
)


class _ScriptedSocket:
    """A socket stand-in that returns a fixed banner from ``recv``."""

    def __init__(self, banner: bytes) -> None:
        self.banner = banner

    def settimeout(self, _timeout: float) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        return self.banner

    def sendall(self, data: bytes) -> None:
        pass

    def close(self) -> None:
        pass


def _connector_for(body: bytes) -> Callable[..., object]:
    def connector(host: str, port: int, timeout: float):
        return _ScriptedSocket(body)

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = ssh.run_ssh(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_short_hostile_answer_is_reported_with_error() -> None:
    # Bodies that are not an SSH banner must yield a truthy top-level error,
    # never a traceback.
    for body in HOSTILE_BODIES:
        results = ssh.run_ssh(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert results.get("error")


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, timeout: float):
        raise OSError("connection refused")

    results = ssh.run_ssh(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, timeout: float):
        raise RuntimeError("hostile transport")

    results = ssh.run_ssh(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
