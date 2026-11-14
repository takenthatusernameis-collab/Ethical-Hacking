"""Permanent sweep test: hostile dnsbrute formatter inputs are rendered, never raised.

Covers ``format_dnsbrute_report_markdown``, ``format_dnsbrute_report_csv`` and
``format_dnsbrute_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``axfr``, ``recursive_axfr``, ``resolved``,
``all_results`` and their nested structures). Every shape yields a string and
never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.dnsbrute import (
    format_dnsbrute_report_csv,
    format_dnsbrute_report_json,
    format_dnsbrute_report_markdown,
)

DNS_BRUTE_FORMATTERS: list[Callable[[Any], str]] = [
    format_dnsbrute_report_markdown,
    format_dnsbrute_report_csv,
    format_dnsbrute_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", None),
    ("target", 1),
    ("target", []),
    ("domain", None),
    ("domain", 1),
    ("zone", None),
    ("nameservers", "x"),
    ("nameservers", None),
    ("nameservers", [None, 1, {}]),
    ("nameserver_source", None),
    ("dnspython_available", "yes"),
    ("axfr", "x"),
    ("axfr", None),
    ("axfr", [None, 1, {}]),
    ("recursive_axfr", "x"),
    ("recursive_axfr", None),
    ("resolved", "x"),
    ("resolved", None),
    ("resolved", [None, 1, {}]),
    ("all_results", "x"),
    ("all_results", None),
    ("all_results", [None, 1, {}]),
    ("axfr_success", None),
    ("axfr_total_records", "x"),
    ("subdomains_tested", "x"),
    ("resolved_count", "x"),
    ("recursive", "x"),
    ("max_depth", "x"),
]

HOSTILE_AXFR: list[object] = [
    None,
    1,
    "x",
    {
        "nameserver": None,
        "success": "x",
        "records_count": {},
        "records": "x",
        "error": 1,
        "zone": 1,
        "depth": "x",
    },
    {"nameserver": "ns", "records": [None, 1, 2.5, ["nested"], {"a": 1}]},
    {"nameserver": "ns", "success": True, "records": True},
]

HOSTILE_RESOLVED: list[object] = [
    None,
    1,
    "x",
    [None, "x", 1, {"subdomain": "a", "hostname": [], "a": {}, "aaaa": "scalar"}],
]

HOSTILE_ALL_RESULTS: list[object] = [
    None,
    1,
    "x",
    [None, "x", 1, {"subdomain": "a", "hostname": "a.x", "a": 1.5, "aaaa": b"bytes"}],
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "zone": "example.com",
    "nameservers": ["ns1.example.com"],
    "nameserver_source": "option",
    "dnspython_available": False,
    "axfr": [
        {
            "nameserver": "ns1.example.com",
            "success": False,
            "records_count": 0,
            "records": [],
            "error": "transfer refused (REFUSED)",
        }
    ],
    "axfr_success": False,
    "axfr_total_records": 0,
    "subdomains_tested": 2,
    "resolved_count": 1,
    "resolved": [
        {"subdomain": "www", "hostname": "www.example.com", "a": ["1.2.3.4"], "aaaa": []}
    ],
    "all_results": [
        {"subdomain": "www", "hostname": "www.example.com", "a": ["1.2.3.4"], "aaaa": []},
        {"subdomain": "mail", "hostname": "mail.example.com", "a": [], "aaaa": []},
    ],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_dnsbrute_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_dnsbrute_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("axfr", HOSTILE_AXFR)
def test_dnsbrute_formatters_tolerate_hostile_axfr(
    formatter: Callable[[Any], str], axfr: object
) -> None:
    output = formatter({"target": "example.com", "axfr": axfr})
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("resolved", HOSTILE_RESOLVED)
def test_dnsbrute_formatters_tolerate_hostile_resolved(
    formatter: Callable[[Any], str], resolved: object
) -> None:
    output = formatter({"target": "example.com", "resolved": resolved})
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("all_results", HOSTILE_ALL_RESULTS)
def test_dnsbrute_formatters_tolerate_hostile_all_results(
    formatter: Callable[[Any], str], all_results: object
) -> None:
    output = formatter({"target": "example.com", "all_results": all_results})
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
def test_dnsbrute_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": None,
            "domain": 1,
            "zone": [],
            "nameservers": "x",
            "axfr": [None, 1, {"nameserver": None, "records": "scalar"}],
            "resolved": [None, 1, {"subdomain": "a", "hostname": [], "a": {}, "aaaa": True}],
            "all_results": [None, {"subdomain": "a", "hostname": "a.x", "a": 1.5, "aaaa": []}],
            "recursive_axfr": [None, {}],
        }
    )
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", DNS_BRUTE_FORMATTERS, ids=_formatter_id)
def test_dnsbrute_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_dnsbrute_report_markdown:
        assert "# ethscan DNS Brute Force Report" in output
        assert "**Target:** example.com" in output
        assert "**Zone:** example.com" in output
        assert "ns1.example.com" in output
        assert "**AXFR Successful:** No" in output
        assert "**Subdomains Tested:** 2" in output
        assert "**Resolved:** 1" in output
        assert "## AXFR Attempts" in output
        assert "transfer refused (REFUSED)" in output
        assert "## Resolved Subdomains" in output
        assert "## All Results" in output
        assert "1.2.3.4" in output
    elif formatter is format_dnsbrute_report_csv:
        assert "example.com" in output
        assert "subdomain" in output
        assert "axfr" in output
        assert "ns1.example.com" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["zone"] == "example.com"
        assert parsed["axfr_success"] is False
        assert parsed["subdomains_tested"] == 2
        assert parsed["resolved"][0]["hostname"] == "www.example.com"
        assert parsed["all_results"][1]["subdomain"] == "mail"
