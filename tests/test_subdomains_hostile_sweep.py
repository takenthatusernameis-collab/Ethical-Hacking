"""Hostile-shape sweep for subdomains report formatters."""

from __future__ import annotations

import json

from ethscan import subdomains

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_subdomains_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(subdomains.format_subdomains_report_json(bad))
        md = subdomains.format_subdomains_report_markdown(bad)
        csv_text = subdomains.format_subdomains_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Subdomain Enumeration Report" in md


def test_subdomains_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": "x", "domain": "x", "resolved": None},
        {"target": "x", "domain": "x", "resolved": "notalist"},
        {
            "target": "x",
            "domain": "x",
            "resolved": [None, 5, "str", [], {}, {"subdomain": "a"}],
        },
        {"target": "x", "domain": "x", "all_results": None},
        {"target": "x", "domain": "x", "per_depth": [None, {"depth": 1}]},
        {"target": "x", "domain": "x", "resolver": "x"},
    ]
    for data in cases:
        json.loads(subdomains.format_subdomains_report_json(data))
        md = subdomains.format_subdomains_report_markdown(data)
        csv_text = subdomains.format_subdomains_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Subdomain Enumeration Report" in md
