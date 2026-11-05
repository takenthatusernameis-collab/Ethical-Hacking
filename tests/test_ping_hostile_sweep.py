"""Hostile-shape sweep for ping report formatters."""

from __future__ import annotations

import json

from ethscan import ping

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_ping_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(ping.format_ping_report_json(bad))
        md = ping.format_ping_report_markdown(bad)
        csv_text = ping.format_ping_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# ethscan Ping Report" in md


def test_ping_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"probes": None},
        {"probes": 5},
        {"probes": "x"},
        {"probes": [None, {"sequence": 2}]},
        {"probes": [{"sequence": 1, "rtt_ms": 5.0}]},
        {"notes": None},
        {"notes": 42},
        {"notes": "x"},
        {"probes": [{"sequence": 1}], "notes": ["ok"]},
    ]
    for data in cases:
        json.loads(ping.format_ping_report_json(data))
        md = ping.format_ping_report_markdown(data)
        csv_text = ping.format_ping_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)