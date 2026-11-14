"""Permanent sweep test: hostile trace formatter inputs are rendered, never raised.

Covers ``format_trace_report_json``, ``format_trace_report_markdown`` and
``format_trace_report_csv`` against hostile top-level shapes and hostile nested
values in key report sections (``hops``, ``recursive_traces``, ``notes``).
Every shape yields a string and never raises, and the JSON formatter always
emits parseable JSON.

Includes regressions for non-numeric hop RTT values (``rtt_avg_ms`` /
``rtt_ms``), which previously raised ``ValueError``/``TypeError`` inside the
markdown formatter's ``_fmt_rtt`` helper.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.trace import (
    _fmt_rtt,
    format_trace_report_csv,
    format_trace_report_json,
    format_trace_report_markdown,
)

TRACE_FORMATTERS: list[Callable[[Any], str]] = [
    format_trace_report_json,
    format_trace_report_markdown,
    format_trace_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", []),
    ("target", {}),
    ("target", 1),
    ("target", None),
    ("host", []),
    ("host", {}),
    ("ip", []),
    ("ip", {}),
    ("dst_ip", []),
    ("dst_ip", {}),
    ("port", "x"),
    ("port", {}),
    ("port", []),
    ("max_hops", "x"),
    ("max_hops", {}),
    ("max_hops", []),
    ("timeout", "x"),
    ("timeout", {}),
    ("probes_per_hop", "x"),
    ("probes_per_hop", {}),
    ("recursive", "x"),
    ("recursive", []),
    ("max_depth", "x"),
    ("max_depth", {}),
    ("error", []),
    ("error", {}),
    ("destination_reached", "x"),
    ("destination_reached", []),
    ("reached_destination", "x"),
    ("reached", "x"),
    ("hops", "x"),
    ("hops", None),
    ("hops", {}),
    ("hops", 1),
    ("hops", 1.5),
    ("recursive_traces", "x"),
    ("recursive_traces", None),
    ("recursive_traces", {}),
    ("recursive_traces", 1),
    ("recursive_traces", 1.5),
    ("notes", "x"),
    ("notes", None),
    ("notes", {}),
    ("notes", 1),
    ("notes", 1.5),
]

HOSTILE_HOP_ENTRY: list[object] = [
    None,
    1,
    "x",
    [],
    {},
    {"hop": []},
    {"hop": {}},
    {"hop": None},
    {"hop": "x"},
    {"ttl": []},
    {"ttl": {}},
    {"ip": []},
    {"ip": {}},
    {"ip": 1},
    {"ip": None},
    {"host": []},
    {"host": {}},
    {"host": 1},
    {"host": None},
    {"response_type": []},
    {"response_type": {}},
    {"response_type": 1},
    {"response_type": None},
    {"reached": "x"},
    {"reached": []},
    {"reached_destination": "x"},
    {"reached_destination": []},
    {"rtt_avg_ms": "x"},
    {"rtt_avg_ms": {}},
    {"rtt_avg_ms": [1]},
    {"rtt_avg_ms": None},
    {"rtt_avg_ms": True},
    {"rtt_avg_ms": "5.0"},
    {"rtt_avg_ms": float("nan")},
    {"rtt_ms": "x"},
    {"rtt_ms": {}},
    {"rtt_ms": [1]},
    {"rtt_ms": None},
    {"rtt_ms": True},
    {"rtt_ms": "5.0"},
    {"rtt_avg_ms": "x", "rtt_ms": 1},
    {"rtt_avg_ms": 1, "rtt_ms": "x"},
]

HOSTILE_NOTES: list[object] = [
    [None],
    [1],
    [{}],
    [[]],
    [1.5],
    [b"bytes"],
    ["ok", None, 1, {}],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-dict", []],
    [{"hop": 1}, None, "bad", 3],
]

HOSTILE_RECURSIVE_ENTRY: list[object] = [
    None,
    1,
    "x",
    [],
    {},
    {"target": []},
    {"target": {}},
    {"target": "t", "hops": None},
    {"target": "t", "hops": "x"},
    {"target": "t", "hops": {}},
    {"target": "t", "hops": [None, 1, {"hop": 2}]},
    {"target": "t", "hops": [{"rtt_avg_ms": "x"}]},
    {"target": "t", "hops": [{"rtt_ms": {}}]},
    {"target": "t", "notes": [None, {}, []]},
    {"target": "t", "error": []},
    {"target": "t", "recursive_traces": "x"},
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "ip": "93.184.215.14",
    "dst_ip": "93.184.215.14",
    "port": 80,
    "max_hops": 30,
    "timeout": 2.0,
    "probes_per_hop": 3,
    "hops": [
        {
            "hop": 1,
            "ttl": 1,
            "ip": "10.0.0.1",
            "host": "10.0.0.1",
            "response_type": "ICMP_TTL_EXCEEDED",
            "rtt_ms": 1.5,
            "rtt_avg_ms": 1.5,
            "reached_destination": False,
            "reached": False,
        },
        {
            "hop": 2,
            "ttl": 2,
            "ip": "93.184.215.14",
            "host": "93.184.215.14",
            "response_type": "REACHED",
            "rtt_ms": 10.0,
            "rtt_avg_ms": 10.0,
            "reached_destination": True,
            "reached": True,
        },
    ],
    "hop_count": 2,
    "destination_reached": True,
    "reached_destination": True,
    "reached": True,
    "notes": ["Trace completed"],
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "hops": [],
    "notes": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "N/A"),
        (0.0, "0.00ms"),
        (1.234, "1.23ms"),
        ("5.0", "5.00ms"),
        ("x", "N/A"),
        ("", "N/A"),
        ({}, "N/A"),
        ([1], "N/A"),
        (True, "N/A"),
        (False, "N/A"),
    ],
)
def test_fmt_rtt_hostile_values_are_guarded(value: object, expected: str) -> None:
    assert _fmt_rtt(cast(Any, value)) == expected


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_trace_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_trace_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_HOP_ENTRY)
def test_trace_formatters_tolerate_hostile_hop_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"hops": [entry]})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_HOP_ENTRY)
def test_trace_formatters_tolerate_hostile_recursive_hop_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"recursive_traces": [{"target": "t", "hops": [entry]}]})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_trace_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_trace_formatters_tolerate_hostile_hops_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"hops": lst})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_trace_formatters_tolerate_hostile_recursive_traces_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"recursive_traces": lst})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_RECURSIVE_ENTRY)
def test_trace_formatters_tolerate_hostile_recursive_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"recursive_traces": [entry]})
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
def test_trace_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": [],
            "port": "x",
            "hops": [None, 1, {"rtt_avg_ms": "x"}, {"rtt_ms": {}}, "not-a-dict"],
            "recursive_traces": [
                None,
                {"target": "t", "hops": [{"rtt_avg_ms": [1]}, None]},
                {"target": [], "hops": "x"},
            ],
            "notes": [None, {}, [], "ok"],
        }
    )
    assert isinstance(output, str)
    if formatter is format_trace_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
def test_trace_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_trace_report_markdown:
        assert "# TCP Traceroute Report" in output
        assert "## Hop Table" in output
        assert "example.com" in output
        assert "10.0.0.1" in output
        assert "1.50ms" in output
        assert "**Reached target:** Yes" in output
    elif formatter is format_trace_report_csv:
        assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in output
        assert "example.com" in output
        assert "93.184.215.14" in output
        assert "true" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert len(parsed["hops"]) == 2
        assert parsed["destination_reached"] is True


@pytest.mark.parametrize("formatter", TRACE_FORMATTERS, ids=_formatter_id)
def test_trace_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_trace_report_markdown:
        assert "# TCP Traceroute Report" in output
        assert "No hops recorded." in output
        assert "**Reached target:** No" in output
    elif formatter is format_trace_report_csv:
        assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in output
        assert "example.com" not in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["hops"] == []
        assert parsed["notes"] == []