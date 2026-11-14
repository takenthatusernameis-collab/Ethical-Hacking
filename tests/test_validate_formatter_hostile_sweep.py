"""Permanent sweep test: hostile validate formatter inputs are rendered, never raised.

Covers ``format_validate_report_json``, ``format_validate_report_markdown`` and
``format_validate_report_csv`` against hostile top-level shapes and hostile
nested values in key report sections (``ports``, ``cidrs``, ``summary``,
``notes``). Every shape yields a string and never raises, and the JSON formatter
always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.validate import (
    format_validate_report_csv,
    format_validate_report_json,
    format_validate_report_markdown,
)

VALIDATE_FORMATTERS: list[Callable[[Any], str]] = [
    format_validate_report_json,
    format_validate_report_markdown,
    format_validate_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("ports", "x"),
    ("ports", None),
    ("ports", {}),
    ("ports", 1),
    ("ports", 1.5),
    ("cidrs", "x"),
    ("cidrs", None),
    ("cidrs", {}),
    ("cidrs", 1),
    ("cidrs", 1.5),
    ("summary", "x"),
    ("summary", None),
    ("summary", []),
    ("summary", 1),
    ("summary", 1.5),
    ("notes", "x"),
    ("notes", None),
    ("notes", {}),
    ("notes", 1),
    ("notes", 1.5),
]

HOSTILE_PORTS_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"spec": []},
    {"spec": {}},
    {"spec": 1},
    {"spec": None},
    {"valid": "x"},
    {"valid": []},
    {"valid": {}},
    {"valid": 1.5},
    {"valid": None},
    {"ports": "x"},
    {"ports": None},
    {"ports": {}},
    {"ports": 1},
    {"ports": [None, "x", {}, [], 1.5]},
    {"count": "x"},
    {"count": None},
    {"count": []},
    {"count": {}},
    {"count": 1.5},
    {"error": []},
    {"error": {}},
    {"error": 1},
]

HOSTILE_CIDRS_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"spec": []},
    {"spec": {}},
    {"spec": 1},
    {"spec": None},
    {"valid": "x"},
    {"valid": []},
    {"valid": {}},
    {"valid": 1.5},
    {"valid": None},
    {"canonical": []},
    {"canonical": {}},
    {"canonical": 1},
    {"canonical": None},
    {"network": "x"},
    {"network": 1},
    {"network": []},
    {"network": None},
    {"network": {"canonical": []}},
    {"network": {"canonical": {}}},
    {"network": {"network_address": []}},
    {"network": {"network_address": {}}},
    {"network": {"broadcast_address": []}},
    {"network": {"broadcast_address": {}}},
    {"network": {"first_host": []}},
    {"network": {"first_host": {}}},
    {"network": {"last_host": []}},
    {"network": {"last_host": {}}},
    {"network": {"total_addresses": "x"}},
    {"network": {"total_addresses": None}},
    {"network": {"total_addresses": []}},
    {"network": {"addresses": "x"}},
    {"network": {"addresses": {}}},
    {"error": []},
    {"error": {}},
    {"error": 1},
]

HOSTILE_SUMMARY: list[object] = [
    {"ports_specified": "x"},
    {"ports_specified": None},
    {"ports_specified": []},
    {"ports_specified": {}},
    {"ports_valid": "x"},
    {"ports_valid": None},
    {"ports_total": "x"},
    {"ports_total": None},
    {"cidrs_specified": "x"},
    {"cidrs_specified": None},
    {"cidrs_valid": "x"},
    {"cidrs_valid": None},
    {"all_valid": "x"},
    {"all_valid": None},
    {"all_valid": []},
    {"all_valid": {}},
]

HOSTILE_NOTES: list[object] = [
    [None],
    [1],
    [{}],
    [[]],
    [1.5],
    [b"bytes"],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-dict", []],
]

WELL_FORMED = {
    "ports": [
        {
            "spec": "80,443,8000-8002",
            "valid": True,
            "ports": [80, 443, 8000, 8001, 8002],
            "count": 5,
            "error": None,
        },
        {
            "spec": "bad",
            "valid": False,
            "ports": [],
            "count": 0,
            "error": "Invalid port number 'bad'",
        },
    ],
    "cidrs": [
        {
            "spec": "192.168.1.0/24",
            "valid": True,
            "canonical": "192.168.1.0/24",
            "network": {
                "network_address": "192.168.1.0",
                "netmask": "255.255.255.0",
                "broadcast_address": "192.168.1.255",
                "wildcard_mask": "0.0.0.255",
                "first_host": "192.168.1.1",
                "last_host": "192.168.1.254",
                "usable_host_count": 254,
                "total_addresses": 256,
                "prefixlen": 24,
                "is_private": True,
                "addresses": None,
            },
            "error": None,
        },
        {
            "spec": "bogus",
            "valid": False,
            "canonical": None,
            "network": None,
            "error": "bad cidr",
        },
    ],
    "summary": {
        "ports_specified": 2,
        "ports_valid": 1,
        "ports_total": 5,
        "cidrs_specified": 2,
        "cidrs_valid": 1,
        "all_valid": False,
    },
    "notes": ["Validated 2 port specification(s).", "Validated 2 CIDR specification(s)."],
}

WELL_FORMED_MINIMAL = {
    "ports": [],
    "cidrs": [],
    "summary": {
        "ports_specified": 0,
        "ports_valid": 0,
        "ports_total": 0,
        "cidrs_specified": 0,
        "cidrs_valid": 0,
        "all_valid": False,
    },
    "notes": ["No port or CIDR specifications provided; nothing to validate."],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_validate_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_validate_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_PORTS_ENTRY)
def test_validate_formatters_tolerate_hostile_ports_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"ports": [entry]})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_CIDRS_ENTRY)
def test_validate_formatters_tolerate_hostile_cidrs_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"cidrs": [entry]})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("summary", HOSTILE_SUMMARY)
def test_validate_formatters_tolerate_hostile_summary(
    formatter: Callable[[Any], str], summary: object
) -> None:
    output = formatter({"summary": summary})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_validate_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_validate_formatters_tolerate_hostile_ports_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"ports": lst})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_validate_formatters_tolerate_hostile_cidrs_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"cidrs": lst})
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
def test_validate_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "ports": [None, 1, {"ports": [None, "x"]}, "not-a-dict"],
            "cidrs": [None, {"network": "x"}, {"spec": []}, 1],
            "summary": "x",
            "notes": [None, {}, []],
        }
    )
    assert isinstance(output, str)
    if formatter is format_validate_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
def test_validate_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_validate_report_markdown:
        assert "# ethscan Validate Report" in output
        assert "## Summary" in output
        assert "## Port Specifications" in output
        assert "## CIDR / Network Specifications" in output
        assert "80,443,8000-8002" in output
        assert "192.168.1.0/24" in output
        assert "## Notes" in output
    elif formatter is format_validate_report_csv:
        assert "type,spec,valid,detail" in output
        assert "port,80,443,8000-8002" in output or "port," in output
        assert "cidr," in output
    else:
        parsed = json.loads(output)
        assert len(parsed["ports"]) == 2
        assert len(parsed["cidrs"]) == 2
        assert parsed["ports"][0]["valid"] is True
        assert parsed["cidrs"][0]["canonical"] == "192.168.1.0/24"


@pytest.mark.parametrize("formatter", VALIDATE_FORMATTERS, ids=_formatter_id)
def test_validate_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_validate_report_markdown:
        assert "# ethscan Validate Report" in output
        assert "## Summary" in output
        assert "*No port specifications provided.*" in output
        assert "*No CIDR specifications provided.*" in output
    elif formatter is format_validate_report_csv:
        assert "type,spec,valid,detail" in output
    else:
        parsed = json.loads(output)
        assert parsed["ports"] == []
        assert parsed["cidrs"] == []
