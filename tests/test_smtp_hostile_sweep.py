"""Permanent sweep test: a hostile SMTP answer is reported, never raised."""
from __future__ import annotations

from ethscan import smtp


TARGET = "127.0.0.1"


class _HostileSocket:
    def __init__(self, body: bytes):
        self._body = body
        self._sent = False

    def settimeout(self, timeout):
        return None

    def recv(self, size):
        if self._sent:
            return b""
        self._sent = True
        return self._body

    def send(self, data):
        return len(data)

    def close(self):
        return None


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in (b"", b"not smtp", b"\x00\xff", b"220 hostile\r\n"):
        def connector(addr, timeout, body=body):
            return _HostileSocket(body)

        results = smtp.run_smtp(TARGET, check_starttls=False, check_relay=False, connector=connector)
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(addr, timeout):
        raise OSError("connection refused")

    results = smtp.run_smtp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")


def test_unnamed_transport_failure_is_reported_not_raised() -> None:
    def connector(addr, timeout):
        raise RuntimeError("boom")

    results = smtp.run_smtp(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
