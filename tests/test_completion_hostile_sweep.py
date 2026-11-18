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


# Fields read by the installation report formatters. ``message`` is the only
# one joined raw into the Markdown output (the others are f-string
# interpolated), so a hostile ``message`` used to raise TypeError from
# ``"\n".join(...)``.
INSTALL_REPORT_FIELDS: tuple[str, ...] = (
    "shell",
    "script_path",
    "rc_file",
    "installed",
    "already_installed",
    "message",
)

INSTALL_HOSTILE_VALUES: tuple[object, ...] = (
    None,
    1,
    1.5,
    True,
    "text",
    b"bytes",
    [],
    [None, 1],
    {},
    {"k": "v"},
)


def test_install_report_formatters_never_raise_on_hostile_fields() -> None:
    for field in INSTALL_REPORT_FIELDS:
        for bad in INSTALL_HOSTILE_VALUES:
            bad_any: Any = bad
            data: dict[str, object] = {field: bad_any}
            json.loads(completion.format_install_report_json(data))
            md = completion.format_install_report_markdown(data)
            csv_text = completion.format_install_report_csv(data)
            assert isinstance(md, str), f"{field}={bad!r} markdown not str"
            assert isinstance(csv_text, str), f"{field}={bad!r} csv not str"
            assert "ethscan Completion Installation" in md


def test_install_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        bad_any: Any = bad
        json.loads(completion.format_install_report_json(cast(Any, bad_any)))
        md = completion.format_install_report_markdown(cast(Any, bad_any))
        csv_text = completion.format_install_report_csv(cast(Any, bad_any))
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "ethscan Completion Installation" in md
