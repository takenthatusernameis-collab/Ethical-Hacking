"""Hostile-shape sweep for headers report formatters.

``headers`` has no cache/file/JSON parsing paths; transport/body handling is
covered by ``tests/test_http_hostile_sweep.py``. This file covers formatter
robustness for hostile report shapes that can reach the CLI/reporting path:
malformed top-level containers and hostile nested fields must never raise.
"""

from __future__ import annotations

import json

from ethscan.headers import (
    format_headers_report_csv,
    format_headers_report_json,
    format_headers_report_markdown,
)

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_headers_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_headers_report_json(bad))
        md = format_headers_report_markdown(bad)
        csv_text = format_headers_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Security Headers Report" in md
        assert "field,value" in csv_text


def test_headers_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"security_headers": None},
        {"security_headers": "x"},
        {"security_headers": 123},
        {"security_headers": {"present": "x", "missing": "x"}},
        {"security_headers": {"present": [None, 1, {"k": "v"}], "missing": [None]}},
        {"findings": "x"},
        {"findings": [None, 1, {"k": "v"}]},
        {"headers": "x"},
        {"error": {"nested": "boom"}},
    ]
    for data in cases:
        json.loads(format_headers_report_json(data))
        assert "ethscan Security Headers Report" in format_headers_report_markdown(data)
        assert "field,value" in format_headers_report_csv(data)
