"""Hostile-shape sweep for dnsbrute report formatters."""

from __future__ import annotations

import json

from ethscan import dnsbrute

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_dnsbrute_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(dnsbrute.format_dnsbrute_report_json(bad))
        md = dnsbrute.format_dnsbrute_report_markdown(bad)
        csv_text = dnsbrute.format_dnsbrute_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Brute Force Report" in md


def test_dnsbrute_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": "x", "axfr": None},
        {"target": "x", "axfr": "notalist"},
        {
            "target": "x",
            "axfr": [None, 5, "str", [], {}, {"nameserver": "ns.example.com"}],
        },
        {"target": "x", "all_results": [None, {"subdomain": "a"}]},
        {"target": "x", "recursive_axfr": [None, {}]},
        {"target": "x", "nameservers": "x"},
        {"target": "x", "resolved": None},
    ]
    for data in cases:
        json.loads(dnsbrute.format_dnsbrute_report_json(data))
        md = dnsbrute.format_dnsbrute_report_markdown(data)
        csv_text = dnsbrute.format_dnsbrute_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Brute Force Report" in md
