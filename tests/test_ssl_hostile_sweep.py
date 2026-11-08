"""Hostile-shape sweep for ssl report formatters."""

from __future__ import annotations

import json
from typing import Any, cast

from ethscan.ssl import (
    format_ssl_report_csv,
    format_ssl_report_json,
    format_ssl_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_ssl_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(format_ssl_report_json(cast(Any, bad_any)))
        md = format_ssl_report_markdown(cast(Any, bad_any))
        csv_text = format_ssl_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan SSL/TLS Certificate Report" in md


def test_ssl_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"target": 123, "host": None, "port": "x"},
        {"cert": "x"},
        {"cert": {"subject": 123, "issuer": [], "sans": "x", "key_size": "x"}},
        {"cert": {"sans": [None, 1, "ok"]}},
        {"error": [], "valid": "x", "chain_length": "x"},
    ]
    for data in cases:
        json.loads(format_ssl_report_json(data))
        md = format_ssl_report_markdown(data)
        csv_text = format_ssl_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan SSL/TLS Certificate Report" in md
