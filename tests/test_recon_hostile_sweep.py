"""Hostile-shape sweep for recon report formatters."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import recon

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_recon_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(recon.format_recon_report_json(cast(Any, bad_any)))
        md = recon.format_recon_report_markdown(cast(Any, bad_any))
        csv_text = recon.format_recon_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Reconnaissance Report" in md


def test_recon_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"target": 123, "modules_run": "x", "subdomains": "x"},
        {"dns": {"records": "x", "record_types_queried": 1}},
        {"whois": {"parsed": "x"}, "geo": {"geolocation": "x"}},
        {"trace": {"hops": [None, "x", {}]}, "notes": "x"},
        {"subdomains": {"resolved": [None, "x", {"subdomain": 1}]}},
    ]
    for data in cases:
        json.loads(recon.format_recon_report_json(data))
        md = recon.format_recon_report_markdown(data)
        csv_text = recon.format_recon_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Reconnaissance Report" in md
