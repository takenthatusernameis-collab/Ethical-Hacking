"""Hostile-shape sweep for brute report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.brute import (
    format_brute_report_csv,
    format_brute_report_json,
    format_brute_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_brute_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_brute_report_json(cast(Any, bad_any)))
        md = format_brute_report_markdown(cast(Any, bad_any))
        csv_text = format_brute_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Brute Force Report" in md


def test_brute_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"target": 123, "host": None, "results": "x", "successful": "x"},
        {"results": [None, 1, "bad", {"username": 123, "password": [], "success": "x"}]},
        {"successful": [None, {"username": [], "password": None}]},
        {"attempts": "x", "successful_count": "x"},
    ]
    for data in cases:
        json.loads(format_brute_report_json(data))
        md = format_brute_report_markdown(data)
        csv_text = format_brute_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Brute Force Report" in md
