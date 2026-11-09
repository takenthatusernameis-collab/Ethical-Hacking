"""Hostile-shape sweep for hash/check report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.hash import (
    format_check_report_csv,
    format_check_report_json,
    format_check_report_markdown,
    format_hash_report_csv,
    format_hash_report_json,
    format_hash_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_hash_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_hash_report_json(cast(Any, bad_any)))
        json.loads(format_check_report_json(cast(Any, bad_any)))
        md = format_hash_report_markdown(cast(Any, bad_any))
        csv_text = format_hash_report_csv(cast(Any, bad_any))
        cmd = format_check_report_markdown(cast(Any, bad_any))
        ccsv = format_check_report_csv(cast(Any, bad_any))
        assert "ethscan Password Hash Report" in md
        assert "ethscan Password Check Report" in cmd
        assert isinstance(csv_text, str)
        assert isinstance(ccsv, str)


def test_hash_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"results": "x", "notes": "x", "algorithm": 123},
        {"results": [None, 1, "bad", {"password": 123, "hash": []}]},
        {"notes": [None, {"k": "v"}]},
        {"iterations": "x", "salt_value": []},
    ]
    for data in cases:
        json.loads(format_hash_report_json(data))
        assert "ethscan Password Hash Report" in format_hash_report_markdown(data)
        assert isinstance(format_hash_report_csv(data), str)
