"""Permanent sweep test: hostile PostgreSQL formatter inputs are rendered, never raised.

Covers ``format_postgresql_report_markdown`` and ``format_postgresql_report_csv``
against hostile ``startup`` (non-dict scalars/lists, hostile dicts with non-string
or nested values) and ``parameters`` (nested inside ``startup``; non-dict values,
hostile dicts with non-string/nested values) plus ``findings`` (non-iterable
scalars, hostile lists). Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.postgresql import (
    format_postgresql_report_csv,
    format_postgresql_report_markdown,
)

POSTGRESQL_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_postgresql_report_markdown,
    format_postgresql_report_csv,
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_DICT_STARTUP: list[object] = [None, 1, 0, True, "startup", ["not", "a", "dict"], 3.14]

HOSTILE_STARTUP_DICTS: list[dict[str, object]] = [
    {"server_version": None},
    {"auth_type_name": 1},
    {"process_id": "bad"},
    {"server_version": ["nested", "list"]},
    {"parameters": "not-a-dict"},
    {"parameters": None},
    {"parameters": 5},
    {"parameters": {"k": None}},
    {"parameters": {"k": [1, 2]}},
    {"parameters": {"k": {"nested": "dict"}}},
    {"normal": "value", "bad": None},
]

WELL_FORMED_STARTUP = {
    "server_version": "14.5",
    "auth_type_name": "md5",
    "auth_type_code": 10,
    "process_id": 12345,
}

HOSTILE_PARAMETER_DICTS: list[dict[Any, object]] = [
    {"port": None},
    {"max_connections": 1},
    {"port": ["nested"]},
    {1: "non-string-key"},
    {"normal": "value", "bad": None},
]

WELL_FORMED_PARAMETERS = {"port": "5432", "max_connections": 100}

NON_ITERABLE_FINDINGS: list[object] = [None, 1, 0, True, "finding", {"x": 1}, 3.14]

HOSTILE_FINDING_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]


# ---------------------------------------------------------------------------
# Hostile ``startup`` values (dict field guarded by _as_dict; Markdown iterates
# specific keys, CSV accesses auth_type_name/process_id via .get()).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("startup", NON_DICT_STARTUP)
def test_postgresql_formatters_tolerate_non_dict_startup(
    formatter: Callable[[dict[str, Any]], str], startup: object
) -> None:
    output = formatter({"startup": startup})
    assert isinstance(output, str)
    # A non-dict startup normalizes to {}, so no Server Greeting section.
    assert "## Server Greeting" not in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("startup", HOSTILE_STARTUP_DICTS)
def test_postgresql_formatters_render_hostile_startup_dicts(
    formatter: Callable[[dict[str, Any]], str], startup: dict[str, object]
) -> None:
    output = formatter({"startup": startup})
    assert isinstance(output, str)
    # A dict startup renders the Server Greeting header in Markdown; bad values
    # are stringified/escaped rather than crashing. CSV does not use sections.
    if "markdown" in formatter.__name__:
        assert "## Server Greeting" in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
def test_postgresql_formatters_still_render_well_formed_startup(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"startup": WELL_FORMED_STARTUP})
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "## Server Greeting" in output
        assert "14.5" in output
        assert "md5" in output
        assert "10" in output
        assert "12345" in output
    else:
        # CSV writes auth_type_name and process_id columns.
        assert "md5" in output
        assert "12345" in output


# ---------------------------------------------------------------------------
# Hostile ``parameters`` values (nested inside ``startup``; Markdown iterates
# the dict, CSV does not render a parameters table).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("parameters", NON_DICT_STARTUP)
def test_postgresql_formatters_tolerate_non_dict_parameters(
    formatter: Callable[[dict[str, Any]], str], parameters: object
) -> None:
    output = formatter({"startup": {"parameters": parameters}})
    assert isinstance(output, str)
    # Non-dict parameters normalize to {}; no Server Parameters table.
    assert "## Server Parameters" not in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("parameters", HOSTILE_PARAMETER_DICTS)
def test_postgresql_formatters_render_hostile_parameter_dicts(
    formatter: Callable[[dict[str, Any]], str], parameters: dict[Any, object]
) -> None:
    output = formatter({"startup": {"parameters": parameters}})
    assert isinstance(output, str)
    # Markdown iterates parameters and stringifies each value; CSV has no
    # parameters table, so only Markdown asserts the section header.
    if "markdown" in formatter.__name__:
        assert "## Server Parameters" in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
def test_postgresql_formatters_still_render_well_formed_parameters(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"startup": {"parameters": WELL_FORMED_PARAMETERS}})
    assert isinstance(output, str)
    if "markdown" in formatter.__name__:
        assert "## Server Parameters" in output
        assert "5432" in output
        assert "100" in output


# ---------------------------------------------------------------------------
# Hostile ``findings`` values (iterated by both formatters; elements stringified).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_postgresql_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output
    if "markdown" in formatter.__name__:
        assert "## Findings" in output
        assert "- No notable findings" in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_postgresql_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", POSTGRESQL_FORMATTERS, ids=_formatter_id)
def test_postgresql_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output
