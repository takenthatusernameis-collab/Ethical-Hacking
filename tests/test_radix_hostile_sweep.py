"""Hostile-shape sweep for radix report formatters."""

from __future__ import annotations

import json

from ethscan import radix

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_radix_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(radix.format_radix_report_json(bad))
        md = radix.format_radix_report_markdown(bad)
        csv_text = radix.format_radix_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Radix Tree Report" in md


def test_radix_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"network_count": "x", "merged": None},
        {"network_count": 1, "merged": "notalist"},
        {
            "network_count": 1,
            "merged": [None, 5, "str", [], {}, "10.0.0.0/8"],
            "cidrs": [None, {}],
        },
        {"contains": None},
        {"contains": {"ip": "1.2.3.4", "in_network": "yes", "matched_network": None}},
        {"diff": None},
        {
            "diff": {
                "diff_network_count": 1,
                "diff_merged_network_count": 1,
                "difference_network_count": 1,
                "total_diff_addresses": 1,
                "difference": [None, "not-a-cidr", "10.0.0.0/8"],
            }
        },
        {"radix_tree": "x"},
    ]
    for data in cases:
        json.loads(radix.format_radix_report_json(data))
        md = radix.format_radix_report_markdown(data)
        csv_text = radix.format_radix_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Radix Tree Report" in md
