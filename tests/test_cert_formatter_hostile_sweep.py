"""Permanent sweep test: hostile cert formatter inputs are rendered, never raised.

Covers ``format_cert_report_markdown``, ``format_cert_report_csv`` and
``format_cert_report_json`` against hostile top-level shapes and hostile
values for ``cert_data``, ``cert_data.entries``, ``subdomains``, and
``notes``. Every shape yields a string and never raises.
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

HOSTILE_SCALARS: list[object] = [None, 1, 0, True, "x", 3.14, [1, 2], {"k": "v"}]

HOSTILE_SUBDOMAINS: list[object] = [
    None,
    1,
    "sub.example.com",
    {"a": "b"},
    [None, 1, True, 3.14, {"nested": True}, ["x"], "ok.example.com"],
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    "note",
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "cached"],
]

HOSTILE_CERT_DATA: list[object] = [
    None,
    1,
    "x",
    True,
    [1, 2],
    {"error": "boom"},
    {"error": {"nested": True}},
    {"count": "not-a-number", "cached": "yes"},
    {"entries": None},
    {"entries": 1},
    {"entries": "x"},
    {"entries": {"a": 1}},
    {"entries": [None, 1, "x", {"name_value": None}, {"name_value": 123}, {"common_name": [1]}]},
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "ip": "93.184.216.34",
    "timeout": 10.0,
    "use_cache": True,
    "offline_fallback": True,
    "cert_data": {
        "count": 2,
        "cached": False,
        "offline_fallback": False,
        "entries": [{"name_value": "www.example.com"}],
    },
    "subdomains": ["example.com", "www.example.com"],
    "notes": ["Result served from cache"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_cert_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_cert_report_json:
        assert output == "{}"


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cert_data", HOSTILE_CERT_DATA)
def test_cert_formatters_tolerate_hostile_cert_data(
    formatter: Callable[[Any], str], cert_data: object
) -> None:
    output = formatter({"cert_data": cert_data})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("subdomains", HOSTILE_SUBDOMAINS)
def test_cert_formatters_tolerate_hostile_subdomains(
    formatter: Callable[[Any], str], subdomains: object
) -> None:
    output = formatter({"subdomains": subdomains})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_cert_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CERT_FORMATTERS, ids=_formatter_id)
def test_cert_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_cert_report_markdown:
        assert "example.com" in output
        assert "www.example.com" in output
        assert "Subdomains" in output
    elif formatter is format_cert_report_csv:
        assert "example.com" in output
        assert "www.example.com" in output
