"""Permanent sweep test: a hostile FTP answer is reported, never raised."""
from __future__ import annotations

from typing import Callable

from ethscan import ftp


TARGET = "127.0.0.1"

HOSTILE_BODIES: tuple[object, ...] = (
    "",
    "not ftp at all",
    "\x00" * 9,
    "hello world",
    "220 \x00\xff",
)


def _factory_for(body: object) -> Callable[[], object]:
    class _Client:
        def connect(self, host, port, timeout=30):
            return None

        def getwelcome(self):
            if isinstance(body, BaseException):
                raise body
            return body

        def login(self, user=None, passwd=None):
            return None

        def close(self):
            return None

    def factory():
        return _Client()

    return factory


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = ftp.run_ftp(TARGET, check_anonymous=False, connector=_factory_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def factory():
        raise OSError("connection refused")

    results = ftp.run_ftp(TARGET, connector=factory)
    assert isinstance(results, dict)
    assert results.get("error")


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def factory():
        raise RuntimeError("boom")

    results = ftp.run_ftp(TARGET, connector=factory)
    assert isinstance(results, dict)
    assert results.get("error")
