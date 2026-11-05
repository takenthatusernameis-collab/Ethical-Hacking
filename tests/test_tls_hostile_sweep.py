"""Permanent sweep test: a hostile TLS transport is reported, never raised.

``ethscan.tls`` probes TLS protocol versions and cipher suites. A hostile
endpoint can fail the handshake or transport in unexpected/unnamed ways, or a
probe can surface malformed negotiated data. ``run_tls``/probe functions must
report failures per probe and never raise; ``run_tls`` must always return a
structured result.
"""
from __future__ import annotations

import pytest

from ethscan import tls


TARGET = "example.com"


@pytest.mark.parametrize("exc_type", [RuntimeError, TypeError, KeyError, ValueError])
def test_version_probe_failure_is_reported_not_raised(exc_type, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise exc_type("hostile transport")

    monkeypatch.setattr(tls, "_probe", boom)

    result = tls.probe_version(TARGET, 443, "TLSv1_2", timeout=1.0)

    assert isinstance(result, dict)
    assert result["version"] == "TLSv1_2"
    assert result["supported"] is False
    assert "hostile transport" in str(result.get("error") or "")


@pytest.mark.parametrize("exc_type", [RuntimeError, TypeError, KeyError, ValueError])
def test_cipher_probe_failure_is_reported_not_raised(exc_type, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise exc_type("hostile transport")

    monkeypatch.setattr(tls, "_probe", boom)

    result = tls.probe_cipher(TARGET, 443, "AES128-GCM-SHA256", timeout=1.0)

    assert isinstance(result, dict)
    assert result["cipher"] == "AES128-GCM-SHA256"
    assert result["supported"] is False
    assert "hostile transport" in str(result.get("error") or "")


def test_probe_returns_none_cipher_reported_not_raised(monkeypatch) -> None:
    monkeypatch.setattr(tls, "_probe", lambda *a, **k: (None, None))

    version = tls.probe_version(TARGET, 443, "TLSv1_2", timeout=1.0)
    cipher = tls.probe_cipher(TARGET, 443, "AES128-GCM-SHA256", timeout=1.0)

    assert version["supported"] is True
    assert version["negotiated_cipher"] is None
    assert cipher["supported"] is True
    assert cipher["negotiated_version"] is None


def test_run_tls_hostile_transport_reported_per_probe(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.tls.socket.create_connection", boom)

    result = tls.run_tls(TARGET, timeout=1.0, max_workers=2)

    assert isinstance(result, dict)
    assert result["host"] == "example.com"
    assert result["versions"]
    assert result["ciphers"]
    for entry in result["versions"]:
        assert entry["supported"] is False
        assert entry["error"]
    for entry in result["ciphers"]:
        assert entry["supported"] is False
        assert entry["error"]


def test_run_tls_mixed_hostile_and_benign_probes(monkeypatch) -> None:
    calls = {"n": 0}

    def flaky(host, port, context, timeout):
        calls["n"] += 1
        if calls["n"] % 2 == 0:
            raise RuntimeError("hostile")
        return "AES128-GCM-SHA256", "TLSv1.2"

    monkeypatch.setattr(tls, "_probe", flaky)

    result = tls.run_tls(
        TARGET, timeout=1.0, versions=["TLSv1_2", "TLSv1_3"], ciphers=["AES128-SHA"], max_workers=1
    )

    assert isinstance(result, dict)
    assert len(result["versions"]) == 2
    assert len(result["ciphers"]) == 1
    statuses = [v["supported"] for v in result["versions"]] + [result["ciphers"][0]["supported"]]
    assert True in statuses
    assert False in statuses
