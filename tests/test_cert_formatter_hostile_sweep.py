"""Permanent sweep test: hostile Cert formatter inputs are rendered, never raised.

Covers ``format_cert_report_markdown``, ``format_cert_report_csv`` and
``format_cert_report_json`` against hostile top-level shapes, ``subdomains``,
``notes`` and ``cert_data`` (including ``cert_data.entries``). Every shape
yields a string and never raises; the formatters already guard their inputs
via ``isinstance`` checks, so this is regression coverage.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.cert import (
    format_cert_report_csv,
    format_cert_report_json,
    format_cert_report_markdown,
)

CERT_FORMATTERS: list[Callable[[Any], str]] = [
    format_cert_report_markdown,
    format_cert_report_csv,
    format_cert_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

NON_LIST_SUBDOMAINS: list[object] = [None, 1, 0, True, "sub", {"x": 1}, 3.14]

HOSTILE_SUBDOMAIN_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
    ["not-a-dict", "a.example.com"],
    ["a", 1],
    [["nested"]],
]

NON_LIST_NOTES: list[object] = [None, 1, 0, True, "note", {"x": 1}, 3.14]

HOSTILE_NOTE_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

NON_DICT_CERT_DATA: list[object] = [None, 1, 0, True, "cert", ["not", "a", "dict"], 3.14]

HOSTILE_CERT_DATA_DICTS: list[dict[str, object]] = [
    {"entries": 1},
    {"entries": None},
    {"entries": [1, 2]},
    {"entries": [["nested"]]},
    {"entries": ["not-a-dict", {"name_value": "a.example.com"}]},
    {"entries": [{"name_value": None}]},
    {"entries": [{"name_value": 1}]},
    {"entries": [{"name_value": ["a"]}]},
    {"entries": [{"name_value": {"k": "v"}}]},
    {"entries": [{"common_name": None}]},
    {"entries": [{"common_name": 123}]},
    {"count": "not-a-number"},
    {"error": 1},
    {"cached": "not-a-bool"},
    {"offline_fallback": 1},
    {"key": "value"},
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "ip": "1.2.3.4",
    "timeout": 10,
    "use_cache": True,
    "offline_fallback": True,
    "cert_data": {
        "entries": [{"name_value": "a.example.com"}],
        "count": 1,
        "cached": False,
    },
    "subdomains": ["a.example.com", "b.example.com"],
    "notes": ["served from cache"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


# ---------------------------------------------------------------------------
# Non-Mapping top-level data.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_cert_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_cert_report_json:
        assert output == "{}"


# ---------------------------------------------------------------------------
# Hostile ``subdomains`` values (iterated in Markdown and CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("subdomains", NON_LIST_SUBDOMAINS)
def test_cert_formatters_tolerate_non_list_subdomains(
    formatter: Callable[[Any], str], subdomains: object
) -> None:
    output = formatter({"subdomains": subdomains})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "**Subdomains Found:** 0" in output


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("subdomains", HOSTILE_SUBDOMAIN_LISTS)
def test_cert_formatters_render_hostile_subdomains_lists(
    formatter: Callable[[Any], str], subdomains: list[object]
) -> None:
    output = formatter({"subdomains": subdomains})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "Subdomains Discovered" in output


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
def test_cert_formatters_still_render_well_formed_subdomains(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter({"subdomains": ["a.example.com", "b.example.com"]})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "a.example.com" in output
        assert "b.example.com" in output
    elif formatter is format_cert_report_csv:
        assert "a.example.com" in output
        assert "b.example.com" in output


# ---------------------------------------------------------------------------
# Hostile ``notes`` values (iterated in Markdown).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", NON_LIST_NOTES)
def test_cert_formatters_tolerate_non_list_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTE_LISTS)
def test_cert_formatters_render_hostile_notes_lists(
    formatter: Callable[[Any], str], notes: list[object]
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "## Notes" in output


# ---------------------------------------------------------------------------
# Hostile ``cert_data`` values (Markdown accesses ``error``/``count``/etc;
# CSV/JSON must still not raise).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cert_data", NON_DICT_CERT_DATA)
def test_cert_formatters_tolerate_non_dict_cert_data(
    formatter: Callable[[Any], str], cert_data: object
) -> None:
    output = formatter({"cert_data": cert_data})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "Certificate Transparency Data" not in output


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cert_data", HOSTILE_CERT_DATA_DICTS)
def test_cert_formatters_render_hostile_cert_data_dicts(
    formatter: Callable[[Any], str], cert_data: dict[str, object]
) -> None:
    output = formatter({"cert_data": cert_data})
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown and isinstance(cert_data, dict) and "entries" in cert_data:
        assert "Certificate Transparency Data" in output


# ---------------------------------------------------------------------------
# Well-formed regression.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
def test_cert_formatters_still_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "ethscan Certificate Transparency Report" in output
        assert "a.example.com" in output
        assert "served from cache" in output
    elif formatter is format_cert_report_csv:
        assert "a.example.com" in output
        assert "b.example.com" in output
    elif formatter is format_cert_report_json:
        assert "example.com" in output
        assert "a.example.com" in output