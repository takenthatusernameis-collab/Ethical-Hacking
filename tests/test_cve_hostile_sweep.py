"""Hostile-input sweep for cve cache/file parsing.

`tests/test_http_hostile_sweep.py` already covers NVD transport/body handling
for the live fetch path. These tests focus on cache/file parsing and stale
offline fallback behavior: hostile cache file bodies and hostile entry shapes
must never raise; stale/offline fallback must return structured results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ethscan import cve


HOSTILE_CACHE_BODIES: tuple[bytes, ...] = (
    b"",
    b"not json at all",
    b"[]",
    b"null",
    b"123",
    b'"string"',
    b"true",
    b"[" * 2000 + b"]" * 2000,
    bytes(range(256)),
    b"{bad json",
)


def _write_cache(cache_file: Path, body: bytes) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(body)


def _services_file(tmp_path: Path) -> Path:
    services = tmp_path / "services.json"
    services.write_text(
        json.dumps({"services": [{"port": 22, "banner": "OpenSSH_7.2"}]})
    )
    return services


@pytest.mark.parametrize("body", HOSTILE_CACHE_BODIES)
def test_load_cache_hostile_body_never_raises(
    body: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    _write_cache(cache_file, body)
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)

    loaded = cve._load_cache()

    assert isinstance(loaded, dict)


@pytest.mark.parametrize("body", HOSTILE_CACHE_BODIES)
def test_get_cached_or_fetch_hostile_cache_never_raises(
    body: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    _write_cache(cache_file, body)
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cve, "_fetch_cve_data", lambda *a, **k: None)

    result = cve._get_cached_or_fetch(
        "CVE-2099-0001", timeout=0.5, use_cache=True, offline_fallback=True, api_url=None
    )

    assert isinstance(result, dict)
    assert result.get("cve_id") == "CVE-2099-0001"
    assert "error" in result


@pytest.mark.parametrize("body", HOSTILE_CACHE_BODIES)
def test_run_cve_hostile_cache_file_never_raises(
    body: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    _write_cache(cache_file, body)
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cve, "_fetch_cve_data", lambda *a, **k: None)

    result = cve.run_cve(
        "127.0.0.1",
        services_file=str(_services_file(tmp_path)),
        timeout=0.5,
        use_cache=True,
        offline_fallback=True,
    )

    assert isinstance(result, dict)
    assert result.get("services_checked") == 1


def test_load_cache_filters_non_dict_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    _write_cache(
        cache_file,
        json.dumps(
            {
                "good": {"timestamp": 1.0, "id": "CVE-1"},
                "list": [1, 2],
                "null": None,
                "str": "x",
                "num": 1,
            }
        ).encode("utf-8"),
    )
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)

    loaded = cve._load_cache()

    assert set(loaded) == {"good"}
    assert isinstance(loaded["good"], dict)


@pytest.mark.parametrize(
    "timestamp",
    [None, "now", [], {}, float("nan"), float("inf"), -float("inf"), True],
)
def test_cache_valid_rejects_hostile_timestamps(timestamp: Any) -> None:
    assert cve._is_cache_valid({"timestamp": timestamp}) is False


def test_stale_offline_fallback_returns_cached_dict_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cve.time, "time", lambda: 100000.0)
    stale = {
        "CVE-2016-6210": {
            "timestamp": 1.0,
            "vulnerabilities": [{"cve": {"id": "CVE-2016-6210"}}],
        }
    }
    cve._save_cache(stale)
    monkeypatch.setattr(cve, "_fetch_cve_data", lambda *a, **k: None)

    result = cve._get_cached_or_fetch(
        "CVE-2016-6210", timeout=0.5, use_cache=True, offline_fallback=True, api_url=None
    )

    assert result.get("cached") is True
    assert result.get("offline_fallback") is True
    assert result.get("vulnerabilities") == stale["CVE-2016-6210"]["vulnerabilities"]
    assert result is not stale["CVE-2016-6210"]


def test_fresh_cache_hit_ignores_hostile_fetch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cve.time, "time", lambda: 1000.0)
    cve._save_cache({"CVE-X": {"timestamp": 999.0, "id": "CVE-X"}})
    monkeypatch.setattr(
        cve,
        "_fetch_cve_data",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = cve._get_cached_or_fetch(
        "CVE-X", timeout=0.5, use_cache=True, offline_fallback=True, api_url=None
    )

    assert result.get("cached") is True
    assert result.get("id") == "CVE-X"


def test_run_cve_hostile_stale_cache_offline_fallback_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_file = tmp_path / "cve_cache.json"
    monkeypatch.setattr(cve, "CACHE_FILE", cache_file)
    monkeypatch.setattr(cve.time, "time", lambda: 100000.0)
    cve._save_cache(
        {
            "CVE-2016-6210": {
                "timestamp": 1.0,
                "vulnerabilities": "not-a-list",
                "nested": {"weird": [None, {"lang": "en", "value": 1}]},
            }
        }
    )
    monkeypatch.setattr(cve, "_fetch_cve_data", lambda *a, **k: None)

    result = cve.run_cve(
        "127.0.0.1",
        services_file=str(_services_file(tmp_path)),
        timeout=0.5,
        use_cache=True,
        offline_fallback=True,
    )

    assert isinstance(result, dict)
    assert result.get("services_checked") == 1
