"""Hostile-shape sweep for completion report formatters."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import completion

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_completion_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(completion.format_completion_report_json(cast(Any, bad_any)))
        md = completion.format_completion_report_markdown(cast(Any, bad_any))
        csv_text = completion.format_completion_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Shell Completion" in md


def test_completion_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"shell": "bash", "prog_name": "ethscan", "script": 123},
        {"shell": None, "script": None},
        {"script": ["not", "a", "string"]},
        {},
    ]
    for data in cases:
        json.loads(completion.format_completion_report_json(data))
        md = completion.format_completion_report_markdown(data)
        csv_text = completion.format_completion_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Shell Completion" in md
