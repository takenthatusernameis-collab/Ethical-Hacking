"""Permanent sweep test: hostile ``records`` shapes never raise in formatters.

Covers ``format_dns_report_markdown`` and ``format_dns_report_csv``
with hostile ``records`` field values. The formatters must never raise; they
should render something reasonable (empty or stringified).
"""
from __future__ import annotations

import csv
import io
from typing import Any, cast

import pytest

from ethscan.dns import format_dns_report_csv, format_dns_report_markdown


HOSTILE_RECORDS_SHAPES: tuple[object, ...] = (
    None,
    1,
    "string",
    [None, 1, "x"],
    {"a": 1},
    {"A": "1.2.3.4"},  # single string value
    {"A": ["1.2.3.4", "5.6.7.8"]},  # list value
    {"A": 123},  # non-iterable value
    {"AAAA": "2001:db8::1", "MX": ["mail.example.com"]},  # mixed iterable and non-iterable
)


@pytest.mark.parametrize("records", HOSTILE_RECORDS_SHAPES)
def test_format_dns_report_markdown_hostile_records(records: object) -> None:
    results = {"records": records, "target": "test", "domain": "example.com"}
    report = format_dns_report_markdown(results)
    assert isinstance(report, str)
    assert "# ethscan DNS Record Enumeration Report" in report


@pytest.mark.parametrize("records", HOSTILE_RECORDS_SHAPES)
def test_format_dns_report_csv_hostile_records(records: object) -> None:
    results = {"records": records, "target": "test", "domain": "example.com"}
    report = format_dns_report_csv(results)
    assert isinstance(report, str)
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"


def test_format_dns_report_markdown_well_formed_preserved() -> None:
    """Well-formed records dict is rendered verbatim."""
    results: dict[str, Any] = {
        "records": {"A": ["1.2.3.4", "5.6.7.8"], "AAAA": ["2001:db8::1"]},
        "target": "test",
        "domain": "example.com",
    }
    report = format_dns_report_markdown(cast(Any, results))
    assert "1.2.3.4" in report
    assert "5.6.7.8" in report
    assert "2001:db8::1" in report


def test_format_dns_report_csv_well_formed_preserved() -> None:
    """Well-formed records dict is rendered in CSV."""
    results: dict[str, Any] = {
        "records": {"A": ["1.2.3.4", "5.6.7.8"], "AAAA": ["2001:db8::1"]},
        "target": "test",
        "domain": "example.com",
    }
    report = format_dns_report_csv(cast(Any, results))
    reader = list(csv.reader(io.StringIO(report)))
    rows = [row for row in reader if row and row[0] != "target"]
    assert len(rows) == 3
    assert "1.2.3.4" in report
    assert "5.6.7.8" in report
    assert "2001:db8::1" in report