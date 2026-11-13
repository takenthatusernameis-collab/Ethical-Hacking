"""Permanent sweep test: hostile vuln formatter inputs are rendered, never raised.

Covers ``format_vuln_report_markdown``, ``format_vuln_report_csv`` and
``format_vuln_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``severity_counts``, ``findings``,
``notes``, ``recursive_hosts_scanned``, ``recursive_findings``). Every shape
yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.vuln import (
    format_vuln_report_csv,
    format_vuln_report_json,
    format_vuln_report_markdown,
)

VULN_FORMATTERS: list[Callable[[Any], str]] = [
    format_vuln_report_markdown,
    format_vuln_report_csv,
    format_vuln_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_SEVERITY_COUNTS: list[object] = [
    None,
    1,
    "x",
    [1, 2],
    {"critical": "x", "high": None, 1: 2},
]

HOSTILE_FINDINGS: list[object] = [
    None,
    1,
    "x",
    True,
    [None, 1, "x", True, 3.14],
    [{"id": None, "kind": 1, "title": [1], "description": {"x": 1}, "product": None, "version": [], "port": "p"}],
    [{"kind": "service", "product": None, "version": None, "port": None}],
    [{"kind": "protocol", "protocol": None}],
    [{"kind": "cipher", "cipher": None}],
    [{"kind": "certificate", "key_size": None, "signature_algorithm": None}],
    [{"kind": "certificate", "key_size": 128, "signature_algorithm": "sha256"}],
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "ok"],
]

HOSTILE_RECURSIVE_HOSTS: list[object] = [None, 1, "x", [None, 1, "x"]]

HOSTILE_RECURSIVE_FINDINGS: list[object] = [
    None,
    1,
    "x",
    [None, 1, {"host": None, "depth": "x", "findings": None, "finding_count": "x", "severity_counts": None, "services_checked": None}],
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "timeout": 3.0,
    "ports": [80, 443],
    "services_checked": 2,
    "tls_checked": True,
    "certificate_checked": False,
    "severity_filter": None,
    "min_severity_filter": None,
    "findings": [
        {
            "id": "CVE-X",
            "kind": "service",
            "severity": "high",
            "product": "nginx",
            "version": "1.0",
            "port": 80,
            "title": "t",
            "description": "d",
        }
    ],
    "finding_count": 1,
    "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
    "notes": ["ok"],
    "recursive": False,
    "max_depth": 0,
    "recursive_hosts_scanned": [],
    "recursive_findings": [],
    "salt": False,
    "pepper": False,
    "algorithm": "sha256",
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_vuln_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_vuln_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("counts", HOSTILE_SEVERITY_COUNTS)
def test_vuln_formatters_tolerate_hostile_severity_counts(
    formatter: Callable[[Any], str], counts: object
) -> None:
    output = formatter({"severity_counts": counts})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDINGS)
def test_vuln_formatters_tolerate_hostile_findings(
    formatter: Callable[[Any], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_vuln_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("hosts", HOSTILE_RECURSIVE_HOSTS)
def test_vuln_formatters_tolerate_hostile_recursive_hosts(
    formatter: Callable[[Any], str], hosts: object
) -> None:
    output = formatter({"recursive": True, "recursive_hosts_scanned": hosts})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("rf", HOSTILE_RECURSIVE_FINDINGS)
def test_vuln_formatters_tolerate_hostile_recursive_findings(
    formatter: Callable[[Any], str], rf: object
) -> None:
    output = formatter({"recursive": True, "recursive_findings": rf})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", VULN_FORMATTERS, ids=_formatter_id)
def test_vuln_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_vuln_report_markdown:
        assert "example.com" in output
        assert "nginx 1.0" in output
        assert "CVE-X" in output
        assert "Severity Summary" in output
    elif formatter is format_vuln_report_csv:
        assert "CVE-X" in output
        assert "nginx" in output
        assert "id,type,severity,product,version,port,title,description" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["finding_count"] == 1
        assert len(parsed["findings"]) == 1


def test_vuln_formatters_render_recursive_well_formed() -> None:
    data = dict(
        WELL_FORMED,
        recursive=True,
        max_depth=2,
        recursive_hosts_scanned=["host2"],
        recursive_findings=[
            {
                "host": "host2",
                "depth": 1,
                "findings": [
                    {
                        "id": "CVE-Y",
                        "kind": "service",
                        "severity": "high",
                        "product": "nginx",
                        "version": "1.0",
                        "port": 80,
                        "title": "t",
                        "description": "d",
                    }
                ],
                "finding_count": 1,
                "severity_counts": {"high": 1},
                "services_checked": 1,
            }
        ],
    )
    output = format_vuln_report_markdown(cast(Any, data))
    assert "Recursive Scan Results" in output
    assert "host2" in output
    assert "CVE-Y" in output