"""Hostile-shape sweep for report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan import report

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_report_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        md = report.format_report_markdown(cast(Any, bad_any))
        csv_text = report.format_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# ethscan Report" in md
    for bad in (None, [], "x", 123, 1.5, True):
        json.loads(report.format_report_json(cast(Any, bad)))


def test_report_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"scan": None},
        {"audit": None},
        {"scan": "x"},
        {"audit": "x"},
        {"scan": {"details": "x"}},
        {"audit": {"results": "x"}},
        {"scan": {"target": "t", "open_ports": [80], "details": [None, {"open": True}]}},
        {"audit": {"passwords_audited": 1, "results": [None, {"password": "p"}]}},
        {"scan": {"ports_scanned": "many"}, "audit": {"results": [{}]}},
    ]
    for data in cases:
        json.loads(report.format_report_json(data))
        md = report.format_report_markdown(data)
        csv_text = report.format_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
