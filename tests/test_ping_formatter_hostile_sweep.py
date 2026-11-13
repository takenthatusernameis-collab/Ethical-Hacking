"""Permanent sweep test: hostile ping formatter inputs are rendered, never raised.

Covers ``format_ping_report_markdown``, ``format_ping_report_csv`` and
``format_ping_report_json`` against hostile top-level shapes and hostile
nested values. Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import json

import pytest

from ethscan.ping import (
    format_ping_report_csv,
    format_ping_report_json,
    format_ping_report_markdown,
)

PING_FORMATTERS: list[Callable[[Any], str]] = [
    format_ping_report_markdown,
    format_ping_report_csv,
    format_ping_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_NESTED: list[dict[str, object]] = [
    {},
    {"probes": None},
    {"probes": 1},
    {"probes": "x"},
    {"probes": []},
    {"probes": [None, 1, "x", [], {}]},
    {"probes": [{"sequence": 1, "rtt_ms": 5.0}, {"sequence": 2, "rtt_ms": None}]},
    {"probes": [{"sequence": "not-int", "ip": None, "response_type": 123}]},
    {"notes": None},
    {"notes": 1},
    {"notes": "x"},
    {"notes": []},
    {"notes": [None, 1, "note", {"k": "v"}]},
    {"target": None, "host": 1, "ip": "x", "count": "y"},
    {"raw_socket_available": "yes", "port": "eighty"},
    {"rtt_min_ms": "fast", "rtt_max_ms": "slow", "rtt_avg_ms": "medium"},
    {"probes": [{"sequence": 1}], "notes": ["ok"]},
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "ip": "93.184.216.34",
    "count": 4,
    "timeout": 2.0,
    "ttl": 64,
    "port": 80,
    "raw_socket_available": False,
    "probes": [
        {
            "ip": "93.184.216.34",
            "rtt_ms": 12.5,
            "ttl": 64,
            "sequence": 1,
            "response_type": "CONNECTED",
            "error": None,
        },
        {
            "ip": "93.184.216.34",
            "rtt_ms": 13.2,
            "ttl": 64,
            "sequence": 2,
            "response_type": "CONNECTED",
            "error": None,
        },
        {
            "ip": "93.184.216.34",
            "rtt_ms": 11.8,
            "ttl": 64,
            "sequence": 3,
            "response_type": "CONNECTED",
            "error": None,
        },
        {
            "ip": "93.184.216.34",
            "rtt_ms": 12.9,
            "ttl": 64,
            "sequence": 4,
            "response_type": "CONNECTED",
            "error": None,
        },
    ],
    "successful": 4,
    "failed": 0,
    "rtt_min_ms": 11.8,
    "rtt_max_ms": 13.2,
    "rtt_avg_ms": 12.6,
    "notes": ["4/4 probes successful", "Raw ICMP socket unavailable; running in TCP connect fallback mode on port 80 (ICMP ping not available)"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", PING_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_ping_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", PING_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("data", HOSTILE_NESTED)
def test_ping_formatters_tolerate_hostile_nested_shapes(
    formatter: Callable[[Any], str], data: dict[str, object]
) -> None:
    output = formatter(cast(Any, data))
    assert isinstance(output, str)
    if formatter is format_ping_report_json:
        json.loads(output)
    elif formatter is format_ping_report_markdown:
        assert "ethscan Ping Report" in output
    else:
        assert "target,ip,sequence,rtt_ms,ttl,response_type,error" in output


@pytest.mark.parametrize("formatter", PING_FORMATTERS, ids=_formatter_id)
def test_ping_formatters_render_well_formed(formatter: Callable[[Any], str]) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_ping_report_markdown:
        assert "ethscan Ping Report" in output
        assert "example.com" in output
        assert "93.184.216.34" in output
        assert "CONNECTED" in output
        assert "12.6" in output
    elif formatter is format_ping_report_csv:
        assert "target,ip,sequence,rtt_ms,ttl,response_type,error" in output
        assert "example.com" in output
        assert "CONNECTED" in output
    else:
        parsed = json.loads(output)
        assert parsed["host"] == "example.com"
        assert parsed["successful"] == 4
        assert parsed["rtt_avg_ms"] == 12.6