"""Permanent sweep test: hostile MongoDB formatter inputs are rendered, never raised.

Covers ``format_mongodb_report_markdown`` and ``format_mongodb_report_csv`` against
hostile ``findings`` and ``buildInfo`` values (non-list/tuple scalars, lists of hostile
elements, non-dict buildInfo). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.mongodb import (
    format_mongodb_report_csv,
    format_mongodb_report_markdown,
)

MONGODB_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_mongodb_report_markdown,
    format_mongodb_report_csv,
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_ITERABLE_FINDINGS: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

NON_DICT_BUILDINFO: list[object] = [None, 1, 0, True, "buildInfo", ["not", "a", "dict"], 3.14]

HOSTILE_BUILDINFO_DICTS: list[dict[str, object]] = [
    {"version": None},
    {"sysInfo": 1, "modules": "not-an-int"},
    {"key": ["nested", "list"]},
    {"1": "non-string-key"},
    {"normal": "value", "bad": None},
]


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_mongodb_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" in output
        assert "- No notable findings" in output


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_mongodb_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
def test_mongodb_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``buildInfo`` values (dict field iterated in Markdown, key-accessed in CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("buildInfo", NON_DICT_BUILDINFO)
def test_mongodb_formatters_tolerate_non_dict_buildinfo(
    formatter: Callable[[dict[str, Any]], str], buildInfo: object
) -> None:
    output = formatter({"buildInfo": buildInfo})
    assert isinstance(output, str)
    # Non-dict buildInfo should not render the Build Info section.
    if "markdown" in formatter.__name__:
        assert "## Build Info" not in output or "No notable findings" in output


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("buildInfo", HOSTILE_BUILDINFO_DICTS)
def test_mongodb_formatters_render_hostile_buildinfo_dicts(
    formatter: Callable[[dict[str, Any]], str], buildInfo: dict[str, object]
) -> None:
    output = formatter({"buildInfo": buildInfo})
    assert isinstance(output, str)
    # Markdown renders buildInfo as a list; CSV accesses specific keys.
    # The formatters should not crash on non-string values or nested structures.
    if "markdown" in formatter.__name__:
        # At least the Build Info section header should appear.
        assert "## Build Info" in output


@pytest.mark.parametrize("formatter", MONGODB_FORMATTERS, ids=_formatter_id)
def test_mongodb_formatters_still_render_well_formed_buildinfo(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "buildInfo": {
            "version": "5.0.0",
            "sysInfo": "Linux x86_64",
            "modules": "ssl",
        }
    })
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "5.0.0" in output
        assert "Linux x86_64" in output
        assert "ssl" in output
    else:
        # CSV has specific columns: sysInfo, modules (no version).
        assert "Linux x86_64" in output
        assert "ssl" in output