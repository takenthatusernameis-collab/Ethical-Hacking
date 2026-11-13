"""Permanent sweep test: hostile MAC formatter inputs are rendered, never raised.

Covers ``format_mac_report_markdown``, ``format_mac_report_csv`` and
``format_mac_report_json`` against hostile top-level shapes and hostile
values for ``mac_data`` and ``notes``. Every shape yields a string and
never raises.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.mac import (
    format_mac_report_csv,
    format_mac_report_json,
    format_mac_report_markdown,
)

MAC_FORMATTERS: list[Callable[[Any], str]] = [
    format_mac_report_markdown,
    format_mac_report_csv,
    format_mac_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_MAC_DATA: list[object] = [
    None,
    1,
    "x",
    True,
    [1, 2],
    {"error": "boom"},
    {"error": {"nested": True}},
    {"vendor": None},
    {"vendor": 123},
    {"vendor": [1, 2]},
    {"vendor": {"nested": True}},
    {"cached": "yes", "offline_fallback": 1},
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    "note",
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "cached"],
]

WELL_FORMED = {
    "target": "00:1A:2B:3C:4D:5E",
    "mac": "00:1a:2b:3c:4d:5e",
    "oui": "001a2b3c",
    "timeout": 5.0,
    "use_cache": True,
    "offline_fallback": True,
    "mac_data": {
        "vendor": "Example Vendor Inc.",
        "cached": False,
        "offline_fallback": False,
    },
    "notes": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_mac_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_mac_report_json:
        assert output == "{}"


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("mac_data", HOSTILE_MAC_DATA)
def test_mac_formatters_tolerate_hostile_mac_data(
    formatter: Callable[[Any], str], mac_data: object
) -> None:
    output = formatter({"mac_data": mac_data})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_mac_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
def test_mac_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_mac_report_markdown:
        assert "Example Vendor Inc." in output
        assert "00:1a:2b:3c:4d:5e" in output
    elif formatter is format_mac_report_csv:
        assert "Example Vendor Inc." in output
        assert "001a2b3c" in output
