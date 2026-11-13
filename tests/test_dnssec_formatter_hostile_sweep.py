"""Permanent sweep test: hostile dnssec formatter inputs are rendered, never raised.

Covers ``format_dnssec_report_markdown``, ``format_dnssec_report_csv`` and
``format_dnssec_report_json`` against hostile top-level shapes and hostile
nested values. Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import json

import pytest

from ethscan.dnssec import (
    format_dnssec_report_csv,
    format_dnssec_report_json,
    format_dnssec_report_markdown,
)

DNSSEC_FORMATTERS: list[Callable[[Any], str]] = [
    format_dnssec_report_markdown,
    format_dnssec_report_csv,
    format_dnssec_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_NESTED: list[dict[str, object]] = [
    {},
    {"target": None, "domain": 1, "validated": "yes"},
    {"dnskey": None},
    {"dnskey": 1},
    {"dnskey": "x"},
    {"dnskey": []},
    {"dnskey": {"keys": None}},
    {"dnskey": {"keys": 1}},
    {"dnskey": {"keys": "x"}},
    {"dnskey": {"keys": [None, 1, "x", [], {"name": 1, "flags": [2]}]}},
    {"dnskey": {"success": None, "error": 1, "keys": []}},
    {"ds": None},
    {"ds": 1},
    {"ds": "x"},
    {"ds": {"records": None}},
    {"ds": {"records": 1}},
    {"ds": {"records": "x"}},
    {"ds": {"records": [None, 1, "x", [], {"key_tag": {"n": 1}}]}},
    {"ds": {"success": "no", "error": None, "records": []}},
    {"rrsig": None},
    {"rrsig": 1},
    {"rrsig": {"records": [None, 1, {"type_covered": 1}]}},
    {"chain": None},
    {"chain": 1},
    {"chain": "x"},
    {"chain": [None, 1, "x", [], {}]},
    {"chain": [{"zone": 1, "dnskey": None, "ds": None}]},
    {"chain": [{"zone": "example.com", "dnskey": 1, "ds": "x"}]},
    {"chain": [{"zone": "example.com", "dnskey": {"keys": [None, 1]}, "ds": {"records": [None]}}]},
    {"chain": [{"zone": "example.com", "dnskey": {"keys": "x"}, "ds": {"records": 1}}]},
    {"findings": None},
    {"findings": 1},
    {"findings": "x"},
    {"findings": [None, 1, "ok", {"k": "v"}, []]},
    {"notes": None},
    {"notes": 1},
    {"notes": "x"},
    {"notes": [None, 1, "note", {"k": "v"}]},
    {"nameservers": None},
    {"nameservers": 1},
    {"nameservers": [None, 1, "ns1.example.com"]},
    {"records": None},
    {"records": [None, 1, {"type": "DNSKEY"}]},
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "validated": True,
    "dnskey": {
        "success": True,
        "keys": [
            {
                "name": "example.com",
                "flags": 257,
                "protocol": 3,
                "algorithm": 13,
                "algorithm_name": "ECDSAP256SHA256",
                "key_tag": 12345,
            }
        ],
    },
    "ds": {
        "success": True,
        "records": [
            {
                "name": "example.com",
                "algorithm": 13,
                "algorithm_name": "ECDSAP256SHA256",
                "key_tag": 12345,
                "digest_type": 2,
                "digest_type_name": "SHA-256",
                "digest": "abc123",
            }
        ],
    },
    "chain": [
        {
            "zone": "example.com",
            "dnskey": {"success": True, "keys": [{"key_tag": 12345}]},
            "ds": {"success": True, "records": [{"key_tag": 12345}]},
        }
    ],
    "notes": ["DNSSEC validated"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", DNSSEC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_dnssec_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", DNSSEC_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("data", HOSTILE_NESTED)
def test_dnssec_formatters_tolerate_hostile_nested_shapes(
    formatter: Callable[[Any], str], data: dict[str, object]
) -> None:
    output = formatter(cast(Any, data))
    assert isinstance(output, str)
    if formatter is format_dnssec_report_json:
        json.loads(output)
    elif formatter is format_dnssec_report_markdown:
        assert "DNSSEC" in output
    else:
        assert "target,domain,validated" in output


@pytest.mark.parametrize("formatter", DNSSEC_FORMATTERS, ids=_formatter_id)
def test_dnssec_formatters_render_well_formed(formatter: Callable[[Any], str]) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_dnssec_report_markdown:
        assert "DNSSEC" in output
        assert "example.com" in output
        assert "12345" in output
    elif formatter is format_dnssec_report_csv:
        assert "target,domain,validated" in output
        assert "example.com" in output
        assert "dnskey" in output
    else:
        parsed = json.loads(output)
        assert parsed["domain"] == "example.com"
        assert parsed["validated"] is True
