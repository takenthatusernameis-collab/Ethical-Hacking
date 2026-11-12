"""Permanent sweep test: hostile SNMP formatter inputs are rendered, never raised.

Covers ``format_snmp_report_markdown`` and ``format_snmp_report_csv`` against
hostile ``findings`` values (non-list/tuple scalars, lists of hostile elements).
Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.snmp import (
    format_snmp_report_csv,
    format_snmp_report_markdown,
)

SNMP_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_snmp_report_markdown,
    format_snmp_report_csv,
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


@pytest.mark.parametrize("formatter", SNMP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", NON_ITERABLE_FINDINGS)
def test_snmp_formatters_tolerate_non_iterable_findings(
    formatter: Callable[[dict[str, Any]], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    assert "a-well-formed-finding" not in output


@pytest.mark.parametrize("formatter", SNMP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDING_LISTS)
def test_snmp_formatters_render_hostile_findings_lists(
    formatter: Callable[[dict[str, Any]], str], findings: list[object]
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)
    for item in findings:
        if item is None and "csv" in formatter.__name__:
            continue
        assert str(item) in output


@pytest.mark.parametrize("formatter", SNMP_FORMATTERS, ids=_formatter_id)
def test_snmp_formatters_still_render_well_formed_findings(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({"findings": ["first", "second"]})
    assert isinstance(output, str)
    assert "first" in output
    assert "second" in output
