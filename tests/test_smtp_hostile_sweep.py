"""Permanent sweep test: a hostile SMTP answer is reported, never raised."""
from __future__ import annotations

from typing import Callable

from ethscan import smtp

TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not smtp at all",
    b"\x00" * 9,
    b"\x00\xff\xfe\xfd",
    b"hello world",
    bytes(range(256)),
)


class _ScriptedSocket:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self._sent = False

    def settimeout(self, _timeout: float) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        return self.body

    def sendall(self, data: bytes) -> None:
        pass

    def close(self) -> None:
        pass

    def makefile(self, *args, **kwargs):
        import io
        return io.BytesIO(self.body)


def _connector_for(body: bytes) -> Callable[..., object]:
    def connector(host, port, timeout):
        return _ScriptedSocket(body)

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = smtp.run_smtp(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host, port, timeout):
        raise OSError("connection refused")

    results = smtp.run_smtp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def connector(host, port, timeout):
        raise RuntimeError("hostile transport")

    results = smtp.run_smtp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
