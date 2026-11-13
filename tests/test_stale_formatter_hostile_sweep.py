"""Permanent sweep test: hostile per-key record shapes never raise in formatters.

Covers ``format_stale_report_markdown`` and ``format_stale_report_csv`` with the
hostile shapes enumerated in the handoff. The formatters must never raise; they
should render something reasonable (empty or stringified). The previously
unguarded ``A`` / ``AAAA`` / ``stale_reasons`` fields (which crashed with
``TypeError: 'int' object is not iterable`` when fed a non-list value) are now
normalized via ``_normalize_records``.
"""
from __future__ import annotations

import csv
import io
from typing import Any, cast

import pytest

from ethscan.stale import (
    _normalize_records,
    format_stale_report_csv,
    format_stale_report_json,
    format_stale_report_markdown,
)


RECORD_HOSTILE: tuple[object, ...] = (
    None,
    1,
    True,
    1.5,
    "string",
    b"bytes",
    [],
    [1, 2, 3],
    {"a": 1},
    (1, 2),
    {1, 2},
    [None, 1, "two", 3.0],
    [{"a": 1}, {"b": 2}],
)


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_stale_report_markdown_hostile_records(shape: object) -> None:
    data = {
        "results": [
            {"domain": "a.example.com", "A": shape, "AAAA": shape, "stale_reasons": shape},
        ],
        "stale_results": [
            {"domain": "b.example.com", "A": shape, "AAAA": shape, "stale_reasons": shape},
        ],
    }
    md = format_stale_report_markdown(cast(Any, data))
    assert isinstance(md, str)
    assert "ethscan Stale DNS Record Detection Report" in md


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_stale_report_csv_hostile_records(shape: object) -> None:
    data = {
        "results": [
            {"domain": "a.example.com", "A": shape, "AAAA": shape, "stale_reasons": shape},
        ],
    }
    csv_text = format_stale_report_csv(cast(Any, data))
    assert isinstance(csv_text, str)
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert reader[0][0] == "domain"


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_stale_report_json_hostile_records(shape: object) -> None:
    import json

    data = {
        "results": [
            {"domain": "a.example.com", "A": shape, "AAAA": shape, "stale_reasons": shape},
        ],
    }
    parsed = json.loads(format_stale_report_json(cast(Any, data)))
    assert isinstance(parsed, dict)


def test_normalize_records_hostile_shapes() -> None:
    """Direct unit test for the normalization helper."""
    assert _normalize_records(None) == []
    assert _normalize_records(1) == ["1"]
    assert _normalize_records(True) == ["True"]
    assert _normalize_records(1.5) == ["1.5"]
    assert _normalize_records("string") == ["string"]
    assert _normalize_records(b"bytes") == []
    assert _normalize_records([]) == []
    assert _normalize_records([1, 2, 3]) == ["1", "2", "3"]
    assert _normalize_records({"a": 1}) == ["{'a': 1}"]
    assert _normalize_records((1, 2)) == ["1", "2"]
    assert _normalize_records({1, 2}) == ["1", "2"]
    assert _normalize_records([None, 1, "two", 3.0]) == ["None", "1", "two", "3.0"]
    assert _normalize_records([{"a": 1}, {"b": 2}]) == ["{'a': 1}", "{'b': 2}"]


def test_format_stale_report_markdown_well_formed_preserved() -> None:
    """Well-formed record lists render verbatim."""
    entry = {
        "domain": "a.example.com",
        "A": ["1.2.3.4", "5.6.7.8"],
        "AAAA": ["::1"],
        "CNAME": "target.example.com",
        "stale": True,
        "stale_reasons": ["IP 1.2.3.4 unreachable"],
    }
    data = {
        "results": [entry],
        "stale_results": [entry],
    }
    md = format_stale_report_markdown(cast(Any, data))
    assert "1.2.3.4, 5.6.7.8" in md
    assert "::1" in md
    assert "IP 1.2.3.4 unreachable" in md
    assert "9.10.11.12" not in md

    fresh = {
        "domain": "b.example.com",
        "A": ["9.10.11.12"],
        "AAAA": [],
        "CNAME": None,
        "stale": False,
        "stale_reasons": [],
    }
    md2 = format_stale_report_markdown(cast(Any, {"results": [fresh], "stale_results": []}))
    assert "9.10.11.12" in md2


def test_format_stale_report_csv_well_formed_preserved() -> None:
    """Well-formed record lists render verbatim in CSV."""
    data = {
        "results": [
            {
                "domain": "a.example.com",
                "A": ["1.2.3.4", "5.6.7.8"],
                "AAAA": ["::1"],
                "CNAME": "target.example.com",
                "stale": True,
                "stale_reasons": ["IP 1.2.3.4 unreachable"],
            },
        ],
    }
    csv_text = format_stale_report_csv(cast(Any, data))
    reader = list(csv.reader(io.StringIO(csv_text)))
    row = reader[1]
    assert row[0] == "a.example.com"
    assert row[1] == "1.2.3.4, 5.6.7.8"
    assert row[2] == "::1"
    assert row[3] == "target.example.com"
    assert row[4] == "true"
    assert row[5] == "IP 1.2.3.4 unreachable"