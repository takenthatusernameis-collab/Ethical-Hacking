"""Hostile-sweep tests for ethscan.cert: untrusted cache/transport data is reported, never raised."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from ethscan import cert


HOSTILE_CACHE_BODIES: tuple[str, ...] = (
    "",
    "not json at all",
    "[]",
    "null",
    '"string"',
    "123",
    "[" * 500 + "]" * 500,
    "\x00\x01\xff",
    '{"example.com": "not a dict"}',
    '{"example.com": [1,2,3]}',
    '{"example.com": {"timestamp": "not a number", "entries": []}}',
    '{"example.com": {"timestamp": null, "entries": []}}',
    '{"example.com": {"entries": "not a list"}}',
    '{"example.com": {"timestamp": '
    + str(time.time())
    + ', "entries": [null, 123, {"name_value": null}, {"common_name": 123}, "x"]}}',
)


@pytest.mark.parametrize("body", HOSTILE_CACHE_BODIES, ids=[f"cache{i}" for i in range(len(HOSTILE_CACHE_BODIES))])
def test_hostile_cache_file_never_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str) -> None:
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_bytes(body.encode("utf-8", errors="surrogatepass"))
    monkeypatch.setattr(cert, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cert, "_resolve_host", lambda _h: "127.0.0.1")
    monkeypatch.setattr(cert, "_fetch_cert_data", lambda *_a, **_k: None)

    result = cert.run_cert("example.com", timeout=1.0, use_cache=True, offline_fallback=True)

    assert isinstance(result, dict)
    assert result["domain"] == "example.com"


def test_fetch_failure_with_stale_hostile_cache_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_file = tmp_path / "cert_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "example.com": {
                    "domain": "example.com",
                    "entries": [{"name_value": "cached.example.com"}, None, 123],
                    "count": 3,
                    "timestamp": time.time() - 100000,
                }
            }
        )
    )
    monkeypatch.setattr(cert, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cert, "_resolve_host", lambda _h: "127.0.0.1")
    monkeypatch.setattr(cert, "_fetch_cert_data", lambda *_a, **_k: None)

    result = cert.run_cert("example.com", timeout=1.0, use_cache=True, offline_fallback=True)

    assert result["cert_data"]["offline_fallback"] is True
    assert "cached.example.com" in result["subdomains"]


def test_hostile_transport_error_types_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Transport/parser failures of unnamed types are reported, never raised."""
    cache_file = tmp_path / "cert_cache.json"
    monkeypatch.setattr(cert, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cert, "_resolve_host", lambda _h: "127.0.0.1")

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("hostile")

    monkeypatch.setattr("urllib.request.urlopen", boom)

    result = cert.run_cert("example.com", timeout=1.0, use_cache=False, offline_fallback=False)

    assert result["cert_data"]["count"] == 0
    assert "error" in result["cert_data"]


def test_fetch_returns_none_reported_not_raised(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cert, "CACHE_FILE", tmp_path / "cert_cache.json")
    monkeypatch.setattr(cert, "_resolve_host", lambda _h: "127.0.0.1")
    monkeypatch.setattr(cert, "_fetch_cert_data", lambda *_a, **_k: None)

    result = cert.run_cert("example.com", timeout=1.0, use_cache=False, offline_fallback=False)

    assert result["cert_data"]["error"]
    assert result["subdomains"] == []


def test_extract_subdomains_hostile_entry_shapes() -> None:
    data: dict[str, object] = {
        "entries": [
            None,
            123,
            "x",
            [],
            {"name_value": None},
            {"name_value": 123},
            {"name_value": ["a"]},
            {"name_value": {"k": "v"}},
            {"common_name": None},
            {"common_name": 123},
            {"name_value": "  OK.Example.COM  \n*.ok.example.com\n"},
        ]
    }
    result = cert._extract_subdomains(data)
    assert "*.ok.example.com" in result
    assert "ok.example.com" in result
