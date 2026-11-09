"""Hostile-input sweep for fuzz report formatters and wordlist handling.

`tests/test_http_hostile_sweep.py` already covers transport/body handling for
`fuzz.run_fuzz` (hostile HTTP answers and unnamed transport failures are
reported, never raised). `tests/test_fuzz.py` covers the happy path of every
report formatter. These tests focus on hostile result/response shapes handed
to the formatters and to `run_fuzz` itself: a cache or pipeline handoff with
non-dict entries, hostile field types, or a hostile top-level container must
never raise and must return structured output.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, cast

import pytest

from ethscan.fuzz import (
    format_fuzz_report_csv,
    format_fuzz_report_json,
    format_fuzz_report_markdown,
    run_fuzz,
)

HOSTILE_TOPLEVEL: tuple[Any, ...] = (None, [], "x", 123, True, object())

HOSTILE_ENTRIES: tuple[Any, ...] = ("not-a-dict", 123, None, [], {"path": "/admin", "status_code": 200, "error": None})

HOSTILE_FINDINGS: tuple[Any, ...] = ("not-a-dict", 123, None, [], {"path": "/admin", "status_code": 200, "error": None})

HOSTILE_WORDLISTS: tuple[list[Any], ...] = (
    ["/admin", 123],
    ["/admin", None],
    ["/admin", ["x"]],
    [],
)


@pytest.mark.parametrize("data", HOSTILE_TOPLEVEL)
def test_csv_toplevel_hostile_never_raises(data: Any) -> None:
    out = format_fuzz_report_csv(data)  # type: ignore[arg-type]
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    assert rows == []
    assert reader.fieldnames is not None


@pytest.mark.parametrize("data", HOSTILE_TOPLEVEL)
def test_markdown_toplevel_hostile_never_raises(data: Any) -> None:
    out = format_fuzz_report_markdown(data)  # type: ignore[arg-type]
    assert "# ethscan HTTP Fuzz Report" in out


@pytest.mark.parametrize("data", HOSTILE_TOPLEVEL)
def test_json_toplevel_hostile_never_raises(data: Any) -> None:
    out = format_fuzz_report_json(data)  # type: ignore[arg-type]
    json.loads(out)


def test_csv_hostile_all_results_entries_never_raise() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": [],
        "all_results": list(HOSTILE_ENTRIES),
    }
    out = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(out)))
    assert reader[0] == ["target", "base_url", "path", "status_code", "error", "is_finding"]
    # Only the dict entry produces a row; hostile entries are skipped.
    assert ["t", "b", "/admin", "200", "", "true"] in reader


def test_markdown_hostile_all_results_entries_never_raise() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": [],
        "all_results": list(HOSTILE_ENTRIES),
    }
    out = format_fuzz_report_markdown(data)
    assert "## All Results" in out
    assert "/admin" in out
    assert "not-a-dict" not in out


def test_csv_hostile_findings_entries_never_raise() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": list(HOSTILE_FINDINGS),
        "all_results": [],
    }
    out = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(out)))
    assert ["finding_path", "finding_status_code"] in reader
    assert ["/admin", "200"] in reader


def test_markdown_hostile_findings_entries_never_raise() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": list(HOSTILE_FINDINGS),
        "all_results": [],
    }
    out = format_fuzz_report_markdown(data)
    assert "## Findings" in out
    assert "/admin" in out


def test_csv_non_iterable_all_results_never_raises() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": [],
        "all_results": 123,
    }
    out = format_fuzz_report_csv(data)
    reader = list(csv.reader(io.StringIO(out)))
    assert len(reader) == 1
    assert reader[0] == ["target", "base_url", "path", "status_code", "error", "is_finding"]


def test_markdown_non_iterable_all_results_never_raises() -> None:
    data = {
        "target": "t",
        "base_url": "b",
        "paths_tested": 1,
        "findings": [],
        "all_results": 123,
    }
    out = format_fuzz_report_markdown(data)
    assert "## All Results" in out
    assert "/admin" not in out


@pytest.mark.parametrize("wordlist", HOSTILE_WORDLISTS, ids=["mixed", "none", "list", "empty"])
def test_run_fuzz_hostile_wordlist_never_raises(wordlist: list[Any]) -> None:
    results = run_fuzz("http://127.0.0.1:9/", wordlist=wordlist, timeout=1.0)
    assert isinstance(results, dict)
    # Non-string entries are skipped probes; paths_tested counts tested paths.
    expected = sum(1 for p in wordlist if isinstance(p, str))
    assert results["paths_tested"] == expected
    all_results = cast(list[dict[str, object]], results["all_results"])
    assert len(all_results) == expected


def test_run_fuzz_hostile_wordlist_skips_non_string_paths() -> None:
    results = run_fuzz(
        "http://127.0.0.1:9/", wordlist=cast("list[str] | None", ["/admin", 123, None, "/login"]), timeout=1.0
    )
    all_results = cast(list[dict[str, object]], results["all_results"])
    paths = [r["path"] for r in all_results]
    assert paths == ["/admin", "/login"]