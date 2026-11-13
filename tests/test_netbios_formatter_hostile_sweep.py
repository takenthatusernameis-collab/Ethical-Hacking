"""Permanent sweep test: hostile ``names`` shapes never raise in formatters.

Covers ``format_netbios_report_markdown`` and ``format_netbios_report_csv``
with hostile ``names`` field values. The formatters must never raise; they
should render something reasonable (empty or stringified).
"""
from __future__ import annotations

import csv
import io

import pytest

from ethscan.netbios import (
    _normalize_names,
    format_netbios_report_csv,
    format_netbios_report_markdown,
)


HOSTILE_NAMES_SHAPES: tuple[object, ...] = (
    None,
    1,
    "string",
    [None, 1, "x"],
    {"a": 1},
    [{"name": "test", "suffix": "<00>", "suffix_hex": "00", "service_type": "Workstation", "flags": {"group": True}}],
)


@pytest.mark.parametrize("names", HOSTILE_NAMES_SHAPES)
def test_format_netbios_report_markdown_hostile_names(names: object) -> None:
    results = {"names": names, "target": "test", "host": "test"}
    report = format_netbios_report_markdown(results)
    assert isinstance(report, str)
    assert "# ethscan NetBIOS Report" in report


@pytest.mark.parametrize("names", HOSTILE_NAMES_SHAPES)
def test_format_netbios_report_csv_hostile_names(names: object) -> None:
    results = {"names": names, "target": "test", "host": "test"}
    report = format_netbios_report_csv(results)
    assert isinstance(report, str)
    reader = list(csv.reader(io.StringIO(report)))
    assert reader[0][0] == "target"
    assert len(reader) >= 2  # header + summary row


def test_normalize_names_hostile_shapes() -> None:
    """Direct unit test for the normalization helper."""
    assert _normalize_names(None) == []
    assert _normalize_names(1) == []
    assert _normalize_names("string") == []
    assert _normalize_names([None, 1, "x"]) == []
    assert _normalize_names({"a": 1}) == []
    assert _normalize_names([{"name": "test"}]) == [{"name": "test"}]
    assert _normalize_names([{"name": "test"}, "not a dict"]) == [{"name": "test"}]


def test_format_netbios_report_markdown_well_formed_preserved() -> None:
    """Well-formed names list is rendered verbatim."""
    results = {
        "names": [
            {"name": "TEST", "suffix": "<00>", "suffix_hex": "00", "service_type": "Workstation", "flags": {"group": True, "unique": False, "permanent": True, "active": True, "conflict": False}}
        ],
        "target": "test",
        "host": "test",
        "accessible": True,
    }
    report = format_netbios_report_markdown(results)
    assert "TEST" in report
    assert "Workstation" in report
    assert "group" in report


def test_format_netbios_report_csv_well_formed_preserved() -> None:
    """Well-formed names list is rendered in CSV."""
    results = {
        "names": [
            {"name": "TEST", "suffix": "<00>", "suffix_hex": "00", "service_type": "Workstation", "flags": {"group": True, "unique": False, "permanent": True, "active": True, "conflict": False}}
        ],
        "target": "test",
        "host": "test",
        "accessible": True,
    }
    report = format_netbios_report_csv(results)
    assert "TEST" in report
    assert "Workstation" in report