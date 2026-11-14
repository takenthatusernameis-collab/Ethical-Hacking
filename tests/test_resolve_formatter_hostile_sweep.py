"""Permanent sweep test: hostile resolve formatter inputs are rendered, never raised.

Covers ``format_resolve_report_markdown``, ``format_resolve_report_csv`` and
``format_resolve_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``records``, ``record_types_queried``,
``target``, ``normalized``, ``is_ip``, ``dnspython_available``, ``server``
and their nested structures). Every shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.resolve import (
    format_resolve_report_csv,
    format_resolve_report_json,
    format_resolve_report_markdown,
)

RESOLVE_FORMATTERS: list[Callable[[Any], str]] = [
    format_resolve_report_markdown,
    format_resolve_report_csv,
    format_resolve_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", None),
    ("target", 1),
    ("target", []),
    ("normalized", None),
    ("normalized", 1),
    ("normalized", []),
    ("is_ip", "yes"),
    ("is_ip", []),
    ("is_ip", 1),
    ("record_types_queried", "x"),
    ("record_types_queried", None),
    ("record_types_queried", [None, 1, {}]),
    ("records", "x"),
    ("records", None),
    ("records", [None, 1, {}]),
    ("dnspython_available", "yes"),
    ("dnspython_available", 1),
    ("server", None),
    ("server", 1),
    ("server", []),
]

HOSTILE_RECORDS: list[object] = [
    None,
    1,
    "x",
    {"A": "1.2.3.4", "MX": [None, {"x": 1}]},
    {"TXT": None},
    {"A": None, "AAAA": [1, 2, 3]},
    {"CNAME": [None, 1, {}, "text"]},
    {"A": [None, 1, 2.5, ["nested"], {"a": 1}]},
    {"PTR": True},
    {"AAAA": {"nested": "dict"}},
    {"A": "1.2.3.4", "MX": None},
    {"A": "1.2.3.4", "MX": [None, 1, {}, "text", b"bytes"]},
]

HOSTILE_RECORD_TYPES_QUERIED: list[object] = [
    None,
    1,
    "x",
    [None, 1, {}, "A"],
    ["A", None, 1, {"type": "MX"}],
]

WELL_FORMED = {
    "target": "example.com",
    "normalized": "example.com",
    "is_ip": False,
    "record_types_queried": ["A", "AAAA", "CNAME"],
    "records": {
        "A": ["1.2.3.4", "5.6.7.8"],
        "AAAA": ["2001:db8::1"],
        "CNAME": ["www.example.com"],
    },
    "dnspython_available": True,
    "server": "8.8.8.8",
}

WELL_FORMED_IP = {
    "target": "8.8.8.8",
    "normalized": "8.8.8.8",
    "is_ip": True,
    "record_types_queried": ["PTR"],
    "records": {"PTR": ["dns.google"]},
    "dnspython_available": False,
    "server": None,
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_resolve_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_resolve_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_resolve_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_resolve_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("records", HOSTILE_RECORDS)
def test_resolve_formatters_tolerate_hostile_records(
    formatter: Callable[[Any], str], records: object
) -> None:
    output = formatter({"target": "example.com", "records": records})
    assert isinstance(output, str)
    if formatter is format_resolve_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("rtype_q", HOSTILE_RECORD_TYPES_QUERIED)
def test_resolve_formatters_tolerate_hostile_record_types_queried(
    formatter: Callable[[Any], str], rtype_q: object
) -> None:
    output = formatter({"target": "example.com", "record_types_queried": rtype_q})
    assert isinstance(output, str)
    if formatter is format_resolve_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
def test_resolve_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": None,
            "normalized": 1,
            "is_ip": [],
            "record_types_queried": [None, 1, {}],
            "records": {"A": [None, 1, {}, "text"], "MX": "scalar"},
            "dnspython_available": "yes",
            "server": 123,
        }
    )
    assert isinstance(output, str)
    if formatter is format_resolve_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
def test_resolve_formatters_render_well_formed_domain(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_resolve_report_markdown:
        assert "# ethscan DNS Forward/Reverse Resolution Report" in output
        assert "**Target:** example.com" in output
        assert "**Normalized:** example.com" in output
        assert "**Type:** Domain Name" in output
        assert "A, AAAA, CNAME" in output
        assert "**dnspython Available:** Yes" in output
        assert "**Custom Resolver:** 8.8.8.8" in output
        assert "## A Records" in output
        assert "1.2.3.4" in output
        assert "5.6.7.8" in output
        assert "## AAAA Records" in output
        assert "2001:db8::1" in output
        assert "## CNAME Records" in output
        assert "www.example.com" in output
    elif formatter is format_resolve_report_csv:
        assert "example.com" in output
        assert "record_type" in output
        assert "record_value" in output
        assert "A" in output
        assert "1.2.3.4" in output
        assert "AAAA" in output
        assert "2001:db8::1" in output
        assert "CNAME" in output
        assert "www.example.com" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["normalized"] == "example.com"
        assert parsed["is_ip"] is False
        assert parsed["record_types_queried"] == ["A", "AAAA", "CNAME"]
        assert parsed["records"]["A"] == ["1.2.3.4", "5.6.7.8"]
        assert parsed["records"]["AAAA"] == ["2001:db8::1"]
        assert parsed["records"]["CNAME"] == ["www.example.com"]
        assert parsed["dnspython_available"] is True
        assert parsed["server"] == "8.8.8.8"


@pytest.mark.parametrize("formatter", RESOLVE_FORMATTERS, ids=_formatter_id)
def test_resolve_formatters_render_well_formed_ip(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_IP))
    assert isinstance(output, str)
    if formatter is format_resolve_report_markdown:
        assert "**Type:** IP Address" in output
        assert "PTR" in output
        assert "dns.google" in output
    elif formatter is format_resolve_report_csv:
        assert "8.8.8.8" in output
        assert "PTR" in output
        assert "dns.google" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "8.8.8.8"
        assert parsed["is_ip"] is True
        assert parsed["record_types_queried"] == ["PTR"]
        assert parsed["records"]["PTR"] == ["dns.google"]