"""Hostile-shape sweep for osdetect report formatters."""

from __future__ import annotations

import json

from ethscan import osdetect

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_osdetect_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(osdetect.format_osdetect_report_json(bad))
        md = osdetect.format_osdetect_report_markdown(bad)
        csv_text = osdetect.format_osdetect_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan OS Detection Report" in md


def test_osdetect_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": "x", "host": "x", "ports_probed": 1, "probes": None},
        {"target": "x", "host": "x", "ports_probed": 1, "probes": "notalist"},
        {
            "target": "x",
            "host": "x",
            "ports_probed": 1,
            "probes": [None, 5, "str", [], {}, {"port": 1}, {"port": "p"}],
        },
        {
            "target": "x",
            "host": "x",
            "ports_probed": 1,
            "probes": [{"port": "p"}],
            "inferred_os": None,
        },
        {"target": "x", "host": "x", "ports_probed": 1, "inferred_os": "linux"},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": "x"},
        {"target": "x", "host": "x", "ports_probed": 1, "notes": [None, 5, {}]},
    ]
    for data in cases:
        json.loads(osdetect.format_osdetect_report_json(data))
        md = osdetect.format_osdetect_report_markdown(data)
        csv_text = osdetect.format_osdetect_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan OS Detection Report" in md
