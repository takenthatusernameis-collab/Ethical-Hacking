"""Permanent sweep test: hostile service formatter inputs are rendered, never raised.

Covers ``format_service_report_json``, ``format_service_report_markdown`` and
``format_service_report_csv`` against hostile top-level shapes and hostile
nested values in the key report section (``results``). Every shape yields a
string and never raises, and the JSON formatter always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.service import (
    format_service_report_csv,
    format_service_report_json,
    format_service_report_markdown,
)

SERVICE_FORMATTERS: list[Callable[[Any], str]] = [
    format_service_report_json,
    format_service_report_markdown,
    format_service_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", "x"),
    ("target", None),
    ("target", []),
    ("target", {}),
    ("target", 1),
    ("host", "x"),
    ("host", None),
    ("host", []),
    ("host", {}),
    ("host", 1),
    ("ports_scanned", "x"),
    ("ports_scanned", None),
    ("ports_scanned", []),
    ("ports_scanned", {}),
    ("ports_scanned", 1.5),
    ("services_found", "x"),
    ("services_found", None),
    ("services_found", []),
    ("services_found", {}),
    ("services_found", 1.5),
    ("results", "x"),
    ("results", None),
    ("results", {}),
    ("results", 1),
    ("results", 1.5),
]

HOSTILE_RESULTS_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"port": None},
    {"port": 1},
    {"port": []},
    {"port": "x"},
    {"service": None},
    {"service": 1},
    {"service": []},
    {"banner": None},
    {"banner": 1},
    {"banner": []},
    {"banner": {}},
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
    "target": "example.com",
    "host": "192.168.1.1",
    "ports_scanned": 24,
    "services_found": 2,
    "results": [
        {"port": 22, "service": "ssh", "banner": "SSH-2.0-OpenSSH_8.2"},
        {"port": 80, "service": "http", "banner": "HTTP/1.1 200 OK"},
    ],
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "host": "192.168.1.1",
    "ports_scanned": 0,
    "services_found": 0,
    "results": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_service_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_service_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_service_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_service_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_RESULTS_ENTRY)
def test_service_formatters_tolerate_hostile_results_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"results": entry})
    assert isinstance(output, str)
    if formatter is format_service_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_service_formatters_tolerate_hostile_results_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"results": lst})
    assert isinstance(output, str)
    if formatter is format_service_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
def test_service_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": "x",
            "host": None,
            "ports_scanned": "many",
            "services_found": "lots",
            "results": [
                None,
                {"port": [], "service": {}},
                "not-a-dict",
                1,
                {"port": 22, "banner": {}},
            ],
        }
    )
    assert isinstance(output, str)
    if formatter is format_service_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
def test_service_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_service_report_markdown:
        assert "# ethscan Service Detection Report" in output
        assert "**Target:** example.com" in output
        assert "**Host:** 192.168.1.1" in output
        assert "**Ports Scanned:** 24" in output
        assert "**Services Found:** 2" in output
        assert "## Detected Services" in output
        assert "| Port | Service | Banner |" in output
        assert "| 22 | ssh | SSH-2.0-OpenSSH_8.2 |" in output
        assert "| 80 | http | HTTP/1.1 200 OK |" in output
    elif formatter is format_service_report_csv:
        assert "port,service,banner" in output
        assert "22,ssh,SSH-2.0-OpenSSH_8.2" in output
        assert "80,http,HTTP/1.1 200 OK" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "192.168.1.1"
        assert parsed["ports_scanned"] == 24
        assert parsed["services_found"] == 2
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["port"] == 22
        assert parsed["results"][0]["service"] == "ssh"
        assert parsed["results"][0]["banner"] == "SSH-2.0-OpenSSH_8.2"
        assert parsed["results"][1]["port"] == 80


@pytest.mark.parametrize("formatter", SERVICE_FORMATTERS, ids=_formatter_id)
def test_service_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_service_report_markdown:
        assert "# ethscan Service Detection Report" in output
        assert "**Target:** example.com" in output
        assert "**Host:** 192.168.1.1" in output
        assert "**Ports Scanned:** 0" in output
        assert "**Services Found:** 0" in output
        assert "*No services detected.*" in output
    elif formatter is format_service_report_csv:
        assert "port,service,banner" in output
        lines = output.strip().split("\n")
        assert len(lines) == 1
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "192.168.1.1"
        assert parsed["ports_scanned"] == 0
        assert parsed["services_found"] == 0
        assert parsed["results"] == []
