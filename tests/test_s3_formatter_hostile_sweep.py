"""Permanent sweep test: hostile s3 formatter inputs are rendered, never raised.

Covers ``format_s3_report_markdown``, ``format_s3_report_csv`` and
``format_s3_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``results``, ``public_buckets``,
``private_buckets``, ``existing_buckets``, ``regions_checked``, ``notes``).
Every shape yields a string and never raises, and the JSON
formatter always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.s3 import (
    format_s3_report_csv,
    format_s3_report_json,
    format_s3_report_markdown,
)

S3_FORMATTERS: list[Callable[[Any], str]] = [
    format_s3_report_markdown,
    format_s3_report_csv,
    format_s3_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", "x"),
    ("target", None),
    ("target", []),
    ("domain", 1),
    ("domain", None),
    ("domain", []),
    ("region", "x"),
    ("region", None),
    ("region", []),
    ("timeout", "x"),
    ("timeout", None),
    ("timeout", []),
    ("workers", "x"),
    ("workers", None),
    ("workers", []),
    ("wordlist_used", "x"),
    ("wordlist_used", None),
    ("wordlist_used", []),
    ("candidates_tested", "x"),
    ("candidates_tested", None),
    ("candidates_tested", []),
    ("regions_checked", "x"),
    ("regions_checked", None),
    ("regions_checked", [None, 1, {}]),
    ("results", "x"),
    ("results", 1),
    ("results", [None, 1, {}]),
    ("public_buckets", "x"),
    ("public_buckets", 1),
    ("public_buckets", [None, 1, {}]),
    ("private_buckets", "x"),
    ("private_buckets", 1),
    ("private_buckets", [None, 1, {}]),
    ("existing_buckets", "x"),
    ("existing_buckets", 1),
    ("existing_buckets", [None, 1, {}]),
    ("notes", "x"),
    ("notes", 1),
    ("notes", [None, 1, {}]),
]

HOSTILE_RESULTS: list[object] = [
    None,
    1,
    "x",
    {},
    [],
    [None, 1, "str", {}, []],
    [{"bucket": None}, {"bucket": 1}, {"bucket": []}],
    [{"region": None}, {"region": 1}, {"region": []}],
    [{"exists": "yes"}, {"public": "yes"}, {"status_code": "x"}],
    [{"dns_resolved": None}, {"dns_resolved": 1}, {"dns_resolved": []}],
    [{"error": None}, {"error": 1}, {"error": []}],
    [{"url": None}, {"url": 1}, {"url": []}],
]

HOSTILE_PUBLIC_BUCKETS: list[object] = [
    None,
    1,
    "x",
    {},
    [],
    [None, 1, "str", {}, []],
    [{"bucket": None}, {"bucket": 1}, {"bucket": []}],
    [{"region": None}, {"region": 1}, {"region": []}],
    [{"url": None}, {"url": 1}, {"url": []}],
    [{"dns_resolved": None}, {"dns_resolved": 1}, {"dns_resolved": []}],
]

HOSTILE_PRIVATE_BUCKETS: list[object] = [
    None,
    1,
    "x",
    {},
    [],
    [None, 1, "str", {}, []],
    [{"bucket": None}, {"bucket": 1}, {"bucket": []}],
    [{"region": None}, {"region": 1}, {"region": []}],
]

HOSTILE_EXISTING_BUCKETS: list[object] = [
    None,
    1,
    "x",
    {},
    [],
    [None, 1, "str", {}, []],
    [{"bucket": None}, {"bucket": 1}, {"bucket": []}],
    [{"region": None}, {"region": 1}, {"region": []}],
]

HOSTILE_REGIONS_CHECKED: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, "str", {}, []],
    ["us-east-1", None, 1, {}],
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, "str", {}, []],
    ["note", None, 1, {}],
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "region": "us-east-1",
    "timeout": 5.0,
    "workers": 20,
    "wordlist_used": False,
    "candidates_tested": 2,
    "regions_checked": ["us-east-1"],
    "results": [
        {
            "bucket": "example-backup",
            "region": "us-east-1",
            "url": "https://example-backup.s3.amazonaws.com/",
            "status_code": 404,
            "dns_resolved": "1.2.3.4",
            "exists": False,
            "public": False,
            "error": None,
        },
        {
            "bucket": "example-cdn",
            "region": "us-east-1",
            "url": "https://example-cdn.s3.amazonaws.com/",
            "status_code": 200,
            "dns_resolved": "5.6.7.8",
            "exists": True,
            "public": True,
            "error": None,
        },
    ],
    "public_buckets": [
        {
            "bucket": "example-cdn",
            "region": "us-east-1",
            "url": "https://example-cdn.s3.amazonaws.com/",
            "dns_resolved": "5.6.7.8",
        }
    ],
    "private_buckets": [],
    "existing_buckets": [
        {
            "bucket": "example-cdn",
            "region": "us-east-1",
            "url": "https://example-cdn.s3.amazonaws.com/",
            "status_code": 200,
            "dns_resolved": "5.6.7.8",
            "exists": True,
            "public": True,
            "error": None,
        }
    ],
    "notes": ["Checked 1 region for each of 2 bucket candidates."],
}

WELL_FORMED_MINIMAL = {
    "target": "example.com",
    "domain": "example.com",
    "region": "us-east-1",
    "timeout": 5.0,
    "workers": 20,
    "wordlist_used": False,
    "candidates_tested": 0,
    "regions_checked": [],
    "results": [],
    "public_buckets": [],
    "private_buckets": [],
    "existing_buckets": [],
    "notes": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_s3_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_s3_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("results", HOSTILE_RESULTS)
def test_s3_formatters_tolerate_hostile_results(
    formatter: Callable[[Any], str], results: object
) -> None:
    output = formatter({"results": results})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("public_buckets", HOSTILE_PUBLIC_BUCKETS)
def test_s3_formatters_tolerate_hostile_public_buckets(
    formatter: Callable[[Any], str], public_buckets: object
) -> None:
    output = formatter({"public_buckets": public_buckets})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("private_buckets", HOSTILE_PRIVATE_BUCKETS)
def test_s3_formatters_tolerate_hostile_private_buckets(
    formatter: Callable[[Any], str], private_buckets: object
) -> None:
    output = formatter({"private_buckets": private_buckets})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("existing_buckets", HOSTILE_EXISTING_BUCKETS)
def test_s3_formatters_tolerate_hostile_existing_buckets(
    formatter: Callable[[Any], str], existing_buckets: object
) -> None:
    output = formatter({"existing_buckets": existing_buckets})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("regions_checked", HOSTILE_REGIONS_CHECKED)
def test_s3_formatters_tolerate_hostile_regions_checked(
    formatter: Callable[[Any], str], regions_checked: object
) -> None:
    output = formatter({"regions_checked": regions_checked})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_s3_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
def test_s3_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "target": "x",
            "domain": None,
            "region": [],
            "timeout": "five",
            "workers": "many",
            "wordlist_used": "yes",
            "candidates_tested": "lots",
            "regions_checked": [None, 1, "us-east-1", {}],
            "results": [
                {
                    "bucket": None,
                    "region": 1,
                    "url": [],
                    "status_code": "x",
                    "dns_resolved": {},
                    "exists": "yes",
                    "public": "no",
                    "error": [],
                },
                {
                    "bucket": "test",
                    "region": "us-east-1",
                    "url": "https://test.s3.amazonaws.com/",
                    "status_code": 200,
                    "dns_resolved": "1.2.3.4",
                    "exists": True,
                    "public": True,
                    "error": None,
                },
            ],
            "public_buckets": [None, {"bucket": "public1"}, 1],
            "private_buckets": [{"bucket": "private1"}],
            "existing_buckets": [{"bucket": "exist1"}],
            "notes": [None, "note1", 1, {}],
        }
    )
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
def test_s3_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_s3_report_markdown:
        assert "# ethscan S3 Bucket Enumeration Report" in output
        assert "**Target:** example.com" in output
        assert "**Domain:** example.com" in output
        assert "**Region:** us-east-1" in output
        assert "**Candidates Tested:** 2" in output
        assert "**Public Buckets:** 1" in output
        assert "**Private Buckets:** 0" in output
        assert "**Existing Buckets:** 1" in output
        assert "## Public Buckets (Accessible)" in output
        assert "example-cdn" in output
        assert "https://example-cdn.s3.amazonaws.com/" in output
        assert "5.6.7.8" in output
        assert "## All Bucket Results" in output
        assert "example-backup" in output
        assert "404" in output
        assert "## Notes" in output
        assert "Checked 1 region for each of 2 bucket candidates" in output
    elif formatter is format_s3_report_csv:
        assert "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error" in output
        assert "example.com,example.com,example-backup,us-east-1,https://example-backup.s3.amazonaws.com/,404,1.2.3.4,False,False," in output
        assert "example.com,example.com,example-cdn,us-east-1,https://example-cdn.s3.amazonaws.com/,200,5.6.7.8,True,True," in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["domain"] == "example.com"
        assert parsed["region"] == "us-east-1"
        assert parsed["candidates_tested"] == 2
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["bucket"] == "example-backup"
        assert parsed["results"][0]["status_code"] == 404
        assert parsed["results"][1]["bucket"] == "example-cdn"
        assert parsed["results"][1]["status_code"] == 200
        assert parsed["public_buckets"][0]["bucket"] == "example-cdn"
        assert parsed["notes"] == ["Checked 1 region for each of 2 bucket candidates."]


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
def test_s3_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_s3_report_markdown:
        assert "# ethscan S3 Bucket Enumeration Report" in output
        assert "**Target:** example.com" in output
        assert "**Candidates Tested:** 0" in output
        assert "**Public Buckets:** 0" in output
        assert "*No publicly accessible buckets found.*" in output
        assert "*No buckets were tested.*" in output
    elif formatter is format_s3_report_csv:
        assert "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error" in output
        # Only header row for minimal
        lines = output.strip().split("\n")
        assert len(lines) == 1
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["candidates_tested"] == 0
        assert parsed["results"] == []
        assert parsed["public_buckets"] == []
        assert parsed["private_buckets"] == []
        assert parsed["existing_buckets"] == []
        assert parsed["notes"] == []