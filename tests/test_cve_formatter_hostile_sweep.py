"""Permanent sweep test: hostile CVE formatter inputs are rendered, never raised.

Covers ``format_cve_report_markdown``, ``format_cve_report_csv`` and
``format_cve_report_json`` against hostile top-level shapes, ``cve_entries``,
``severity_counts``, ``ports`` and ``notes``. Every shape yields a string and
never raises; the formatters already guard their inputs via ``isinstance``
checks, so this is regression coverage.
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

NON_LIST_CVE_ENTRIES: list[object] = [None, 1, 0, True, "entry", {"x": 1}, 3.14]

HOSTILE_CVE_ENTRY_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
    ["not-a-dict", {"source": "builtin", "finding": {"id": "CVE-1"}}],
    [{"source": "builtin", "finding": None}],
    [{"source": "nvd", "cve": None}],
    [{"source": "nvd", "cve": {"id": "CVE-1", "severity": 1}}],
    [{"source": "nvd", "cve": {"severity": "high", "description": 123}}],
    [{"source": "nvd", "cve": {"references": "not-a-list"}}],
    [{"finding": {"id": 1, "severity": "high"}}, {"cve": {"id": "CVE-2"}}],
]

NON_DICT_SEVERITY_COUNTS: list[object] = [None, 1, 0, True, "counts", ["x"], 3.14]

HOSTILE_SEVERITY_COUNTS: list[dict[str, object]] = [
    {"critical": "not-a-number"},
    {"high": None},
    {"medium": 3.14},
    {"low": True},
    {"unknown": 5},
]

NON_LIST_PORTS: list[object] = [None, 1, 0, True, "ports", {"x": 1}, 3.14]

HOSTILE_PORTS_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

NON_LIST_NOTES: list[object] = [None, 1, 0, True, "note", {"x": 1}, 3.14]

HOSTILE_NOTE_LISTS: list[list[object]] = [
    [None],
    [1],
    [None, 1],
    ["ok", None, 1, 2.5, {"nested": True}],
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "timeout": 10,
    "service_timeout": 3.0,
    "workers": 50,
    "use_cache": True,
    "offline_fallback": True,
    "api_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
    "severity_filter": None,
    "min_severity_filter": None,
    "ports": [22, 80, 443],
    "profile": "normal",
    "services_checked": 3,
    "error": None,
    "cve_entries": [
        {
            "source": "builtin",
            "port": 22,
            "product": "OpenSSH",
            "version": "7.2",
            "finding": {
                "id": "CVE-2016-6210",
                "severity": "high",
                "title": "User Enumeration",
                "description": "OpenSSH user enumeration",
            },
        },
        {
            "source": "nvd",
            "port": 80,
            "product": "Apache",
            "version": "2.4.1",
            "cve_id": "CVE-2021-41773",
            "cve": {
                "id": "CVE-2021-41773",
                "severity": "critical",
                "score": 9.8,
                "description": "Path traversal",
                "published": "2021-09-06",
                "last_modified": "2021-10-07",
                "references": ["https://example.com/ref1"],
            },
            "cached": True,
            "offline_fallback": False,
        },
    ],
    "cve_count": 2,
    "severity_counts": {"critical": 1, "high": 1, "medium": 0, "low": 0},
    "notes": ["served from cache"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


# ---------------------------------------------------------------------------
# Non-Mapping top-level data.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_cve_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_cve_report_json:
        assert output == "{}"


# ---------------------------------------------------------------------------
# Hostile ``cve_entries`` values (iterated by Markdown and CSV).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cve_entries", NON_LIST_CVE_ENTRIES)
def test_cve_formatters_tolerate_non_list_cve_entries(
    formatter: Callable[[Any], str], cve_entries: object
) -> None:
    output = formatter({"cve_entries": cve_entries})
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "No CVEs matched" in output


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cve_entries", HOSTILE_CVE_ENTRY_LISTS)
def test_cve_formatters_render_hostile_cve_entry_lists(
    formatter: Callable[[Any], str], cve_entries: list[object]
) -> None:
    output = formatter({"cve_entries": cve_entries})
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "CVE Findings" in output


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
def test_cve_formatters_still_render_well_formed_cve_entries(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output
        assert "User Enumeration" in output
        assert "Path traversal" in output
    elif formatter is format_cve_report_csv:
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output
    elif formatter is format_cve_report_json:
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output


# ---------------------------------------------------------------------------
# Hostile ``severity_counts`` values (accessed in Markdown).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("severity_counts", NON_DICT_SEVERITY_COUNTS)
def test_cve_formatters_tolerate_non_dict_severity_counts(
    formatter: Callable[[Any], str], severity_counts: object
) -> None:
    output = formatter({"severity_counts": severity_counts})
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        for name in ("critical", "high", "medium", "low"):
            assert f"**{name.capitalize()}:** 0" in output


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("severity_counts", HOSTILE_SEVERITY_COUNTS)
def test_cve_formatters_render_hostile_severity_counts(
    formatter: Callable[[Any], str], severity_counts: dict[str, object]
) -> None:
    output = formatter({"severity_counts": severity_counts})
    assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Hostile ``ports`` values (iterated in Markdown).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ports", NON_LIST_PORTS)
def test_cve_formatters_tolerate_non_list_ports(
    formatter: Callable[[Any], str], ports: object
) -> None:
    output = formatter({"ports": ports})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ports", HOSTILE_PORTS_LISTS)
def test_cve_formatters_render_hostile_ports_lists(
    formatter: Callable[[Any], str], ports: list[object]
) -> None:
    output = formatter({"ports": ports})
    assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Hostile ``notes`` values (iterated in Markdown).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", NON_LIST_NOTES)
def test_cve_formatters_tolerate_non_list_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTE_LISTS)
def test_cve_formatters_render_hostile_notes_lists(
    formatter: Callable[[Any], str], notes: list[object]
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "## Notes" in output


# ---------------------------------------------------------------------------
# Well-formed regression.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("formatter", CVE_FORMATTERS, ids=_formatter_id)
def test_cve_formatters_still_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_cve_report_markdown:
        assert "ethscan CVE Report" in output
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output
        assert "served from cache" in output
    elif formatter is format_cve_report_csv:
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output
    elif formatter is format_cve_report_json:
        assert "example.com" in output
        assert "CVE-2016-6210" in output
        assert "CVE-2021-41773" in output