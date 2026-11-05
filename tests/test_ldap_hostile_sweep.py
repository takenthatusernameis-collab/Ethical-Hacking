"""Permanent sweep test: a hostile LDAP answer is reported, never raised.

Covers the public entry point ``run_ldap`` which takes a hostile transport
answer. Every body a hostile LDAP server can send yields a result dict with
an ``error`` key and never raises; a connector that blows up is reported the
same way.
"""
from __future__ import annotations

from typing import Callable

from ethscan import ldap

TARGET = "127.0.0.1"

#: Bodies a hostile LDAP server can send: empty, non-LDAP text, truncated
#: BER headers, an SEQUENCE with nothing after the tag/length, a truncated
#: TLV, a non-LDAP application tag, and the full byte range.
HOSTILE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not ldap at all",
    b"\x00" * 9,
    b"\x30\x01\x00",  # SEQUENCE, length 1, content missing a messageID TLV
    b"\x30\x02\x01\x00",  # SEQUENCE with just a messageID, nothing after
    b"\x30\x81\x80" + b"\x00" * 128,  # SEQUENCE, long-form length, empty content
    b"\x04\x03abc",  # OCTET_STRING (not a SEQUENCE), not an LDAP message
    b"\x70\x01\x00",  # unknown application tag
    bytes(range(256)),
    b"\x00\xff\xfe\xfd",
)


def _connector_for(body: bytes) -> Callable[..., tuple[bytes | None, str | None]]:
    def connector(host: str, port: int, request: bytes, timeout: float):
        return body, None

    return connector


def test_hostile_answer_is_reported_not_raised() -> None:
    for body in HOSTILE_BODIES:
        results = ldap.run_ldap(TARGET, connector=_connector_for(body))
        assert isinstance(results, dict)
        assert "error" in results


def test_transport_failure_is_reported_not_raised() -> None:
    def connector(host: str, port: int, request: bytes, timeout: float):
        raise OSError("connection refused")

    results = ldap.run_ldap(TARGET, connector=connector)
    assert isinstance(results, dict)
    assert results.get("error")
