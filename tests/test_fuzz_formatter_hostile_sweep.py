"""Permanent sweep test: hostile fuzz formatter inputs are rendered, never raised.

Covers ``format_fuzz_report_markdown``, ``format_fuzz_report_csv`` and
``format_fuzz_report_json`` against hostile top-level shapes and hostile
nested values. Every shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.fuzz import (
    format_fuzz_report_csv,
    format_fuzz_report_json,
    format_fuzz_report_markdown,
)

FUZZ_FORMATTERS: list[Callable[[Any], str]] = [
    format_fuzz_report_markdown,
    format_fuzz_report_csv,
    format_fuzz_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_NESTED: list[dict[str, object]] = [
    {},
    {"target": None, "base_url": 1, "paths_tested": "x"},
    {"target": [1, 2], "base_url": {"u": 1}},
    {"paths_tested": None},
    {"paths_tested": -1},
    {"paths_tested": [10]},
    {"findings": None},
    {"findings": 1},
    {"findings": "x"},
    {"findings": [None, 1, "x", [], {"path": 1, "status_code": "200"}]},
    {"all_results": None},
    {"all_results": 1},
    {"all_results": "x"},
    {"all_results": [None, 1, "x", []]},
    {"all_results": [{"path": None, "status_code": None, "error": 1}]},
    {"all_results": [{"path": ["/admin"], "status_code": "500", "error": [1]}]},
    {"findings": [None], "all_results": [None, {"path": "/a", "status_code": 200}]},
    {"target": "t", "base_url": "u", "paths_tested": 2, "findings": "no", "all_results": "no"},
]

WELL_FORMED = {
    "target": "http://example.test",
    "base_url": "http://example.test",
    "paths_tested": 4,
    "findings": [
        {"path": "/admin", "status_code": 200},
        {"path": "/login", "status_code": 302},
    ],
    "all_results": [
        {"path": "/", "status_code": 404, "error": None},
        {"path": "/admin", "status_code": 200, "error": None},
        {"path": "/login", "status_code": 302, "error": None},
        {"path": "/err", "status_code": None, "error": "timeout"},
    ],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", FUZZ_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_fuzz_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", FUZZ_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("data", HOSTILE_NESTED)
def test_fuzz_formatters_tolerate_hostile_nested_shapes(
    formatter: Callable[[Any], str], data: dict[str, object]
) -> None:
    output = formatter(cast(Any, data))
    assert isinstance(output, str)
    if formatter is format_fuzz_report_json:
        json.loads(output)
    elif formatter is format_fuzz_report_markdown:
        assert "HTTP Fuzz Report" in output
    else:
        assert "target,base_url,path,status_code,error,is_finding" in output


@pytest.mark.parametrize("formatter", FUZZ_FORMATTERS, ids=_formatter_id)
def test_fuzz_formatters_render_well_formed(formatter: Callable[[Any], str]) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    assert "example.test" in output
    if formatter is format_fuzz_report_markdown:
        assert "HTTP Fuzz Report" in output
        assert "/admin" in output
        assert "200" in output
    elif formatter is format_fuzz_report_csv:
        assert "target,base_url,path,status_code,error,is_finding" in output
        assert "finding_path,finding_status_code" in output
        assert "/admin" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "http://example.test"
        assert parsed["paths_tested"] == 4
        assert len(parsed["findings"]) == 2
