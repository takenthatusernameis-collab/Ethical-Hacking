"""Hostile-sweep tests for ethscan.geo: untrusted cache/transport data is reported, never raised."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

import pytest

from ethscan import geo
from ethscan.geo import (
    format_geo_report_csv,
    format_geo_report_json,
    format_geo_report_markdown,
)


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


# ---------------------------------------------------------------------------
# Formatter sweep: hostile top-level and nested shapes are rendered, never raised.
# ---------------------------------------------------------------------------

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_geo_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_geo_report_json(cast(Any, bad_any)))
        md = format_geo_report_markdown(cast(Any, bad_any))
        csv_text = format_geo_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan IP Geolocation Report" in md


def test_geo_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": False, "error": "boom"},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": False, "error": ""},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": True, "hops": "not a list"},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": True, "hops": ["not a dict", 123, None]},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": True, "hops": [{"geolocation": "not a dict"}, {"geolocation": {}}]},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": True, "hops": [{"geolocation": {"country": "US"}}, {"geolocation": {"city": "NYC"}}]},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": False, "notes": "not a list"},
        {"target": "x", "host": "x", "ip": "8.8.8.8", "timeout": 1.0, "use_cache": False, "offline_fallback": False, "recursive": False, "notes": ["note1", 123, None]},
    ]
    for data in cases:
        json.loads(format_geo_report_json(data))
        md = format_geo_report_markdown(data)
        csv_text = format_geo_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan IP Geolocation Report" in md
        # A hostile hops value must not render a Hop Geolocation section
        if not isinstance(data.get("hops"), (list, tuple)):
            assert "## Hop Geolocation" not in md
        # Notes are rendered when present and non-empty after normalization
        notes_val = data.get("notes")
        if isinstance(notes_val, (list, tuple)) and notes_val:
            assert "## Notes" in md
