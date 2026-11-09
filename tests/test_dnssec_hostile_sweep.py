"""Permanent sweep test: a hostile DNSSEC answer is reported, never raised.

Covers ``run_dnssec`` with hostile transport/resolver injection seams. Every
hostile response a DNS server can send yields a result dict and never raises;
a connector that blows up is reported the same way.
"""
from __future__ import annotations

from typing import cast

from ethscan import dnssec

TARGET = "example.com"

HOSTILE_BODIES: tuple[bytes | None, ...] = (
    b"",
    b"not dns at all",
    b"\x00" * 12,
    b"\x00" * 512,
    b"\xff" * 64,
    bytes(range(256)),
    None,
)


def _hostile_udp(body: bytes | None):
    def udp_query(nameserver: str, query: bytes, timeout: float):
        return body

    return udp_query


def _hostile_tcp(body: bytes | None):
    def tcp_query(nameserver: str, query: bytes, timeout: float):
        return body

    return tcp_query


def test_hostile_answer_is_reported_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(dnssec, "DNS_AVAILABLE", False)
    for body in HOSTILE_BODIES:
        results = dnssec.run_dnssec(
            TARGET,
            nameserver_resolver=lambda domain, timeout: ["127.0.0.1"],
            udp_query=_hostile_udp(body),
            tcp_query=_hostile_tcp(body),
        )
        assert isinstance(results, dict)
        assert "validated" in results


def test_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(dnssec, "DNS_AVAILABLE", False)

    def udp_query(nameserver: str, query: bytes, timeout: float):
        raise OSError("connection refused")

    results = dnssec.run_dnssec(
        TARGET,
        nameserver_resolver=lambda domain, timeout: ["127.0.0.1"],
        udp_query=udp_query,
    )
    assert isinstance(results, dict)
    dnskey = cast(dict[str, object] | None, results.get("dnskey"))
    assert "error" in (dnskey or {})


def test_unnamed_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(dnssec, "DNS_AVAILABLE", False)

    def udp_query(nameserver: str, query: bytes, timeout: float):
        raise RuntimeError("hostile transport")

    results = dnssec.run_dnssec(
        TARGET,
        nameserver_resolver=lambda domain, timeout: ["127.0.0.1"],
        udp_query=udp_query,
    )
    assert isinstance(results, dict)
    dnskey = cast(dict[str, object] | None, results.get("dnskey"))
    assert "error" in (dnskey or {})


def test_resolver_failure_is_reported_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(dnssec, "DNS_AVAILABLE", False)

    def resolver(domain: str, timeout: float):
        raise RuntimeError("hostile resolver")

    results = dnssec.run_dnssec(TARGET, nameserver_resolver=resolver)
    assert isinstance(results, dict)
    dnskey = cast(dict[str, object] | None, results.get("dnskey"))
    assert "error" in (dnskey or {})
