"""Permanent sweep test: a hostile WHOIS answer is reported, never raised.

``run_whois`` obtains raw WHOIS text via ``query_whois`` (a socket transport)
and parses it. A WHOIS server can return arbitrary bytes (decoded with
replacement), empty responses, oversized payloads, or malformed key/value
lines. Every hostile response must yield a structured result dict and never
raise; a transport failure is reported through the ``error`` field.
"""
from __future__ import annotations

from typing import Callable

import pytest

from ethscan import whois


TARGET = "example.com"

HOSTILE_RAW: tuple[str, ...] = (
    "",
    "\x00",
    "\x00" * 4096,
    "not whois at all",
    "Registrar:\n" * 500,
    "Name Server: " + "a" * 2000 + ".example.com\n",
    "Status: " + ",".join(f"status{i}" for i in range(200)) + "\n",
    "ReferralServer: " + "http://" + "x" * 500 + "\n",
    "%%%ERROR:1: rate limit\n" + "x" * 10000,
    "\r\n".join(f"key{i}: value{i}" for i in range(1000)),
    "Registrar: \ufffd\ufffd\nCreation Date: not-a-date\n",
    # Simulates bytes decoded with errors='replace' from a hostile server.
    "Registrar: \ufffd\x00\ufffe example\nName Server: ns1.\ufffd.com\n",
)


def _mock_query(raw: str) -> Callable[..., str]:
    def query(target: str, server: str = "", port: int = 43, timeout: float = 5.0) -> str:
        return raw

    return query


@pytest.mark.parametrize("raw", HOSTILE_RAW, ids=[f"raw{i}" for i in range(len(HOSTILE_RAW))])
def test_hostile_raw_is_reported_not_raised(monkeypatch, raw: str) -> None:
    monkeypatch.setattr(whois, "query_whois", _mock_query(raw))

    result = whois.run_whois(TARGET)

    assert isinstance(result, dict)
    assert result["target"] == TARGET
    assert "parsed" in result
    assert isinstance(result["parsed"], dict)
    assert "recursive_hops" in result


@pytest.mark.parametrize("raw", HOSTILE_RAW, ids=[f"raw{i}" for i in range(len(HOSTILE_RAW))])
def test_hostile_raw_recursive_is_reported_not_raised(monkeypatch, raw: str) -> None:
    monkeypatch.setattr(whois, "query_whois", _mock_query(raw))

    result = whois.run_whois(TARGET, recursive=True, max_depth=2)

    assert isinstance(result, dict)
    assert result.get("recursive") is True
    assert isinstance(result.get("recursive_hops"), list)


def test_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    def query(target: str, server: str = "", port: int = 43, timeout: float = 5.0) -> str:
        raise OSError("connection refused")

    monkeypatch.setattr(whois, "query_whois", query)

    result = whois.run_whois(TARGET)

    assert isinstance(result, dict)
    assert result.get("error")


def test_unnamed_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    def query(target: str, server: str = "", port: int = 43, timeout: float = 5.0) -> str:
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(whois, "query_whois", query)

    result = whois.run_whois(TARGET)

    assert isinstance(result, dict)
    assert "hostile transport" in (result.get("error") or "")


def test_recursive_hop_transport_failure_is_reported_not_raised(monkeypatch) -> None:
    calls = {"n": 0}

    def query(target: str, server: str = "", port: int = 43, timeout: float = 5.0) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return "Registrar WHOIS Server: whois.registrar.example\n"
        raise RuntimeError("hostile referral transport")

    monkeypatch.setattr(whois, "query_whois", query)

    result = whois.run_whois(TARGET, recursive=True, max_depth=2)

    assert isinstance(result, dict)
    hops = result.get("recursive_hops") or []
    assert isinstance(hops, list)
    assert any(hop.get("error") for hop in hops)
