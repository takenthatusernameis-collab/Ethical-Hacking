"""Hostile-shape sweep for urlcheck report formatters.

``urlcheck`` composes web/fuzz/ssl results and has no cache/file/JSON parsing
paths of its own; transport/body handling is covered by
``tests/test_http_hostile_sweep.py``. This file covers formatter robustness
for hostile report shapes: malformed top-level containers and hostile nested
section data must never raise.
"""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan.urlcheck import (
    format_urlcheck_report_csv,
    format_urlcheck_report_json,
    format_urlcheck_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_urlcheck_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_urlcheck_report_json(cast(Any, bad_any)))
        md = format_urlcheck_report_markdown(cast(Any, bad_any))
        csv_text = format_urlcheck_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Consolidated Web Assessment Report" in md
        assert "section,key,value" in csv_text


def test_urlcheck_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"summary": "x"},
        {"summary": {"web_checks_run": "x"}},
        {"web": "x"},
        {"web": {"security_headers": "x", "information_disclosure": "x", "ssl": "x"}},
        {"web": {"security_headers": {"present": [None], "missing": "x"}}},
        {"fuzz": "x"},
        {"fuzz": {"findings": "x", "all_results": "x"}},
        {"fuzz": {"findings": [None, 1], "all_results": [None, 1, {"path": "/"}]}},
        {"ssl": "x"},
        {"ssl": {"cert": "x"}},
        {"ssl": {"cert": {"subject": {"nested": "x"}}, "valid": "x"}},
    ]
    for data in cases:
        json.loads(format_urlcheck_report_json(data))
        assert "ethscan Consolidated Web Assessment Report" in format_urlcheck_report_markdown(
            data
        )
        assert "section,key,value" in format_urlcheck_report_csv(data)
