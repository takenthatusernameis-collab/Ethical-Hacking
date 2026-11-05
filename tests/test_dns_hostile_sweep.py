"""Permanent sweep test: hostile DNS answers are reported, never raised."""
from __future__ import annotations

import socket


from ethscan import dns


TARGET = "example.com"


def test_hostile_socket_failure_not_raised(monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("network unreachable")

    monkeypatch.setattr(socket, "getaddrinfo", boom)

    for workers in (1, 4):
        result = dns.run_dns(TARGET, workers=workers)
        assert isinstance(result, dict)
        assert result["target"] == TARGET
        assert isinstance(result.get("records"), dict)


def test_hostile_socket_garbage_not_raised(monkeypatch) -> None:
    def garbage(*a, **k):
        return [("garbage",)] * 5

    monkeypatch.setattr(socket, "getaddrinfo", garbage)

    result = dns.run_dns(TARGET, record_types=["A", "AAAA", "MX", "TXT"], workers=3)
    assert isinstance(result, dict)
    assert isinstance(result.get("records"), dict)


def test_hostile_dnspython_failure_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])

    dns_pkg = getattr(dns, "dns", None)
    resolver_mod = getattr(dns_pkg, "resolver", None)
    if dns.DNS_AVAILABLE and resolver_mod is not None:
        class BoomResolver:
            def __init__(self, *a, **k):
                pass

            def resolve(self, *a, **k):
                raise RuntimeError("boom")

        monkeypatch.setattr(resolver_mod, "Resolver", BoomResolver)
    else:
        # Ensure the dnspython path is exercised safely even if a prior test
        # polluted module attributes in an order-dependent way.
        monkeypatch.setattr(dns, "DNS_AVAILABLE", False)

    result = dns.run_dns(TARGET, record_types=["MX", "NS"], server="1.1.1.1", workers=2)
    assert isinstance(result, dict)
    assert isinstance(result.get("records"), dict)
