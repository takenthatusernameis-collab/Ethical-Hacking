"""Permanent sweep test: hostile subtake formatter inputs are rendered, never raised.

Covers ``format_subtake_report_json``, ``format_subtake_report_markdown`` and
``format_subtake_report_csv`` against hostile top-level shapes and hostile
nested values in the key report sections (``vulnerable`` and ``all_results``).
Every shape yields a string and never raises, and the JSON formatter always
emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.subtake import (
    format_subtake_report_csv,
    format_subtake_report_json,
    format_subtake_report_markdown,
)

SUBTAKE_FORMATTERS: list[Callable[[Any], str]] = [
    format_subtake_report_json,
    format_subtake_report_markdown,
    format_subtake_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", "x"),
    ("target", None),
    ("target", []),
    ("target", {}),
    ("target", 1),
    ("domain", "x"),
    ("domain", None),
    ("domain", []),
    ("domain", {}),
    ("domain", 1),
    ("subdomains_tested", "x"),
    ("subdomains_tested", None),
    ("subdomains_tested", []),
    ("subdomains_tested", {}),
    ("subdomains_tested", 1.5),
    ("vulnerable_count", "x"),
    ("vulnerable_count", None),
    ("vulnerable_count", []),
    ("vulnerable_count", {}),
    ("vulnerable_count", 1.5),
    ("vulnerable", "x"),
    ("vulnerable", None),
    ("vulnerable", {}),
    ("vulnerable", 1),
    ("vulnerable", 1.5),
    ("all_results", "x"),
    ("all_results", None),
    ("all_results", {}),
    ("all_results", 1),
    ("all_results", 1.5),
    ("resolver", "x"),
    ("resolver", None),
    ("resolver", []),
    ("resolver", {}),
    ("resolver", 1),
    ("dnspython_available", "x"),
    ("dnspython_available", None),
    ("dnspython_available", []),
    ("dnspython_available", {}),
    ("dnspython_available", 1),
]

HOSTILE_VULNERABLE_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"takeover": None},
    {"takeover": []},
    {"takeover": {}},
    {"takeover": {"service": None}},
    {"takeover": {"service": 1}},
    {"takeover": {"service": []}},
    {"takeover": {"cname": None}},
    {"takeover": {"cname": []}},
    {"takeover": {"cname": {}}},
    {"takeover": {"fingerprint": None}},
    {"takeover": {"fingerprint": []}},
    {"takeover": {"fingerprint": {}}},
    {"takeover": {"http_confirmed": None}},
    {"takeover": {"http_confirmed": []}},
    {"subdomain": []},
    {"subdomain": {}},
    {"hostname": []},
    {"hostname": {}},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_ALL_RESULTS_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"subdomain": []},
    {"subdomain": {}},
    {"hostname": []},
    {"hostname": {}},
    {"cname": []},
    {"cname": {}},
    {"cname": None},
    {"a_records": None},
    {"a_records": "x"},
    {"a_records": {}},
    {"a_records": [None, 1, {}, "not-a-string", []]},
    {"a_records": [[1, 2], {"x": 1}]},
    {"aaaa_records": None},
    {"aaaa_records": "x"},
    {"aaaa_records": {}},
    {"aaaa_records": [None, 1, {}, []]},
    {"vulnerable": []},
    {"vulnerable": {}},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-dict", []],
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "subdomains_tested": 2,
    "vulnerable_count": 1,
    "resolver": "1.1.1.1",
    "dnspython_available": True,
    "vulnerable": [
        {
            "subdomain": "a",
            "hostname": "a.example.com",
            "cname": "a.s3.amazonaws.com",
            "a_records": ["1.2.3.4"],
            "aaaa_records": [],
            "vulnerable": True,
            "takeover": {
                "service": "S3",
                "cname": "a.s3.amazonaws.com",
                "fingerprint": "fp",
                "http_confirmed": True,
            },
        }
    ],
    "all_results": [
        {
            "subdomain": "a",
            "hostname": "a.example.com",
            "cname": "a.s3.amazonaws.com",
            "a_records": ["1.2.3.4"],
            "aaaa_records": [],
            "vulnerable": True,
            "takeover": {
                "service": "S3",
                "cname": "a.s3.amazonaws.com",
                "fingerprint": "fp",
                "http_confirmed": True,
            },
        },
        {
            "subdomain": "b",
            "hostname": "b.example.com",
            "cname": None,
            "a_records": [],
            "aaaa_records": [],
            "vulnerable": False,
            "takeover": None,
        },
    ],
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "domain": "example.com",
    "subdomains_tested": 0,
    "vulnerable_count": 0,
    "resolver": None,
    "dnspython_available": False,
    "vulnerable": [],
    "all_results": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_subtake_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_subtake_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_VULNERABLE_ENTRY)
def test_subtake_formatters_tolerate_hostile_vulnerable_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"vulnerable": [entry]})
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_ALL_RESULTS_ENTRY)
def test_subtake_formatters_tolerate_hostile_all_results_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"all_results": [entry]})
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_subtake_formatters_tolerate_hostile_vulnerable_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"vulnerable": lst})
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_subtake_formatters_tolerate_hostile_all_results_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"all_results": lst})
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
def test_subtake_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": "x",
            "domain": None,
            "subdomains_tested": "many",
            "vulnerable_count": [],
            "resolver": {},
            "dnspython_available": [],
            "vulnerable": [
                None,
                {"takeover": []},
                {"takeover": {"service": None, "cname": [], "fingerprint": {}}},
                1,
                "x",
            ],
            "all_results": [
                None,
                {"a_records": {}, "aaaa_records": [None, {"x": 1}]},
                1,
                "x",
                {"cname": {}, "subdomain": []},
            ],
        }
    )
    assert isinstance(output, str)
    if formatter is format_subtake_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
def test_subtake_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_subtake_report_markdown:
        assert "# ethscan Subdomain Takeover Report" in output
        assert "**Target:** example.com" in output
        assert "**Domain:** example.com" in output
        assert "**Resolver:** 1.1.1.1 (dnspython: Yes)" in output
        assert "**Subdomains Tested:** 2" in output
        assert "**Vulnerable:** 1" in output
        assert "## Vulnerable Subdomains (Potential Takeover)" in output
        assert "| Subdomain | Hostname | CNAME | Service | Fingerprint | HTTP Confirmed |" in output
        assert "| a | a.example.com | a.s3.amazonaws.com | S3 | fp | Yes |" in output
        assert "## All Results" in output
        assert "| Subdomain | Hostname | CNAME | A Records | AAAA Records | Vulnerable |" in output
        assert "| a | a.example.com | a.s3.amazonaws.com | 1.2.3.4 | N/A | Yes |" in output
        assert "| b | b.example.com | N/A | N/A | N/A | No |" in output
    elif formatter is format_subtake_report_csv:
        assert (
            "subdomain,hostname,cname,a_records,aaaa_records,vulnerable,service,"
            "fingerprint,http_confirmed" in output
        )
        assert "a,a.example.com,a.s3.amazonaws.com,1.2.3.4,,true,S3,fp,true" in output
        assert "b,b.example.com,,,,false,,,false" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["domain"] == "example.com"
        assert parsed["subdomains_tested"] == 2
        assert parsed["vulnerable_count"] == 1
        assert parsed["resolver"] == "1.1.1.1"
        assert parsed["dnspython_available"] is True
        assert len(parsed["vulnerable"]) == 1
        assert parsed["vulnerable"][0]["subdomain"] == "a"
        assert parsed["vulnerable"][0]["takeover"]["service"] == "S3"
        assert len(parsed["all_results"]) == 2
        assert parsed["all_results"][0]["a_records"] == ["1.2.3.4"]
        assert parsed["all_results"][1]["subdomain"] == "b"


@pytest.mark.parametrize("formatter", SUBTAKE_FORMATTERS, ids=_formatter_id)
def test_subtake_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_subtake_report_markdown:
        assert "# ethscan Subdomain Takeover Report" in output
        assert "**Target:** example.com" in output
        assert "**Domain:** example.com" in output
        assert "**Subdomains Tested:** 0" in output
        assert "**Vulnerable:** 0" in output
        assert "*No vulnerable subdomains detected.*" in output
    elif formatter is format_subtake_report_csv:
        assert (
            "subdomain,hostname,cname,a_records,aaaa_records,vulnerable,service,"
            "fingerprint,http_confirmed" in output
        )
        lines = output.strip().split("\n")
        assert len(lines) == 1
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["domain"] == "example.com"
        assert parsed["subdomains_tested"] == 0
        assert parsed["vulnerable_count"] == 0
        assert parsed["resolver"] is None
        assert parsed["dnspython_available"] is False
        assert parsed["vulnerable"] == []
        assert parsed["all_results"] == []