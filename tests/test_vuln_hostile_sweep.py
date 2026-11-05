"""Hostile-shape sweep for vuln report formatters."""

from __future__ import annotations

import json

from ethscan.vuln import (
    format_vuln_report_csv,
    format_vuln_report_json,
    format_vuln_report_markdown,
)

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_vuln_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_vuln_report_json(bad))
        md = format_vuln_report_markdown(bad)
        csv_text = format_vuln_report_csv(bad)
        assert "ethscan Vulnerability Report" in md
        assert isinstance(csv_text, str)


def test_vuln_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"findings": "x", "notes": "x", "severity_counts": "x"},
        {"findings": [None, 1, "bad", {"id": 123, "severity": []}]},
        {"notes": [None, {"k": "v"}]},
        {"recursive": True, "recursive_hosts_scanned": "x", "recursive_findings": "x"},
        {"severity_filter": [], "min_severity_filter": {}},
    ]
    for data in cases:
        json.loads(format_vuln_report_json(data))
        assert "ethscan Vulnerability Report" in format_vuln_report_markdown(data)
        assert isinstance(format_vuln_report_csv(data), str)
"""
"""
