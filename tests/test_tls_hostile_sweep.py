"""Hostile-shape sweep for tls report formatters."""

from __future__ import annotations

import json

from ethscan.tls import (
    format_tls_report_csv,
    format_tls_report_json,
    format_tls_report_markdown,
)

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_tls_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_tls_report_json(bad))
        md = format_tls_report_markdown(bad)
        csv_text = format_tls_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan TLS Enumeration Report" in md


def test_tls_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"target": 123, "host": None, "port": "x"},
        {"versions": "x", "ciphers": "x", "notes": "x", "supported_versions": "x"},
        {"versions": [None, 1, "bad", {"version": 123, "supported": "x"}]},
        {"ciphers": [None, {"cipher": [], "supported": [], "error": []}]},
        {"notes": [None, 1, "ok"]},
    ]
    for data in cases:
        json.loads(format_tls_report_json(data))
        md = format_tls_report_markdown(data)
        csv_text = format_tls_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan TLS Enumeration Report" in md
