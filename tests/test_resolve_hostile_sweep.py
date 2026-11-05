"""Hostile-shape sweep for resolve report formatters."""

from __future__ import annotations

import json

from ethscan import resolve

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_resolve_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(resolve.format_resolve_report_json(bad))
        md = resolve.format_resolve_report_markdown(bad)
        csv_text = resolve.format_resolve_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Forward/Reverse Resolution Report" in md


def test_resolve_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"records": "x", "record_types_queried": "x", "target": [1]},
        {"records": {"A": "1.2.3.4", "MX": [None, {"x": 1}]}},
        {"records": {"TXT": None}, "is_ip": "yes"},
    ]
    for data in cases:
        json.loads(resolve.format_resolve_report_json(data))
        md = resolve.format_resolve_report_markdown(data)
        csv_text = resolve.format_resolve_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Forward/Reverse Resolution Report" in md
