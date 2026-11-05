"""Hostile-shape sweep for cidr report formatters."""

from __future__ import annotations

import json

from ethscan import cidr

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_cidr_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(cidr.format_cidr_report_json(bad))
        md = cidr.format_cidr_report_markdown(bad)
        csv_text = cidr.format_cidr_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan CIDR Network Calculator Report" in md


def test_cidr_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"cidr": "10.0.0.0/8", "network": None},
        {"cidr": "10.0.0.0/8", "network": "notadict"},
        {"cidr": 123, "ip_version": None, "network": {}},
        {"contains": "x"},
        {"diff": None},
        {
            "diff": {
                "diff_cidr": "x",
                "difference_network_count": 1,
                "total_diff_addresses": 1,
                "difference": [None, "not-a-cidr", "10.0.0.0/8"],
            }
        },
    ]
    for data in cases:
        json.loads(cidr.format_cidr_report_json(data))
        md = cidr.format_cidr_report_markdown(data)
        csv_text = cidr.format_cidr_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan CIDR Network Calculator Report" in md
