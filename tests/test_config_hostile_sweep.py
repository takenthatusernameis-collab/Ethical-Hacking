"""Hostile-shape sweep for config report formatter."""

from __future__ import annotations

from typing import Any, cast

import json

from ethscan import config

HOSTILE_TOP_LEVEL: tuple[object, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_config_json_never_raises_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(config.format_config_report_json(cast(Any, bad_any)))


def test_config_markdown_never_raises_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        md = config.format_config_report_markdown(cast(Any, bad_any))
        assert isinstance(md, str)
        assert "ethscan Configuration" in md


def test_config_csv_never_raises_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        csv_text = config.format_config_report_csv(cast(Any, bad_any))
        assert isinstance(csv_text, str)
        lines = csv_text.splitlines()
        assert lines and lines[0] == "section,option,value"


def test_config_json_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"defaults": "x"},
        {"defaults": [None, "x"]},
        {"defaults": {"timeout": 5}, "commands": "x"},
        {"commands": {"scan": "x"}},
        {"commands": {"scan": {"ports": [1, 2]}}},
        {"_path": 123, "_parse_error": b"boom"},
    ]
    for data in cases:
        json.loads(config.format_config_report_json(data))


def test_config_markdown_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"defaults": "x"},
        {"defaults": [None, "x"]},
        {"defaults": {"timeout": 5}, "commands": "x"},
        {"commands": {"scan": "x"}},
        {"commands": {"scan": {"ports": [1, 2]}}},
        {"_path": 123, "_parse_error": b"boom"},
    ]
    for data in cases:
        md = config.format_config_report_markdown(data)
        assert isinstance(md, str)
        assert "ethscan Configuration" in md


def test_config_csv_hostile_nested_shapes_never_raise() -> None:
    cases: list[dict[str, object]] = [
        {"defaults": "x"},
        {"defaults": [None, "x"]},
        {"defaults": {"timeout": 5}, "commands": "x"},
        {"commands": {"scan": "x"}},
        {"commands": {"scan": {"ports": [1, 2]}}},
        {"_path": 123, "_parse_error": b"boom"},
    ]
    for data in cases:
        csv_text = config.format_config_report_csv(data)
        assert isinstance(csv_text, str)
        lines = csv_text.splitlines()
        assert lines and lines[0] == "section,option,value"


def test_config_json_with_warnings() -> None:
    data = {"defaults": {"timeout": 5.0}, "commands": {"scan": {"ports": "common"}}}
    result = config.format_config_report_json(data, warnings=["warning 1", "warning 2"])
    parsed = json.loads(result)
    assert parsed["warnings"] == ["warning 1", "warning 2"]


def test_config_markdown_with_warnings() -> None:
    data = {"defaults": {"timeout": 5.0}, "commands": {"scan": {"ports": "common"}}}
    md = config.format_config_report_markdown(data, warnings=["warning 1", "warning 2"])
    assert "Warnings" in md
    assert "warning 1" in md
    assert "warning 2" in md
