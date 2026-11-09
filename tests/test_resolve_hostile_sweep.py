"""Hostile-shape sweep for resolve report formatters."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import resolve

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_resolve_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(resolve.format_resolve_report_json(cast(Any, bad_any)))
        md = resolve.format_resolve_report_markdown(cast(Any, bad_any))
        csv_text = resolve.format_resolve_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Forward/Reverse Resolution Report" in md


def test_resolve_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
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
