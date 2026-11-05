"""Permanent sweep test: a hostile SMB answer is reported, never raised.

Covers both public entry points that take a hostile transport answer:
``run_smb`` (SMB1 negotiate) and ``run_smb2`` (SMB2/SMB3 negotiate). Every
body a hostile server can send yields a result dict with an ``error`` key
and never raises; a connector that blows up is reported the same way.
"""
from __future__ import annotations

from typing import Callable

from ethscan import smb

TARGET = "127.0.0.1"

#: Bodies a hostile SMB server can send: empty, non-SMB text, truncated
#: headers, an SMB1 frame with nothing after the magic, an SMB2 frame with
#: nothing after the magic, and the full byte range.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not smb at all",
    b"\x00" * 9,
    b"\xffSMB\x72",
    b"\xfeSMB",
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        for runner in (smb.run_smb, smb.run_smb2):
            results = runner(TARGET, connector=_connector_for(body))
            assert isinstance(results, dict)
            assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    for runner in (smb.run_smb, smb.run_smb2):
        results = runner(TARGET, connector=connector)
        assert isinstance(results, dict)
        assert results.get("error")
