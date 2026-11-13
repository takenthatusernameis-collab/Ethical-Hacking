"""Permanent sweep test: hostile Nmap formatter inputs are rendered, never raised.

Covers ``format_nmap_report_markdown``, ``format_nmap_report_csv`` and
``format_nmap_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``severity_counts``, ``services``,
``findings``, ``notes``). Every shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.nmap import (
    format_nmap_report_csv,
    format_nmap_report_json,
    format_nmap_report_markdown,
)

NMAP_FORMATTERS: list[Callable[[Any], str]] = [
    format_nmap_report_markdown,
    format_nmap_report_csv,
    format_nmap_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_SEVERITY_COUNTS: list[object] = [
    None,
    1,
    "x",
    [1, 2],
    {"critical": "x", "high": None, 1: 2},
]

HOSTILE_SERVICES: list[object] = [
    None,
    1,
    "x",
    True,
    [None, 1, "x", True, 3.14],
    [{"host": None, "hostnames": 1, "port": "p", "protocol": None, "service_name": True, "product": [1], "version": {"x": 1}, "extrainfo": None, "ostype": [], "banner": 1}],
]

HOSTILE_FINDINGS: list[object] = [
    None,
    1,
    "x",
    True,
    [None, 1, "x", True, 3.14],
    [{"id": None, "kind": 1, "title": [1], "description": {"x": 1}, "product": None, "version": [], "port": "p", "host": True, "hostnames": 1, "state": None, "service_name": [], "score": "x"}],
    [{"kind": "service", "product": None, "version": None, "port": None, "host": None}],
    [{"kind": "protocol", "protocol": None}],
    [{"kind": "cipher", "cipher": None}],
    [{"kind": "certificate", "key_size": None, "signature_algorithm": None}],
    [{"kind": "certificate", "key_size": "x"}],
    [{"kind": "certificate", "key_size": 128, "signature_algorithm": "sha256"}],
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "ok"],
]

WELL_FORMED = {
    "input_file": "in.xml",
    "hosts_scanned": 1,
    "total_ports_scanned": 1,
    "total_open_ports": 1,
    "services_detected": 1,
    "finding_count": 1,
    "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
    "services": [
        {
            "host": "h",
            "hostnames": ["n"],
            "port": 80,
            "protocol": "tcp",
            "service_name": "http",
            "product": "nginx",
            "version": "1.0",
            "extrainfo": "",
            "ostype": "",
            "banner": "nginx 1.0",
        }
    ],
    "findings": [
        {
            "id": "CVE-X",
            "kind": "service",
            "title": "t",
            "description": "d",
            "product": "nginx",
            "version": "1.0",
            "port": 80,
            "host": "h",
            "hostnames": ["n"],
            "state": "open",
            "service_name": "http",
            "score": 5.0,
        }
    ],
    "notes": ["ok"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_nmap_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_nmap_report_json:
        assert output == "{}"


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("counts", HOSTILE_SEVERITY_COUNTS)
def test_nmap_formatters_tolerate_hostile_severity_counts(
    formatter: Callable[[Any], str], counts: object
) -> None:
    output = formatter({"severity_counts": counts})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("services", HOSTILE_SERVICES)
def test_nmap_formatters_tolerate_hostile_services(
    formatter: Callable[[Any], str], services: object
) -> None:
    output = formatter({"services": services})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDINGS)
def test_nmap_formatters_tolerate_hostile_findings(
    formatter: Callable[[Any], str], findings: object
) -> None:
    output = formatter({"findings": findings})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_nmap_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", NMAP_FORMATTERS, ids=_formatter_id)
def test_nmap_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_nmap_report_markdown:
        assert "in.xml" in output
        assert "nginx 1.0" in output
        assert "CVE-X" in output
        assert "Severity Summary" in output
    elif formatter is format_nmap_report_csv:
        assert "CVE-X" in output
        assert "nginx" in output
        assert "host,addr,port,state,service,product,version,cve_id,severity,score,title" in output
    else:
        parsed = json.loads(output)
        assert parsed["input_file"] == "in.xml"
        assert parsed["finding_count"] == 1
        assert len(parsed["findings"]) == 1