"""Hostile-input sweep for subtake formatting.

`tests/test_http_hostile_sweep.py` already covers transport/body handling for
HTTP probing helpers and the shared hostile response cases. These tests focus
on hostile result/response shapes passed to report formatters: a cache or
pipeline handoff with non-dict entries, hostile field types, or a hostile top-
level container must never raise and must return structured output.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import pytest

from ethscan.subtake import (
    format_subtake_report_csv,
    format_subtake_report_json,
    format_subtake_report_markdown,
)


HOSTILE_TOPLEVEL: tuple[Any, ...] = (None, [], "x", 123, True, object())


@pytest.mark.parametrize("data", HOSTILE_TOPLEVEL)
def test_csv_toplevel_hostile_never_raises(data: Any) -> None:
    out = format_subtake_report_csv(data)  # type: ignore[arg-type]
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    assert rows == []
    assert reader.fieldnames is not None


@pytest.mark.parametrize("data", HOSTILE_TOPLEVEL)
def test_json_toplevel_hostile_never_raises(data: Any) -> None:
    out = format_subtake_report_json(data)  # type: ignore[arg-type]
    # Must be valid JSON (json.dumps handles primitives/object via default=str)
    json.loads(out)


def test_csv_hostile_entry_shapes_never_raise() -> None:
    data = {
        "target": "t",
        "domain": "d",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": [],
        "all_results": [
            "not-a-dict",
            123,
            None,
            [],
            {
                "subdomain": "x",
                "hostname": "x.d",
                "cname": None,
                "a_records": "nope",
                "aaaa_records": {"bad": 1},
                "vulnerable": False,
                "takeover": "nope",
            },
            {
                "subdomain": "y",
                "hostname": "y.d",
                "cname": "c.example.net",
                "a_records": [1, None, {"x": "y"}],
                "aaaa_records": [float("nan")],
                "vulnerable": True,
                "takeover": {
                    "service": "S3",
                    "cname": "c.example.net",
                    "fingerprint": "fp",
                    "http_confirmed": True,
                },
            },
        ],
    }
    out = format_subtake_report_csv(data)
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    assert [r["hostname"] for r in rows] == ["x.d", "y.d"]


def test_markdown_hostile_entry_shapes_never_raise() -> None:
    data = {
        "target": "t",
        "domain": "d",
        "subdomains_tested": 1,
        "vulnerable_count": 0,
        "vulnerable": ["nope", {"subdomain": "v", "hostname": "v.d", "takeover": "nope"}],
        "all_results": [
            "not-a-dict",
            123,
            None,
            {
                "subdomain": "x",
                "hostname": "x.d",
                "cname": None,
                "a_records": "nope",
                "aaaa_records": None,
                "vulnerable": False,
                "takeover": "nope",
            },
        ],
    }
    out = format_subtake_report_markdown(data)
    assert "ethscan Subdomain Takeover Report" in out
    assert "| x | x.d |" in out


def test_csv_hostile_containers_never_raise() -> None:
    data = {
        "target": "t",
        "domain": "d",
        "subdomains_tested": 0,
        "vulnerable_count": 0,
        "vulnerable": "nope",
        "all_results": "nope",
    }
    out = format_subtake_report_csv(data)
    reader = csv.DictReader(io.StringIO(out))
    assert list(reader) == []
