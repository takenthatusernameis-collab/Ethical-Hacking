"""Hostile-shape sweep for validate report formatters."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import validate

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_validate_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(validate.format_validate_report_json(cast(Any, bad_any)))
        md = validate.format_validate_report_markdown(cast(Any, bad_any))
        csv_text = validate.format_validate_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# ethscan Validate Report" in md


def test_validate_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"ports": None},
        {"cidrs": None},
        {"summary": "x"},
        {"ports": [{"spec": 5}]},
        {"ports": [None, {"spec": "80"}]},
        {"cidrs": [None, {"network": "x"}]},
        {"cidrs": [{"spec": "1.2.3.4", "valid": True, "network": "notadict"}]},
        {"ports": "notalist"},
        {"cidrs": "notalist"},
    ]
    for data in cases:
        json.loads(validate.format_validate_report_json(data))
        md = validate.format_validate_report_markdown(data)
        csv_text = validate.format_validate_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
