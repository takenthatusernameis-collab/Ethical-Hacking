"""Permanent sweep test: hostile MAC formatter inputs are rendered, never raised.

Covers ``format_mac_report_markdown``, ``format_mac_report_csv`` and
``format_mac_report_json`` against hostile top-level shapes, ``mac_data``,
``notes``, and the scalar fields ``mac``/``oui``/``vendor``. Every shape
yields a string and never raises; the formatters already guard their inputs
via ``isinstance`` checks, so this is regression coverage.
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

NON_DICT_MAC_DATA: list[object] = [None, 1, 0, True, "data", ["x"], 3.14]

HOSTILE_MAC_DATA_DICTS: list[dict[str, object]] = [
    {"vendor": 1},
    {"vendor": None},
    {"vendor": ["nested"]},
    {"vendor": {"k": "v"}},
    {"error": 1},
    {"error": None},
    {"error": ["nested"]},
    {"cached": "not-a-bool"},
    {"offline_fallback": 1},
    {"timestamp": "not-a-number"},
    {"mac": 123},
    {"key": "value"},
]

NON_LIST_NOTES: list[object] = [None, 1, 0, True, "note", {"x": 1}, 3.14]

HOSTILE_NOTE_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

SCALAR_MAC: list[object] = [None, 1, 0, True, 3.14, ["nested"], {"k": "v"}]
SCALAR_OUI: list[object] = [None, 1, 0, True, 3.14, ["nested"], {"k": "v"}]

WELL_FORMED = {
    "target": "00:1A:2B:3C:4D:5E",
    "mac": "00:1a:2b:3c:4d:5e",
    "oui": "001a2b",
    "timeout": 5.0,
    "use_cache": True,
    "offline_fallback": True,
    "mac_data": {
        "mac": "00:1a:2b:3c:4d:5e",
        "vendor": "Vendor Inc.",
        "timestamp": 1234567890.0,
        "cached": False,
        "offline_fallback": False,
    },
    "notes": ["served from cache"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


# ---------------------------------------------------------------------------
# Non-Mapping top-level data.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_mac_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_mac_report_json:
        assert output == "{}"


# ---------------------------------------------------------------------------
# Hostile ``mac_data`` values (accessed by all formatters).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("mac_data", NON_DICT_MAC_DATA)
def test_mac_formatters_tolerate_non_dict_mac_data(
    formatter: Callable[[Any], str], mac_data: object
) -> None:
    output = formatter({"mac_data": mac_data})
    assert isinstance(output, str)
    if formatter is format_mac_report_markdown:
        assert "No MAC vendor data available" in output


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("mac_data", HOSTILE_MAC_DATA_DICTS)
def test_mac_formatters_render_hostile_mac_data_dicts(
    formatter: Callable[[Any], str], mac_data: dict[str, object]
) -> None:
    output = formatter({"mac_data": mac_data})
    assert isinstance(output, str)
    if formatter is format_mac_report_markdown:
        assert "MAC Vendor Data" in output


# ---------------------------------------------------------------------------
# Hostile ``notes`` values (iterated in Markdown).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", NON_LIST_NOTES)
def test_mac_formatters_tolerate_non_list_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTE_LISTS)
def test_mac_formatters_render_hostile_notes_lists(
    formatter: Callable[[Any], str], notes: list[object]
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_mac_report_markdown:
        assert "## Notes" in output


# ---------------------------------------------------------------------------
# Hostile scalar fields ``mac`` and ``oui`` (rendered in Markdown/CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("mac", SCALAR_MAC)
def test_mac_formatters_tolerate_hostile_mac_scalar(
    formatter: Callable[[Any], str], mac: object
) -> None:
    output = formatter({"mac": mac})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("oui", SCALAR_OUI)
def test_mac_formatters_tolerate_hostile_oui_scalar(
    formatter: Callable[[Any], str], oui: object
) -> None:
    output = formatter({"oui": oui})
    assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Well-formed regression.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", MAC_FORMATTERS, ids=_formatter_id)
def test_mac_formatters_still_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_mac_report_markdown:
        assert "ethscan MAC Vendor Lookup Report" in output
        assert "00:1a:2b:3c:4d:5e" in output
        assert "001a2b" in output
        assert "Vendor Inc." in output
        assert "served from cache" in output
    elif formatter is format_mac_report_csv:
        assert "00:1a:2b:3c:4d:5e" in output
        assert "001a2b" in output
        assert "Vendor Inc." in output
    elif formatter is format_mac_report_json:
        assert "00:1a:2b:3c:4d:5e" in output
        assert "Vendor Inc." in output