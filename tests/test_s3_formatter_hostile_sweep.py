"""Permanent sweep test: hostile s3 formatter inputs are rendered, never raised.

Covers ``format_s3_report_markdown``, ``format_s3_report_csv`` and
``format_s3_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``results``, ``public_buckets``,
``private_buckets``, ``existing_buckets``, ``regions_checked``, ``notes``).
Every shape yields a string and never raises, and the JSON formatter
always emits parseable JSON.
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
    ("domain", "x"),
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
    ("regions_checked", {}),
    ("results", "x"),
    ("results", None),
    ("results", {}),
    ("results", 1),
    ("public_buckets", "x"),
    ("public_buckets", None),
    ("public_buckets", {}),
    ("public_buckets", 1),
    ("private_buckets", "x"),
    ("private_buckets", None),
    ("private_buckets", {}),
    ("private_buckets", 1),
    ("existing_buckets", "x"),
    ("existing_buckets", None),
    ("existing_buckets", {}),
    ("existing_buckets", 1),
    ("notes", "x"),
    ("notes", None),
    ("notes", {}),
    ("notes", 1),
]

HOSTILE_BUCKET_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"bucket": None},
    {"bucket": 1},
    {"bucket": []},
    {"region": None},
    {"region": 1},
    {"region": []},
    {"url": None},
    {"url": 1},
    {"url": []},
    {"status_code": "x"},
    {"status_code", None},
    {"status_code": []},
    {"dns_resolved": 1},
    {"dns_resolved": []},
    {"dns_resolved": {}},
    {"exists": "x"},
    {"exists": None},
    {"exists": []},
    {"public": "x"},
    {"public": None},
    {"public": []},
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
            "status_code": 200,
            "dns_resolved": "1.2.3.4",
            "exists": True,
            "public": True,
            "error": None,
        },
        {
            "bucket": "example-dev",
            "region": "us-east-1",
            "url": "https://example-dev.s3.amazonaws.com/",
            "status_code": 403,
            "dns_resolved": "1.2.3.5",
            "exists": True,
            "public": False,
            "error": None,
        },
    ],
    "public_buckets": [
        {
            "bucket": "example-backup",
            "region": "us-east-1",
            "url": "https://example-backup.s3.amazonaws.com/",
            "status_code": 200,
            "dns_resolved": "1.2.3.4",
            "exists": True,
            "public": True,
            "error": None,
        }
    ],
    "private_buckets": [
        {
            "bucket": "example-dev",
            "region": "us-east-1",
            "url": "https://example-dev.s3.amazonaws.com/",
            "status_code": 403,
            "dns_resolved": "1.2.3.5",
            "exists": True,
            "public": False,
            "error": None,
        }
    ],
    "existing_buckets": [
        {
            "bucket": "example-backup",
            "region": "us-east-1",
            "url": "https://example-backup.s3.amazonaws.com/",
            "status_code": 200,
            "dns_resolved": "1.2.3.4",
            "exists": True,
            "public": True,
            "error": None,
        },
        {
            "bucket": "example-dev",
            "region": "us-east-1",
            "url": "https://example-dev.s3.amazonaws.com/",
            "status_code": 403,
            "dns_resolved": "1.2.3.5",
            "exists": True,
            "public": False,
            "error": None,
        },
    ],
    "notes": ["Checked 1 region for 2 bucket candidates."],
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
@pytest.mark.parametrize("results", HOSTILE_BUCKET_ENTRY)
def test_s3_formatters_tolerate_hostile_results(
    formatter: Callable[[Any], str], results: object
) -> None:
    output = formatter({"results": results})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["public_buckets", "private_buckets", "existing_buckets"])
@pytest.mark.parametrize("buckets", HOSTILE_BUCKET_ENTRY)
def test_s3_formatters_tolerate_hostile_bucket_lists(
    formatter: Callable[[Any], str], field: str, buckets: object
) -> None:
    output = formatter({field: buckets})
    assert isinstance(output, str)
    if formatter is format_s3_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", S3_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field", ["regions_checked", "notes"])
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_s3_formatters_tolerate_hostile_simple_lists(
    formatter: Callable[[Any], str], field: str, lst: object
) -> None:
    output = formatter({field: lst})
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
            "timeout": "x",
            "workers": {},
            "wordlist_used": 1,
            "candidates_tested": "many",
            "regions_checked": [None, 1, {}],
            "results": [
                {"bucket": None, "region": 1, "url": [], "status_code": "x", "dns_resolved": {}, "exists": "yes", "public": [], "error": 123},
                "not-a-dict",
                None,
                1,
            ],
            "public_buckets": [None, {"bucket": []}, "bad"],
            "private_buckets": {"not": "a-list"},
            "existing_buckets": 1,
            "notes": [None, 1, {}],
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
        assert "**Timeout:** 5.0s" in output
        assert "**Workers:** 20" in output
        assert "**Wordlist Used:** No" in output
        assert "**Candidates Tested:** 2" in output
        assert "**Regions Checked:** us-east-1" in output
        assert "**Public Buckets:** 1" in output
        assert "**Private Buckets:** 1" in output
        assert "**Existing Buckets:** 2" in output
        assert "## Public Buckets (Accessible)" in output
        assert "example-backup" in output
        assert "https://example-backup.s3.amazonaws.com/" in output
        assert "1.2.3.4" in output
        assert "## All Bucket Results" in output
        assert "example-dev" in output
        assert "403" in output
        assert "## Notes" in output
        assert "Checked 1 region for 2 bucket candidates" in output
    elif formatter is format_s3_report_csv:
        assert "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error" in output
        assert "example.com,example.com,example-backup,us-east-1,https://example-backup.s3.amazonaws.com/,200,1.2.3.4,True,True," in output
        assert "example.com,example.com,example-dev,us-east-1,https://example-dev.s3.amazonaws.com/,403,1.2.3.5,True,False," in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["domain"] == "example.com"
        assert parsed["region"] == "us-east-1"
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["bucket"] == "example-backup"
        assert parsed["results"][0]["public"] is True
        assert parsed["results"][1]["bucket"] == "example-dev"
        assert parsed["results"][1]["public"] is False
        assert len(parsed["public_buckets"]) == 1
        assert len(parsed["private_buckets"]) == 1
        assert len(parsed["existing_buckets"]) == 2
        assert parsed["notes"] == ["Checked 1 region for 2 bucket candidates."]


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
        assert "**Private Buckets:** 0" in output
        assert "**Existing Buckets:** 0" in output
        assert "## Public Buckets (Accessible)" in output
        assert "*No publicly accessible buckets found.*" in output
        assert "## All Bucket Results" in output
        assert "*No buckets were tested.*" in output
    elif formatter is format_s3_report_csv:
        assert "target,domain,bucket,region,url,status_code,dns_resolved,exists,public,error" in output
        # Only header row for minimal case
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