"""Permanent sweep test: hostile urlcheck formatter inputs are rendered, never raised.

Covers ``format_urlcheck_report_markdown``, ``format_urlcheck_report_csv`` and
``format_urlcheck_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``summary``, ``web``, ``fuzz``,
``ssl`` and their nested structures). Every shape yields a string and never
raises, and the JSON formatter always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.urlcheck import (
    format_urlcheck_report_csv,
    format_urlcheck_report_json,
    format_urlcheck_report_markdown,
)

URLCHECK_FORMATTERS: list[Callable[[Any], str]] = [
    format_urlcheck_report_markdown,
    format_urlcheck_report_csv,
    format_urlcheck_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", None),
    ("target", 1),
    ("target", []),
    ("normalized_target", None),
    ("normalized_target", 1),
    ("normalized_target", []),
    ("port", "x"),
    ("port", []),
    ("timeout", "x"),
    ("timeout", {}),
    ("workers", "x"),
    ("workers", []),
    ("checks_requested", "x"),
    ("checks_requested", [None, 1, {}]),
    ("fuzz_enabled", "yes"),
    ("summary", "x"),
    ("summary", None),
    ("summary", [None, 1, {}]),
    ("web", "x"),
    ("web", None),
    ("web", [None, 1, {}]),
    ("fuzz", "x"),
    ("fuzz", None),
    ("fuzz", [None, 1, {}]),
    ("ssl", "x"),
    ("ssl", None),
    ("ssl", [None, 1, {}]),
]

HOSTILE_SUMMARY: list[object] = [
    None,
    1,
    "x",
    {"total_findings": None},
    {"total_findings": "x"},
    {"web_checks_run": "x"},
    {"web_checks_run": [None, 1, {}]},
    {"web_checks_run": {"a": 1}},
    {"fuzz_enabled": "yes"},
    {"ssl_checked": 1},
]

HOSTILE_WEB: list[object] = [
    None,
    1,
    "x",
    {"host": None},
    {"host": []},
    {"port": []},
    {"secure": "x"},
    {"error": 1},
    {"error": "e"},
    {"security_headers": "x"},
    {"security_headers": {"present": "x"}},
    {"security_headers": {"missing": "x"}},
    {"security_headers": {"present": [None, 1, {}]}},
    {"security_headers": {"missing": [None, 1, {}]}},
    {"security_headers": {"present_count": [], "total": {}}},
    {"information_disclosure": "x"},
    {"information_disclosure": [None, 1, {"header": []}]},
    {"information_disclosure": [{"header": [], "value": {}, "description": 1}]},
    {"ssl": "x"},
    {"ssl": {"valid": "x"}},
    {"ssl": {"subject": []}},
    {"ssl": {"error": 1}},
    {"ssl": {"not_after": []}},
    {"ssl": {"days_remaining": {}}},
]

HOSTILE_FUZZ: list[object] = [
    None,
    1,
    "x",
    {"base_url": None},
    {"base_url": []},
    {"paths_tested": []},
    {"findings": "x"},
    {"findings": [None, 1, {"path": []}]},
    {"findings": [{"path": [], "status_code": {}}]},
    {"all_results": "x"},
    {"all_results": [None, 1, {"path": [], "status_code": [], "error": {}}]},
]

HOSTILE_SSL: list[object] = [
    None,
    1,
    "x",
    {"host": None},
    {"host": []},
    {"port": []},
    {"error": 1},
    {"error": "e"},
    {"cert": "x"},
    {"cert": None},
    {"cert": []},
    {"cert": {"subject": []}},
    {"cert": {"sans": "x"}},
    {"cert": {"sans": [None, 1, {}]}},
    {"chain_length": "x"},
    {"valid": "x"},
    {"cert": {"key_size": []}},
    {"cert": {"signature_algorithm": []}},
]

WELL_FORMED = {
    "target": "example.com",
    "normalized_target": "https://example.com",
    "checks_requested": ["headers", "ssl"],
    "fuzz_enabled": True,
    "port": 443,
    "timeout": 5.0,
    "workers": 10,
    "summary": {
        "total_findings": 1,
        "web_checks_run": ["headers", "ssl"],
        "fuzz_enabled": True,
        "ssl_checked": True,
    },
    "web": {
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": ["Content-Security-Policy"],
            "missing": ["X-Frame-Options"],
            "total": 7,
            "present_count": 1,
            "missing_count": 6,
        },
        "information_disclosure": [
            {"header": "Server", "value": "nginx", "description": "Server banner"}
        ],
        "ssl": {"valid": True, "subject": "example.com", "issuer": "Let's Encrypt"},
    },
    "fuzz": {
        "base_url": "https://example.com",
        "paths_tested": 2,
        "findings": [{"path": "/admin", "status_code": 200, "error": None}],
        "all_results": [
            {"path": "/admin", "status_code": 200, "error": None},
            {"path": "/login", "status_code": 404, "error": None},
        ],
    },
    "ssl": {
        "host": "example.com",
        "port": 443,
        "error": None,
        "chain_length": 2,
        "cert": {
            "subject": "example.com",
            "issuer": "Let's Encrypt",
            "sans": ["example.com"],
            "not_before": "Jan  1 00:00:00 2020 GMT",
            "not_after": "Jan  1 00:00:00 2027 GMT",
            "signature_algorithm": "sha256WithRSAEncryption",
            "key_size": 2048,
        },
    },
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "summary": {"total_findings": 0, "web_checks_run": [], "fuzz_enabled": False},
    "web": None,
    "fuzz": None,
    "ssl": None,
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_urlcheck_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_urlcheck_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("summary", HOSTILE_SUMMARY)
def test_urlcheck_formatters_tolerate_hostile_summary(
    formatter: Callable[[Any], str], summary: object
) -> None:
    output = formatter({"target": "example.com", "summary": summary})
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("web", HOSTILE_WEB)
def test_urlcheck_formatters_tolerate_hostile_web(
    formatter: Callable[[Any], str], web: object
) -> None:
    output = formatter({"target": "example.com", "web": web})
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("fuzz", HOSTILE_FUZZ)
def test_urlcheck_formatters_tolerate_hostile_fuzz(
    formatter: Callable[[Any], str], fuzz: object
) -> None:
    output = formatter({"target": "example.com", "fuzz": fuzz})
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ssl", HOSTILE_SSL)
def test_urlcheck_formatters_tolerate_hostile_ssl(
    formatter: Callable[[Any], str], ssl: object
) -> None:
    output = formatter({"target": "example.com", "ssl": ssl})
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
def test_urlcheck_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": None,
            "normalized_target": 1,
            "port": [],
            "timeout": {},
            "workers": "x",
            "summary": {"total_findings": "x", "web_checks_run": [None, 1, {}]},
            "web": {
                "host": [],
                "security_headers": {"present": "x", "missing": [None]},
                "information_disclosure": [None, {"header": []}],
            },
            "fuzz": {
                "findings": [None, {"path": []}],
                "all_results": [None, {"path": [], "status_code": []}],
            },
            "ssl": {"cert": {"sans": [None], "key_size": []}, "chain_length": "x"},
        }
    )
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
def test_urlcheck_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_markdown:
        assert "# ethscan Consolidated Web Assessment Report" in output
        assert "**Target:** example.com" in output
        assert "**Normalized Target:** https://example.com" in output
        assert "**Port:** 443" in output
        assert "**Total Findings:** 1" in output
        assert "**Web Checks Run:** headers, ssl" in output
        assert "**Fuzzing Enabled:** Yes" in output
        assert "**SSL Checked:** Yes" in output
        assert "## Web Security Checks" in output
        assert "Content-Security-Policy" in output
        assert "X-Frame-Options" in output
        assert "### Information Disclosure" in output
        assert "Server banner" in output
        assert "## HTTP Fuzzing / Path Discovery" in output
        assert "/admin" in output
        assert "## SSL/TLS Certificate Inspection" in output
        assert "sha256WithRSAEncryption" in output
    elif formatter is format_urlcheck_report_csv:
        assert "section,key,value" in output
        assert "example.com" in output
        assert "https://example.com" in output
        assert "header_present" in output
        assert "Content-Security-Policy" in output
        assert "header_missing" in output
        assert "X-Frame-Options" in output
        assert "information_disclosure" in output
        assert "Server" in output
        assert "/admin (200)" in output
        assert "sha256WithRSAEncryption" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["normalized_target"] == "https://example.com"
        assert parsed["summary"]["total_findings"] == 1
        assert parsed["web"]["host"] == "example.com"
        assert parsed["fuzz"]["paths_tested"] == 2
        assert parsed["ssl"]["cert"]["key_size"] == 2048


@pytest.mark.parametrize("formatter", URLCHECK_FORMATTERS, ids=_formatter_id)
def test_urlcheck_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_urlcheck_report_markdown:
        assert "# ethscan Consolidated Web Assessment Report" in output
        assert "**Total Findings:** 0" in output
        assert "**Web Checks Run:** None" in output
        assert "**Fuzzing Enabled:** No" in output
        assert "**SSL Checked:** No" in output
    elif formatter is format_urlcheck_report_csv:
        assert "section,key,value" in output
        assert "example.com" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["summary"]["total_findings"] == 0
        assert parsed["web"] is None
        assert parsed["fuzz"] is None
        assert parsed["ssl"] is None