"""Permanent sweep test: hostile scanner formatter inputs are rendered, never raised.

Covers ``format_scan_report_markdown``, ``format_scan_report_csv`` and
``format_scan_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``details``, ``open_ports``).
Every shape yields a string and never raises, and the JSON formatter always
emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.scanner import (
    format_scan_report_csv,
    format_scan_report_json,
    format_scan_report_markdown,
)

SCANNER_FORMATTERS: list[Callable[[Any], str]] = [
    format_scan_report_markdown,
    format_scan_report_csv,
    format_scan_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", "x"),
    ("target", None),
    ("target", []),
    ("host", "x"),
    ("host", None),
    ("host", []),
    ("ports_scanned", "x"),
    ("ports_scanned", None),
    ("ports_scanned", []),
    ("ports_scanned", 1.5),
    ("ports_scanned", {}),
    ("open_ports", "x"),
    ("open_ports", None),
    ("open_ports", {}),
    ("open_ports", 1),
    ("details", "x"),
    ("details", None),
    ("details", {}),
    ("details", 1),
]

HOSTILE_DETAIL_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"port": None},
    {"port": 1},
    {"port": []},
    {"port": "x"},
    {"open": "x"},
    {"open": None},
    {"open": []},
    {"open": 1},
    {"open": {}},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-string", []],
]

WELL_FORMED = {
    "target": "example.com",
    "host": "192.168.1.1",
    "ports_scanned": 3,
    "open_ports": [80, 443],
    "details": [
        {"port": 80, "open": True},
        {"port": 443, "open": True},
        {"port": 22, "open": False},
    ],
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "host": "192.168.1.1",
    "ports_scanned": 0,
    "open_ports": [],
    "details": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_scanner_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_scanner_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("details", HOSTILE_DETAIL_ENTRY)
def test_scanner_formatters_tolerate_hostile_details(
    formatter: Callable[[Any], str], details: object
) -> None:
    output = formatter({"details": details})
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["details"])
@pytest.mark.parametrize("entry", HOSTILE_DETAIL_ENTRY)
def test_scanner_formatters_tolerate_hostile_entry_lists(
    formatter: Callable[[Any], str], field: str, entry: object
) -> None:
    output = formatter({field: entry})
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["open_ports"])
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_scanner_formatters_tolerate_hostile_simple_lists(
    formatter: Callable[[Any], str], field: str, lst: object
) -> None:
    output = formatter({field: lst})
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
def test_scanner_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": "x",
            "host": None,
            "ports_scanned": "many",
            "open_ports": [None, 1, {}, "not-a-port", []],
            "details": [
                None,
                {"port": [], "open": "yes"},
                "not-a-dict",
                1,
                {"port": 80, "open": {}},
            ],
        }
    )
    assert isinstance(output, str)
    if formatter is format_scan_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
def test_scanner_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_scan_report_markdown:
        assert "# ethscan Port Scan Report" in output
        assert "**Target:** example.com" in output
        assert "**Host:** 192.168.1.1" in output
        assert "**Ports Scanned:** 3" in output
        assert "**Open Ports:** 80, 443" in output
        assert "## Port Details" in output
        assert "| 80 | Open |" in output
        assert "| 443 | Open |" in output
        assert "| 22 | Closed |" in output
    elif formatter is format_scan_report_csv:
        assert "port,open" in output
        assert "80,true" in output
        assert "443,true" in output
        assert "22,false" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "192.168.1.1"
        assert parsed["ports_scanned"] == 3
        assert parsed["open_ports"] == [80, 443]
        assert len(parsed["details"]) == 3
        assert parsed["details"][0]["port"] == 80
        assert parsed["details"][0]["open"] is True
        assert parsed["details"][2]["port"] == 22
        assert parsed["details"][2]["open"] is False


@pytest.mark.parametrize("formatter", SCANNER_FORMATTERS, ids=_formatter_id)
def test_scanner_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_scan_report_markdown:
        assert "# ethscan Port Scan Report" in output
        assert "**Target:** example.com" in output
        assert "**Host:** 192.168.1.1" in output
        assert "**Ports Scanned:** 0" in output
        assert "**Open Ports:** None" in output
        assert "*No ports scanned.*" in output
    elif formatter is format_scan_report_csv:
        assert "port,open" in output
        lines = output.strip().split("\n")
        assert len(lines) == 1
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "192.168.1.1"
        assert parsed["ports_scanned"] == 0
        assert parsed["open_ports"] == []
        assert parsed["details"] == []