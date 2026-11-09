"""Hostile-shape sweep for web report formatters.

``web`` has no cache/file/JSON parsing paths; transport/body handling is
covered by ``tests/test_http_hostile_sweep.py``. This file covers formatter
robustness for hostile report shapes: malformed top-level containers and
hostile nested fields must never raise.
"""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.web import (
    format_web_report_csv,
    format_web_report_json,
    format_web_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_web_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_web_report_json(cast(Any, bad_any)))
        md = format_web_report_markdown(cast(Any, bad_any))
        csv_text = format_web_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Web Security Report" in md
        assert "field,value" in csv_text


def test_web_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"security_headers": "x"},
        {"security_headers": {"present": [None, 1], "missing": "x"}},
        {"information_disclosure": "x"},
        {"information_disclosure": [None, "s", 1, {"header": "X"}]},
        {"findings": "x"},
        {"findings": [None, 1, {"a": 1}]},
        {"ssl": "x"},
        {"ssl": 123},
        {"ssl": {"error": "boom", "subject": None}},
        {"headers": "x"},
        {"notes": {"a": 1}},
    ]
    for data in cases:
        json.loads(format_web_report_json(data))
        assert "ethscan Web Security Report" in format_web_report_markdown(data)
        assert "field,value" in format_web_report_csv(data)
