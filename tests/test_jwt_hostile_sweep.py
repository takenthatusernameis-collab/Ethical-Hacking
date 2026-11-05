"""Hostile-shape sweep for jwt report formatters."""

from __future__ import annotations

import json

from ethscan.jwt import (
    format_jwt_report_csv,
    format_jwt_report_json,
    format_jwt_report_markdown,
)

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_jwt_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_jwt_report_json(bad))
        md = format_jwt_report_markdown(bad)
        csv_text = format_jwt_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan JWT Inspection Report" in md


def test_jwt_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"valid_structure": True, "header": "x", "claims": "x", "findings": "x"},
        {"valid_structure": False, "findings": [None, 1, "ok"]},
        {"valid_structure": True, "header": {1: "x"}, "other_claims": {1: 2}},
        {"valid_structure": True, "standard_claims": "x", "other_claims": "x"},
        {"valid_structure": True, "claims": {"exp": "x"}, "exp_status": 123},
    ]
    for data in cases:
        json.loads(format_jwt_report_json(data))
        md = format_jwt_report_markdown(data)
        csv_text = format_jwt_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan JWT Inspection Report" in md
