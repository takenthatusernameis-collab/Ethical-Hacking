"""Permanent sweep test: hostile ``root_dse`` shapes never raise in formatters.

Covers ``format_ldap_report_markdown`` and ``format_ldap_report_csv`` with the
seven hostile shapes enumerated in the handoff. The formatters must never
raise; they should render something reasonable (empty or stringified).
"""
from __future__ import annotations

import csv
import io
from typing import Any, cast

import pytest

from ethscan.ldap import (
    _normalize_root_dse,
    format_ldap_report_csv,
    format_ldap_report_markdown,
)


HOSTILE_SHAPES = [
    (None, "None"),
    (1, "int"),
    ("string", "str"),
    ([1, 2], "list"),
    ({"vendorName": 1}, "dict-int"),
    ({"vendorName": None}, "dict-None"),
    ({"vendorName": [None, 1]}, "dict-list-None-int"),
]


@pytest.mark.parametrize("shape,label", HOSTILE_SHAPES)
def test_format_ldap_report_markdown_hostile_root_dse(shape, label) -> None:
    results = {"root_dse": shape, "accessible": True}
    report = format_ldap_report_markdown(results)
    assert isinstance(report, str)
    assert "# ethscan LDAP Reconnaissance Report" in report


@pytest.mark.parametrize("shape,label", HOSTILE_SHAPES)
def test_format_ldap_report_csv_hostile_root_dse(shape, label) -> None:
    results = {"root_dse": shape, "accessible": True}
    report = format_ldap_report_csv(results)
    assert isinstance(report, str)
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"
    assert len(reader) == 2  # header + one data row


HOSTILE_NOTES: tuple[object, ...] = (1, None, "x", [1, None], {"a": 1})


@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_format_ldap_report_markdown_hostile_notes(notes: object) -> None:
    results: dict[str, object] = {
        "root_dse": {},
        "accessible": True,
        "notes": notes,
    }
    report = format_ldap_report_markdown(cast(Any, results))
    assert isinstance(report, str)
    assert "# ethscan LDAP Reconnaissance Report" in report
    if isinstance(notes, (list, tuple)):
        for note in notes:
            assert str(note) in report
    else:
        assert "## Notes" not in report


@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_format_ldap_report_csv_hostile_notes(notes: object) -> None:
    results: dict[str, object] = {
        "root_dse": {},
        "accessible": True,
        "notes": notes,
    }
    report = format_ldap_report_csv(cast(Any, results))
    assert isinstance(report, str)
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"


def test_normalize_root_dse_hostile_shapes() -> None:
    """Direct unit test for the normalization helper."""
    assert _normalize_root_dse(None) == {}
    assert _normalize_root_dse(1) == {}
    assert _normalize_root_dse("string") == {}
    assert _normalize_root_dse([1, 2]) == {}
    assert _normalize_root_dse({"vendorName": 1}) == {}
    assert _normalize_root_dse({"vendorName": None}) == {}
    assert _normalize_root_dse({"vendorName": [None, 1]}) == {"vendorName": ["None", "1"]}
    # Well-formed input is preserved (elements stringified)
    assert _normalize_root_dse({"vendorName": ["a", "b"]}) == {"vendorName": ["a", "b"]}
    # Non-list values are dropped
    assert _normalize_root_dse({"vendorName": ["a"], "other": 123}) == {"vendorName": ["a"]}


def test_format_ldap_report_markdown_well_formed_preserved() -> None:
    """Well-formed root_dse is rendered verbatim (elements already strings)."""
    results = {
        "root_dse": {"vendorName": ["OpenLDAP"], "namingContexts": ["dc=example,dc=com"]},
        "accessible": True,
    }
    report = format_ldap_report_markdown(results)
    assert "**vendorName:** OpenLDAP" in report
    assert "**namingContexts:** dc=example,dc=com" in report


def test_format_ldap_report_csv_well_formed_preserved() -> None:
    """Well-formed root_dse is rendered verbatim in CSV."""
    results = {
        "root_dse": {"vendorName": ["OpenLDAP"], "namingContexts": ["dc=example,dc=com"]},
        "accessible": True,
    }
    report = format_ldap_report_csv(results)
    reader = list(csv.reader(io.StringIO(report)))
    row = reader[1]
    assert row[11] == "OpenLDAP"  # vendor_name column
    assert row[13] == "dc=example,dc=com"  # naming_contexts column
    # root_dse_attributes column contains all attributes
    assert "vendorName=OpenLDAP" in row[15]
    assert "namingContexts=dc=example,dc=com" in row[15]