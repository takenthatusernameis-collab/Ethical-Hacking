"""Hostile-sweep tests for ethscan.geo: untrusted cache/transport data is reported, never raised."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from ethscan import geo


HOSTILE_CACHE_BODIES: tuple[str, ...] = (
    "",
    "not json at all",
    "[]",
    "null",
    '"string"',
    "123",
    "[" * 500 + "]" * 500,
    "\x00\x01\xff",
    '{"8.8.8.8": "not a dict"}',
    '{"8.8.8.8": [1,2,3]}',
    '{"8.8.8.8": {"timestamp": "not a number", "status": "success"}}',
    '{"8.8.8.8": {"timestamp": null, "status": "success"}}',
    '{"8.8.8.8": {"status": "success"}}',
    '{"other": {"timestamp": '
    + str(time.time())
    + ', "status": "success"}}',
)


@pytest.mark.parametrize(
    "body", HOSTILE_CACHE_BODIES, ids=[f"cache{i}" for i in range(len(HOSTILE_CACHE_BODIES))]
)
def test_hostile_cache_file_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str
) -> None:
    cache_file = tmp_path / "geo_cache.json"
    cache_file.write_bytes(body.encode("utf-8", errors="surrogatepass"))
    monkeypatch.setattr(geo, "CACHE_FILE", cache_file)
    monkeypatch.setattr(geo, "_resolve_host", lambda _h: "8.8.8.8")
    monkeypatch.setattr(geo, "_fetch_geo_data", lambda *_a, **_k: None)

    result = geo.run_geo("8.8.8.8", timeout=1.0, use_cache=True, offline_fallback=True)

    assert isinstance(result, dict)
    assert result["ip"] == "8.8.8.8"


def test_stale_hostile_cache_offline_fallback_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_file = tmp_path / "geo_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "8.8.8.8": {
                    "status": "success",
                    "country": "Cachedland",
                    "timestamp": time.time() - 100000,
                },
                "bad": "not a dict",
            }
        )
    )
    monkeypatch.setattr(geo, "CACHE_FILE", cache_file)
    monkeypatch.setattr(geo, "_resolve_host", lambda _h: "8.8.8.8")
    monkeypatch.setattr(geo, "_fetch_geo_data", lambda *_a, **_k: None)

    result = geo.run_geo("8.8.8.8", timeout=1.0, use_cache=True, offline_fallback=True)

    geo_data = result["geolocation"]
    assert isinstance(geo_data, dict)
    assert geo_data["offline_fallback"] is True
    assert geo_data["country"] == "Cachedland"


def test_hostile_transport_error_type_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(geo, "CACHE_FILE", tmp_path / "geo_cache.json")
    monkeypatch.setattr(geo, "_resolve_host", lambda _h: "8.8.8.8")

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("urllib.request.urlopen", boom)

    result = geo.run_geo("8.8.8.8", timeout=1.0, use_cache=False, offline_fallback=False)

    geo_data = result["geolocation"]
    assert isinstance(geo_data, dict)
    assert geo_data["status"] == "fail"
    assert "error" in geo_data
