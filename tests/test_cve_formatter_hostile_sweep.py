"""Permanent sweep test: hostile CVE formatter inputs are rendered, never raised.

Covers ``format_cve_report_markdown``, ``format_cve_report_csv`` and
``format_cve_report_json`` against hostile top-level shapes and hostile
values for ``cve_entries``, ``severity_counts``, ``notes``, and nested
finding/cve payloads. Every shape yields a string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.cve import (
    format_cve_report_csv,
    format_cve_report_json,
    format_cve_report_markdown,
)

CVE_FORMATTERS: list[Callable[[Any], str]] = [
    format_cve_report_markdown,
    format_cve_report_csv,
    format_cve_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_ENTRIES: list[object] = [
    None,
    1,
    "x",
    True,
    {"a": 1},
    [None, 1, "x", True, 3.14],
    [{"source": "builtin", "finding": None}],
    [{"source": "builtin", "finding": 1}],
    [{"source": "builtin", "finding": "x"}],
    [{"source": "builtin", "finding": {"id": None, "severity": 1, "title": [1], "description": {"x": 1}, "port": "p"}}],
    [{"source": "nvd", "cve": None}],
    [{"source": "nvd", "cve": 1}],
    [{"source": "nvd", "cve": "x"}],
    [{"source": "nvd", "cve": {"severity": 1, "description": [1], "references": "x", "score": {"v": 1}}}],
    [{"source": "nvd", "cve": {"references": [None, 1, {"u": 1}]}}],
    [{"source": "unknown", "finding": {"severity": "high"}, "cve": {"severity": "low"}}],
]

HOSTILE_SEVERITY_COUNTS: list[object] = [
    None,
    1,
    "x",
    [1, 2],
    {"critical": "x", "high": None, 1: 2},
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    "note",
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "ok"],
]

HOSTILE_PORTS: list[object] = [None, 1, "80", {"p": 80}, [80, "443", None]]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "timeout": 10.0,
    "use_cache": True,
    "offline_fallback": True,
    "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
    "cve_entries": [
        {
            "source": "builtin",
            "port": 22,
            "product": "OpenSSH",
            "version": "8.0",
            "finding": {
                "id": "CVE-TEST-1",
                "severity": "high",
                "title": "Test issue",
                "description": "Test desc",
                "kind": "service",
                "product": "OpenSSH",
                "version": "8.0",
                "port": 22,
            },
            "cve": {"id": "CVE-TEST-1", "severity": "high"},
        },
        {
            "source": "nvd",
            "port": 80,
            "product": "nginx",
            "version": "1.0",
            "cve_id": "CVE-TEST-2",
            "cve": {
                "id": "CVE-TEST-2",
                "severity": "medium",
                "score": 5.0,
                "description": "NVD desc",
                "references": ["https://example.com"],
            },
            "cached": True,
            "offline_fallback": False,
        },
    ],
    "notes": ["ok"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_cve_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_cve_report_json:
        assert output == "{}"


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entries", HOSTILE_ENTRIES)
def test_cve_formatters_tolerate_hostile_cve_entries(
    formatter: Callable[[Any], str], entries: object
) -> None:
    output = formatter({"cve_entries": entries})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("counts", HOSTILE_SEVERITY_COUNTS)
def test_cve_formatters_tolerate_hostile_severity_counts(
    formatter: Callable[[Any], str], counts: object
) -> None:
    output = formatter({"severity_counts": counts})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_cve_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ports", HOSTILE_PORTS)
def test_cve_formatters_tolerate_hostile_ports(
    formatter: Callable[[Any], str], ports: object
) -> None:
    output = formatter({"ports": ports})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
def test_cve_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "CVE-TEST-1" in output
        assert "NVD desc" in output
        assert "Severity Summary" in output
    elif formatter is format_cve_report_csv:
        assert "CVE-TEST-1" in output
        assert "CVE-TEST-2" in output
