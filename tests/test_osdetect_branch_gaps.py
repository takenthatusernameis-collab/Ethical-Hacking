"""Branch-gap tests for ethscan.osdetect.

Covers the remaining partial branches:
- ``probe_rst`` / ``probe_fin`` / ``probe_ack``: when ``socket.socket()``
  raises before assignment, ``sock`` stays ``None`` and the ``finally`` block
  skips the close (213->215, 253->255, 292->294).
- ``run_osdetect``: a future that raises is caught by the per-future ``except``
  handler, which looks up the port and appends a NO-RESPONSE probe (428-430).
- ``run_osdetect`` dedup: a duplicate OS name hits the ``name in seen`` guard
  and is skipped (470->469).
"""
from __future__ import annotations

import socket

from ethscan.osdetect import probe_ack, probe_fin, probe_rst, run_osdetect


def test_probe_rst_socket_creation_failure_covers_213_215(monkeypatch) -> None:
    # socket.socket() raises before sock is assigned; sock stays None so the
    # finally guard `if sock is not None` is False and close is skipped (213->215).
    def boom(*args, **kwargs):
        raise OSError("no socket")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", boom)

    res = probe_rst("h", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert "no socket" in str(res["error"])


def test_probe_fin_socket_creation_failure_covers_253_255(monkeypatch) -> None:
    # Same invariant as probe_rst for the FIN probe (253->255).
    def boom(*args, **kwargs):
        raise OSError("no socket")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", boom)

    res = probe_fin("h", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert "no socket" in str(res["error"])


def test_probe_ack_socket_creation_failure_covers_292_294(monkeypatch) -> None:
    # Same invariant as probe_rst for the ACK probe (292->294).
    def boom(*args, **kwargs):
        raise OSError("no socket")

    monkeypatch.setattr(
        "ethscan.osdetect.socket.getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))
        ],
    )
    monkeypatch.setattr("ethscan.osdetect.socket.socket", boom)

    res = probe_ack("h", 80, 1.0)
    assert res["response"] == "NO-RESPONSE"
    assert "no socket" in str(res["error"])


def test_run_osdetect_future_failure_reported_covers_428_430(monkeypatch) -> None:
    # A probe that raises is caught by the per-future except handler, which
    # looks up the port and appends a NO-RESPONSE probe (428-430).
    def raising_probe(*args, **kwargs):
        raise RuntimeError("probe boom")

    monkeypatch.setattr("ethscan.osdetect.probe_syn", raising_probe)

    results = run_osdetect("example.com", ports=[80], timeout=1.0)
    assert len(results["probes"]) == 1
    probe = results["probes"][0]
    assert probe["response"] == "NO-RESPONSE"
    assert probe["probe_type"] == "SYN"
    assert probe["port"] == 80
    assert "probe boom" in str(probe["error"])


def test_run_osdetect_dedup_skips_seen_covers_470_469() -> None:
    # Two connected probes both infer "Linux"; the second hits the
    # `name in seen` guard and is skipped (470->469).
    from unittest.mock import patch

    from ethscan import osdetect

    syn1 = {
        "port": 80,
        "connected": True,
        "response": "SYN-ACK",
        "probe_type": "SYN",
        "flags_observed": "SYN-ACK",
        "error": None,
    }
    syn2 = {
        "port": 443,
        "connected": True,
        "response": "SYN-ACK",
        "probe_type": "SYN",
        "flags_observed": "SYN-ACK",
        "error": None,
    }
    with patch("ethscan.osdetect.probe_syn", side_effect=[syn1, syn2]):
        res = osdetect.run_osdetect("example.com", ports=[80, 443], timeout=1.0, max_workers=2)

    assert res["inferred_os"] == ["Linux"]
    assert res["inferred_os_count"] == 1