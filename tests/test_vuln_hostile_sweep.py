"""Hostile-shape sweep for vuln report formatters."""

from __future__ import annotations

import json
from typing import Any, Mapping, cast

import pytest

from ethscan.vuln import (
    format_vuln_report_csv,
    format_vuln_report_json,
    format_vuln_report_markdown,
)

HOSTILE_TOP_LEVEL: tuple[Any, ...] = (None, [], "x", 123, 1.5, True, b"bytes")


def test_vuln_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(format_vuln_report_json(cast(Mapping[str, object], bad)))
        md = format_vuln_report_markdown(cast(Mapping[str, object], bad))
        csv_text = format_vuln_report_csv(cast(Mapping[str, object], bad))
        assert "ethscan Vulnerability Report" in md
        assert isinstance(csv_text, str)


def test_vuln_formatters_hostile_nested_shapes_never_raise() -> None:
    cases: list[Mapping[str, object]] = [
        cast(Mapping[str, object], {"findings": "x", "notes": "x", "severity_counts": "x"}),
        cast(Mapping[str, object], {"findings": [None, 1, "bad", {"id": 123, "severity": []}]}),
        cast(Mapping[str, object], {"notes": [None, {"k": "v"}]}),
        cast(Mapping[str, object], {"recursive": True, "recursive_hosts_scanned": "x", "recursive_findings": "x"}),
        cast(Mapping[str, object], {"severity_filter": [], "min_severity_filter": {}}),
        cast(
            Mapping[str, object],
            {
                "recursive": True,
                "recursive_hosts_scanned": ["host-a"],
                "recursive_findings": [
                    "not-a-dict",
                    123,
                    None,
                    {
                        "host": "host-b",
                        "depth": 1,
                        "finding_count": 0,
                        "services_checked": 1,
                        "severity_counts": "bad",
                        "findings": "bad",
                    },
                    {
                        "host": "host-c",
                        "depth": 2,
                        "finding_count": 1,
                        "services_checked": 1,
                        "severity_counts": {},
                        "findings": ["not-a-finding", {"id": "X", "severity": "high"}],
                    },
                ],
            },
        ),
    ]
    for data in cases:
        json.loads(format_vuln_report_json(data))
        assert "ethscan Vulnerability Report" in format_vuln_report_markdown(data)
        assert isinstance(format_vuln_report_csv(data), str)


HOSTILE_HOSTS_SCANNED: tuple[object, ...] = (None, 0, 1, True, 1.5, "x", b"bytes")


@pytest.mark.parametrize("shape", HOSTILE_HOSTS_SCANNED)
def test_vuln_markdown_recursive_hosts_scanned_hostile(shape: object) -> None:
    """Permanent sweep: scalar recursive_hosts_scanned must not crash markdown."""
    data = cast(
        Any,
        {
            "target": "1.2.3.4",
            "host": "1.2.3.4",
            "recursive": True,
            "max_depth": 2,
            "recursive_hosts_scanned": shape,
            "recursive_findings": [],
        },
    )
    md = format_vuln_report_markdown(data)
    assert isinstance(md, str)
    assert "ethscan Vulnerability Report" in md
    assert "Recursive Scan Results" not in md


@pytest.mark.parametrize("shape", HOSTILE_HOSTS_SCANNED)
def test_vuln_markdown_recursive_findings_hostile(shape: object) -> None:
    """Permanent sweep: scalar recursive_findings must not crash markdown."""
    data = cast(
        Any,
        {
            "target": "1.2.3.4",
            "host": "1.2.3.4",
            "recursive": True,
            "max_depth": 2,
            "recursive_hosts_scanned": ["1.2.3.5"],
            "recursive_findings": shape,
        },
    )
    md = format_vuln_report_markdown(data)
    assert isinstance(md, str)
    assert "ethscan Vulnerability Report" in md


def test_vuln_markdown_recursive_findings_elem_hostile() -> None:
    """Permanent sweep: non-dict recursive findings elements must not crash."""
    for bad in (None, 0, "x", (1, 2), {1, 2}, b"bytes", True, [1, 2]):
        data = cast(
            Any,
            {
                "target": "1.2.3.4",
                "host": "1.2.3.4",
                "recursive": True,
                "max_depth": 2,
                "recursive_hosts_scanned": ["1.2.3.5"],
                "recursive_findings": [bad],
            },
        )
        md = format_vuln_report_markdown(data)
        assert isinstance(md, str)
        assert "ethscan Vulnerability Report" in md


def test_vuln_markdown_well_formed_recursive_preserved() -> None:
    """Well-formed recursive scan data renders verbatim."""
    data = cast(
        Any,
        {
            "target": "1.2.3.4",
            "host": "1.2.3.4",
            "recursive": True,
            "max_depth": 2,
            "recursive_hosts_scanned": ["1.2.3.5", "1.2.3.6"],
            "recursive_findings": [
                {
                    "host": "1.2.3.5",
                    "depth": 1,
                    "finding_count": 0,
                    "services_checked": 1,
                    "severity_counts": {},
                    "findings": [],
                },
            ],
        },
    )
    md = format_vuln_report_markdown(data)
    assert "Recursive Scan Results" in md
    assert "1.2.3.5" in md
    assert "**Recursive Hosts Scanned:** 2" in md
"""
"""
