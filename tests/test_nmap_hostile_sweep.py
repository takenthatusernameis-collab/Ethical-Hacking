"""Hostile-shape sweep for nmap report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.nmap import (
    NmapResult,
    format_nmap_report_csv,
    format_nmap_report_json,
    format_nmap_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_nmap_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_nmap_report_json(cast(NmapResult, bad_any)))
        md = format_nmap_report_markdown(cast(NmapResult, bad_any))
        csv_text = format_nmap_report_csv(cast(NmapResult, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Nmap Vulnerability Report" in md


def test_nmap_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"input_file": 123, "hosts_scanned": "x", "severity_counts": "x"},
        {"services": "x", "findings": "x", "notes": "x"},
        {"services": [None, 1, "bad", {"host": 123, "hostnames": "x"}]},
        {"findings": [None, {"id": None, "severity": 1, "hostnames": "x"}]},
        {"severity_counts": {123: "x"}, "notes": [None, {"k": "v"}]},
    ]
    for data in cases:
        json.loads(format_nmap_report_json(cast(NmapResult, data)))
        md = format_nmap_report_markdown(cast(NmapResult, data))
        csv_text = format_nmap_report_csv(cast(NmapResult, data))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Nmap Vulnerability Report" in md
