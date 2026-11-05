"""Hostile-sweep tests for ethscan.mac: untrusted cache/transport data is reported, never raised."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from ethscan import mac


HOSTILE_CACHE_BODIES: tuple[str, ...] = (
    "",
    "not json at all",
    "[]",
    "null",
    '"string"',
    "123",
    "[" * 500 + "]" * 500,
    "\x00\x01\xff",
    '{"00:1a:2b:3c:4d:5e": "not a dict"}',
    '{"00:1a:2b:3c:4d:5e": [1,2,3]}',
    '{"00:1a:2b:3c:4d:5e": {"timestamp": "not a number", "vendor": "X"}}',
    '{"00:1a:2b:3c:4d:5e": {"timestamp": null, "vendor": "X"}}',
    '{"00:1a:2b:3c:4d:5e": {"vendor": "X"}}',
    '{"other": {"timestamp": ' + str(time.time()) + ', "vendor": "Y"}}',
)


@pytest.mark.parametrize(
    "body", HOSTILE_CACHE_BODIES, ids=[f"cache{i}" for i in range(len(HOSTILE_CACHE_BODIES))]
)
def test_hostile_cache_file_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str
) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_bytes(body.encode("utf-8", errors="surrogatepass"))
    monkeypatch.setattr(mac, "CACHE_FILE", cache_file)
    monkeypatch.setattr(mac, "_fetch_mac_data", lambda *_a, **_k: None)

    result = mac.run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=True, offline_fallback=True)

    assert isinstance(result, dict)
    assert result["mac"] == "00:1a:2b:3c:4d:5e"


def test_stale_hostile_cache_offline_fallback_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_file = tmp_path / "mac_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "00:1a:2b:3c:4d:5e": {
                    "mac": "00:1a:2b:3c:4d:5e",
                    "vendor": "CachedVendor",
                    "timestamp": time.time() - 100000,
                },
                "bad": "not a dict",
            }
        )
    )
    monkeypatch.setattr(mac, "CACHE_FILE", cache_file)
    monkeypatch.setattr(mac, "_fetch_mac_data", lambda *_a, **_k: None)

    result = mac.run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=True, offline_fallback=True)

    mac_data = result["mac_data"]
    assert isinstance(mac_data, dict)
    assert mac_data["offline_fallback"] is True
    assert mac_data["vendor"] == "CachedVendor"


def test_hostile_transport_error_type_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mac, "CACHE_FILE", tmp_path / "mac_cache.json")

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("urllib.request.urlopen", boom)

    result = mac.run_mac("00:1A:2B:3C:4D:5E", timeout=1.0, use_cache=False, offline_fallback=False)

    mac_data = result["mac_data"]
    assert isinstance(mac_data, dict)
    assert mac_data["vendor"] is None
    assert "error" in mac_data
