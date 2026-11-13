"""Permanent sweep test: hostile Memcached formatter inputs are rendered, never raised.

Covers ``format_memcached_report_markdown`` and ``format_memcached_report_csv`` against
hostile ``findings`` and ``stats`` values (non-list/tuple scalars, lists of hostile
elements, non-dict stats). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.memcached import (
    format_memcached_report_csv,
    format_memcached_report_markdown,
)

MEMCACHED_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_memcached_report_markdown,
    format_memcached_report_csv,
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

NON_DICT_STATS: list[object] = [None, 1, 0, True, "stats", ["not", "a", "dict"], 3.14]

HOSTILE_STATS_DICTS: list[dict[str, object]] = [
    {"pid": None},
    {"uptime": 1, "bytes": "not-an-int"},
    {"key": ["nested", "list"]},
    {"1": "non-string-key"},
    {"normal": "value", "bad": None},
]


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_memcached_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" in output
        assert "- None detected" in output


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_memcached_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
def test_memcached_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``stats`` values (dict field iterated in Markdown, key-accessed in CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("stats", NON_DICT_STATS)
def test_memcached_formatters_tolerate_non_dict_stats(
    formatter: Callable[[dict[str, Any]], str], stats: object
) -> None:
    output = formatter({"stats": stats})
    assert isinstance(output, str)
    # Non-dict stats should not render the stats tables/rows.
    if "markdown" in formatter.__name__:
        assert "## Stats" not in output or "No stats collected" in output


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("stats", HOSTILE_STATS_DICTS)
def test_memcached_formatters_render_hostile_stats_dicts(
    formatter: Callable[[dict[str, Any]], str], stats: dict[str, object]
) -> None:
    output = formatter({"stats": stats})
    assert isinstance(output, str)
    # Markdown renders stats as tables; CSV accesses specific keys.
    # The formatters should not crash on non-string values or nested structures.
    if "markdown" in formatter.__name__:
        # At least the Stats section header should appear.
        assert "## Stats" in output


@pytest.mark.parametrize("formatter", MEMCACHED_FORMATTERS, ids=_formatter_id)
def test_memcached_formatters_still_render_well_formed_stats(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "stats": {
            "pid": "1234",
            "uptime": "3600",
            "bytes": "1048576",
            "curr_connections": "10",
        }
    })
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "1234" in output
        assert "3600" in output
    else:
        # CSV has specific columns: uptime, bytes, curr_connections (no pid)
        assert "3600" in output
        assert "1048576" in output
        assert "10" in output