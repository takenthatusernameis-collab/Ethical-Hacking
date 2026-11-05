"""Hostile-shape sweep for stale report formatters."""

from __future__ import annotations

import json

from ethscan import stale

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_stale_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(stale.format_stale_report_json(bad))
        md = stale.format_stale_report_markdown(bad)
        csv_text = stale.format_stale_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Stale DNS Record Detection Report" in md


def test_stale_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"stale_results": None},
        {"stale_results": "notalist"},
        {"stale_results": [None, 5, "str", [], {}, {"domain": "x"}]},
        {"results": None},
        {"results": [None, {"domain": "x"}]},
        {"total_checked": "x", "stale_count": "x", "fresh_count": "x"},
    ]
    for data in cases:
        json.loads(stale.format_stale_report_json(data))
        md = stale.format_stale_report_markdown(data)
        csv_text = stale.format_stale_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Stale DNS Record Detection Report" in md
