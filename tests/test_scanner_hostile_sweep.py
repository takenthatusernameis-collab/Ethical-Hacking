"""Hostile-shape sweep for scanner report formatters."""

from __future__ import annotations

import json

from ethscan.scanner import (
    format_scan_report_csv,
    format_scan_report_json,
    format_scan_report_markdown,
)

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_scan_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_scan_report_json(bad))
        md = format_scan_report_markdown(bad)
        csv_text = format_scan_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Port Scan Report" in md


def test_scan_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": 123, "host": [], "ports_scanned": "x", "open_ports": "x"},
        {"details": "x"},
        {"details": [None, 1, "bad", {"port": 123, "open": [], "host": "x"}]},
        {"open_ports": [None, "x", 80]},
        {"ports_scanned": {}, "target": None},
    ]
    for data in cases:
        json.loads(format_scan_report_json(data))
        md = format_scan_report_markdown(data)
        csv_text = format_scan_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Port Scan Report" in md
