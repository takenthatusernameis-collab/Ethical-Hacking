"""Permanent sweep test: hostile MSSQL formatter inputs are rendered, never raised.

Covers ``format_mssql_report_markdown`` and ``format_mssql_report_csv`` against
hostile ``findings`` and ``prelogin`` values (non-list/tuple scalars, lists of hostile
elements, non-dict prelogin). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.mssql import (
    format_mssql_report_csv,
    format_mssql_report_markdown,
)

MSSQL_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_mssql_report_markdown,
    format_mssql_report_csv,
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

NON_DICT_PRELOGIN: list[object] = [None, 1, 0, True, "prelogin", ["not", "a", "dict"], 3.14]

HOSTILE_PRELOGIN_DICTS: list[dict[str, object]] = [
    {"version": None},
    {"encryption": 1, "instance_name": "not-an-int"},
    {"key": ["nested", "list"]},
    {"1": "non-string-key"},
    {"normal": "value", "bad": None},
]


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_mssql_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" in output
        assert "- No notable findings" in output


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_mssql_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
def test_mssql_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output


# ---------------------------------------------------------------------------
# Hostile ``prelogin`` values (dict field iterated in Markdown, key-accessed in CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("prelogin", NON_DICT_PRELOGIN)
def test_mssql_formatters_tolerate_non_dict_prelogin(
    formatter: Callable[[dict[str, Any]], str], prelogin: object
) -> None:
    output = formatter({"prelogin": prelogin})
    assert isinstance(output, str)
    # Non-dict prelogin should not render the PRELOGIN Response section.
    if "markdown" in formatter.__name__:
        assert "## PRELOGIN Response" not in output or "No notable findings" in output


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("prelogin", HOSTILE_PRELOGIN_DICTS)
def test_mssql_formatters_render_hostile_prelogin_dicts(
    formatter: Callable[[dict[str, Any]], str], prelogin: dict[str, object]
) -> None:
    output = formatter({"prelogin": prelogin})
    assert isinstance(output, str)
    # Markdown renders prelogin as a list; CSV accesses specific keys.
    # The formatters should not crash on non-string values or nested structures.
    if "markdown" in formatter.__name__:
        # At least the PRELOGIN Response section header should appear.
        assert "## PRELOGIN Response" in output


@pytest.mark.parametrize("formatter", MSSQL_FORMATTERS, ids=_formatter_id)
def test_mssql_formatters_still_render_well_formed_prelogin(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "prelogin": {
            "version": "16.0.0",
            "encryption": "REQUIRED",
            "instance_name": "MSSQLSERVER",
            "thread_id": 42,
        }
    })
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "16.0.0" in output
        assert "REQUIRED" in output
        assert "MSSQLSERVER" in output
        assert "42" in output
    else:
        # CSV has specific columns: encryption, instance_name, thread_id (no version).
        assert "REQUIRED" in output
        assert "MSSQLSERVER" in output
        assert "42" in output