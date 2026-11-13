"""Hostile-shape sweep for dnsbrute report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan import dnsbrute

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_dnsbrute_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(dnsbrute.format_dnsbrute_report_json(cast(Any, bad_any)))
        md = dnsbrute.format_dnsbrute_report_markdown(cast(Any, bad_any))
        csv_text = dnsbrute.format_dnsbrute_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Brute Force Report" in md


def test_dnsbrute_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
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
        {"target": "x", "axfr": [{"nameserver": "ns", "records": 123}]},
        {"target": "x", "axfr": [{"nameserver": "ns", "records": True}]},
        {"target": "x", "axfr": [{"nameserver": "ns", "records": "scalar"}]},
        {"target": "x", "resolved": [{"subdomain": "a", "hostname": "a.x", "a": 123, "aaaa": []}]},
        {"target": "x", "resolved": [{"subdomain": "a", "hostname": "a.x", "a": [], "aaaa": True}]},
        {"target": "x", "all_results": [{"subdomain": "a", "hostname": "a.x", "a": 1.5, "aaaa": []}]},
        {"target": "x", "recursive_axfr": [{"nameserver": "ns", "records": b"bytes"}]},
    ]
    for data in cases:
        json.loads(dnsbrute.format_dnsbrute_report_json(data))
        md = dnsbrute.format_dnsbrute_report_markdown(data)
        csv_text = dnsbrute.format_dnsbrute_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan DNS Brute Force Report" in md
