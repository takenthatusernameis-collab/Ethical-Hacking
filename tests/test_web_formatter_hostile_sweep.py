"""Permanent sweep test: hostile web formatter inputs are rendered, never raised.

Covers ``format_web_report_markdown``, ``format_web_report_csv`` and
``format_web_report_json`` against hostile top-level shapes and hostile
values for ``security_headers``, ``information_disclosure``, ``findings``,
``ssl`` and ``notes``. Every shape yields a string and never raises.

The CSV formatter previously crashed with ``TypeError: 'int' object is not
iterable`` when ``security_headers["present"]``/``["missing"]`` was a truthy
non-list (regression test ``test_web_csv_formatters_reject_non_list_header_lists``
pins that payload).
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.web import (
    format_web_report_csv,
    format_web_report_json,
    format_web_report_markdown,
)

WEB_FORMATTERS: list[Callable[[Any], str]] = [
    format_web_report_markdown,
    format_web_report_csv,
    format_web_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_SECURITY_HEADERS: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    [1, 2],
    {"a": 1},
    {"present": 1},
    {"missing": "x"},
    {"present": None},
    {"missing": None},
    {"present_count": "y", "total": None},
    {"present": ["Content-Security-Policy"], "missing": ["X-Frame-Options"]},
    {"present": [1, None, 2.5, {"nested": True}], "missing": ["ok", None]},
]

HOSTILE_INFORMATION_DISCLOSURE: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    [1, 2],
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, ["x"], "ok"],
    [{"header": None, "value": 1, "description": ["x"]}],
    ["not-a-dict", {"header": "Server", "value": "Apache", "description": "info"}],
]

HOSTILE_FINDINGS: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    [1, 2],
    {"a": 1},
    [None, 1, True, 3.14, "finding", {"nested": True}],
    ["ok", None, 2.5],
]

HOSTILE_SSL: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    [1, 2],
    {"a": 1},
    {"valid": "yes", "error": None, "subject": 1, "issuer": None},
    {"valid": False, "error": 1, "not_after": "not-a-date", "days_remaining": "a lot", "chain_length": None},
    {"valid": True, "subject": {"cn": "x"}, "issuer": ["list"]},
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    0,
    True,
    "note",
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "cached"],
]

WELL_FORMED = {
    "target": "https://example.com",
    "host": "example.com",
    "port": 443,
    "secure": True,
    "headers": {"content-type": "text/html"},
    "security_headers": {
        "present": ["Content-Security-Policy"],
        "missing": ["X-Frame-Options"],
        "total": 7,
        "present_count": 1,
        "missing_count": 6,
    },
    "information_disclosure": [
        {"header": "Server", "value": "Apache/2.4", "description": "Server version"},
    ],
    "findings": ["Out-of-support web server version detected."],
    "ssl": {
        "valid": True,
        "subject": "example.com",
        "issuer": "Let's Encrypt",
        "not_after": "Jan  1 00:00:00 2027 GMT",
        "days_remaining": 100,
        "chain_length": 2,
    },
    "notes": ["Completed"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_web_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("security_headers", HOSTILE_SECURITY_HEADERS)
def test_web_formatters_tolerate_hostile_security_headers(
    formatter: Callable[[Any], str], security_headers: object
) -> None:
    output = formatter({"security_headers": security_headers})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("information_disclosure", HOSTILE_INFORMATION_DISCLOSURE)
def test_web_formatters_tolerate_hostile_information_disclosure(
    formatter: Callable[[Any], str], information_disclosure: object
) -> None:
    output = formatter({"information_disclosure": information_disclosure})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDINGS)
def test_web_formatters_tolerate_hostile_findings(
    formatter: Callable[[Any], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ssl", HOSTILE_SSL)
def test_web_formatters_tolerate_hostile_ssl(
    formatter: Callable[[Any], str], ssl: object
) -> None:
    output = formatter({"ssl": ssl})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_web_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
def test_web_formatters_render_well_formed(formatter: Callable[[Any], str]) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_web_report_markdown:
        assert "# ethscan Web Security Report" in output
        assert "example.com" in output
        assert "## Security Headers" in output
        assert "## Information Disclosure" in output
        assert "## SSL/TLS" in output
        assert "Apache/2.4" in output
    elif formatter is format_web_report_csv:
        assert "field,value" in output
        assert "example.com" in output
        assert "Apache/2.4" in output
    else:
        import json

        parsed = json.loads(output)
        assert parsed["target"] == "https://example.com"
        assert parsed["security_headers"]["total"] == 7


# ---------------------------------------------------------------------------
# Regression: exact crash payload pinned.
# ---------------------------------------------------------------------------


_CSV_CRASH_PAYLOAD = {
    "security_headers": {"present": 1, "missing": "x", "total": None, "present_count": "y"}
}


@pytest.mark.parametrize("formatter", WEB_FORMATTERS, ids=_formatter_id)
def test_web_formatters_tolerate_non_list_header_lists_regression(
    formatter: Callable[[Any], str],
) -> None:
    # Before the fix, ``format_web_report_csv`` raised ``TypeError: 'int'
    # object is not iterable`` when ``security_headers["present"]`` was a
    # truthy non-list. All three formatters must now render a string.
    output = formatter(_CSV_CRASH_PAYLOAD)
    assert isinstance(output, str)
    if formatter is format_web_report_csv:
        assert "security_header,status" in output
