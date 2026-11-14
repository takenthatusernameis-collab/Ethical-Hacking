"""Permanent sweep test: hostile brute formatter inputs are rendered, never raised.

Covers ``format_brute_report_markdown``, ``format_brute_report_csv`` and
``format_brute_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``successful``, ``results``).
Every shape yields a string and never raises, and the JSON formatter always
emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.brute import (
    format_brute_report_csv,
    format_brute_report_json,
    format_brute_report_markdown,
)

BRUTE_FORMATTERS: list[Callable[[Any], str]] = [
    format_brute_report_markdown,
    format_brute_report_csv,
    format_brute_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", "x"),
    ("target", None),
    ("target", []),
    ("host", "x"),
    ("host", None),
    ("host", []),
    ("protocol", "x"),
    ("protocol", None),
    ("protocol", []),
    ("protocol", 1),
    ("protocol", {}),
    ("port", "x"),
    ("port", None),
    ("port", []),
    ("port", 1.5),
    ("port", {}),
    ("timeout", "x"),
    ("timeout", None),
    ("timeout", []),
    ("usernames_tested", "x"),
    ("usernames_tested", None),
    ("usernames_tested", []),
    ("passwords_tested", "x"),
    ("passwords_tested", None),
    ("passwords_tested", []),
    ("attempts", "x"),
    ("attempts", None),
    ("attempts", []),
    ("successful_count", "x"),
    ("successful_count", None),
    ("successful_count", []),
    ("successful", "x"),
    ("successful", None),
    ("successful", {}),
    ("successful", 1),
    ("results", "x"),
    ("results", None),
    ("results", {}),
    ("results", 1),
]

HOSTILE_RESULT_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"username": None},
    {"username": 1},
    {"username": []},
    {"password": None},
    {"password": 1},
    {"password": []},
    {"success": "x"},
    {"success": None},
    {"success": []},
    {"error": 1},
    {"error": []},
    {"error": {}},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-string", []],
]

WELL_FORMED = {
    "target": "ftp.example.com",
    "host": "ftp.example.com",
    "protocol": "ftp",
    "port": 21,
    "timeout": 5.0,
    "usernames_tested": 1,
    "passwords_tested": 2,
    "attempts": 2,
    "successful_count": 1,
    "successful": [
        {
            "username": "admin",
            "password": "secret",
            "success": True,
            "error": None,
        }
    ],
    "results": [
        {
            "username": "admin",
            "password": "secret",
            "success": True,
            "error": None,
        },
        {
            "username": "admin",
            "password": "wrong",
            "success": False,
            "error": "530 Login incorrect",
        },
    ],
}

WELL_FORMED_MINIMAL = {
    "target": "ftp.example.com",
    "host": "ftp.example.com",
    "protocol": "ftp",
    "port": 21,
    "timeout": 5.0,
    "usernames_tested": 0,
    "passwords_tested": 0,
    "attempts": 0,
    "successful_count": 0,
    "successful": [],
    "results": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_brute_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_brute_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("results", HOSTILE_RESULT_ENTRY)
def test_brute_formatters_tolerate_hostile_results(
    formatter: Callable[[Any], str], results: object
) -> None:
    output = formatter({"results": results})
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["successful", "results"])
@pytest.mark.parametrize("entry", HOSTILE_RESULT_ENTRY)
def test_brute_formatters_tolerate_hostile_entry_lists(
    formatter: Callable[[Any], str], field: str, entry: object
) -> None:
    output = formatter({field: entry})
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["successful", "results"])
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_brute_formatters_tolerate_hostile_simple_lists(
    formatter: Callable[[Any], str], field: str, lst: object
) -> None:
    output = formatter({field: lst})
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
def test_brute_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": "x",
            "host": None,
            "protocol": [],
            "port": "x",
            "timeout": {},
            "usernames_tested": 1,
            "passwords_tested": [],
            "attempts": "many",
            "successful_count": "x",
            "successful": [
                None,
                {"username": [], "password": 1, "success": {}, "error": "bad"},
                "bad",
                1,
            ],
            "results": [
                {"username": None, "password": [], "success": "yes", "error": 123},
                "not-a-dict",
                None,
                1,
            ],
        }
    )
    assert isinstance(output, str)
    if formatter is format_brute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
def test_brute_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_brute_report_markdown:
        assert "# ethscan Brute Force Report" in output
        assert "**Target:** ftp.example.com" in output
        assert "**Host:** ftp.example.com" in output
        assert "**Protocol:** ftp" in output
        assert "**Port:** 21" in output
        assert "**Attempts:** 2" in output
        assert "**Successful Logins:** 1" in output
        assert "## Successful Logins" in output
        assert "| admin | secret |" in output
        assert "## All Attempts" in output
        assert "| admin | secret | Yes |  |" in output
        assert "| admin | wrong | No | 530 Login incorrect |" in output
    elif formatter is format_brute_report_csv:
        assert "username,password,success,error" in output
        assert "admin,secret,true," in output
        assert "admin,wrong,false,530 Login incorrect" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "ftp.example.com"
        assert parsed["host"] == "ftp.example.com"
        assert parsed["protocol"] == "ftp"
        assert parsed["port"] == 21
        assert parsed["attempts"] == 2
        assert parsed["successful_count"] == 1
        assert len(parsed["successful"]) == 1
        assert parsed["successful"][0]["username"] == "admin"
        assert len(parsed["results"]) == 2
        assert parsed["results"][1]["error"] == "530 Login incorrect"


@pytest.mark.parametrize("formatter", BRUTE_FORMATTERS, ids=_formatter_id)
def test_brute_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_brute_report_markdown:
        assert "# ethscan Brute Force Report" in output
        assert "**Attempts:** 0" in output
        assert "**Successful Logins:** 0" in output
        assert "## Successful Logins" in output
        assert "*No successful logins.*" in output
        assert "## All Attempts" in output
        assert "| Username | Password | Success | Error |" in output
    elif formatter is format_brute_report_csv:
        assert "username,password,success,error" in output
        lines = output.strip().split("\n")
        assert len(lines) == 1
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "ftp.example.com"
        assert parsed["attempts"] == 0
        assert parsed["successful_count"] == 0
        assert parsed["successful"] == []
        assert parsed["results"] == []
