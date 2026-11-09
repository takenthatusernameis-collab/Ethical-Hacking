"""Hostile-shape sweep for trace report formatters."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import trace

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_trace_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(trace.format_trace_report_json(cast(Any, bad_any)))
        md = trace.format_trace_report_markdown(cast(Any, bad_any))
        csv_text = trace.format_trace_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# TCP Traceroute Report" in md


def test_trace_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"hops": None},
        {"hops": 5},
        {"hops": "x"},
        {"hops": [{"hop": 1, "ip": "1.1.1.1"}]},
        {"hops": [None, {"hop": 2}]},
        {"recursive_traces": None},
        {"recursive_traces": "x"},
        {"recursive_traces": 7},
        {"recursive_traces": [{"hops": 42}]},
        {"recursive_traces": [{"target": "t", "hops": [{"ip": "1.1.1.1"}]}]},
    ]
    for data in cases:
        json.loads(trace.format_trace_report_json(data))
        md = trace.format_trace_report_markdown(data)
        csv_text = trace.format_trace_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
