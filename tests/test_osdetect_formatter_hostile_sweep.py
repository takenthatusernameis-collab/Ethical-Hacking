"""Permanent sweep test: hostile per-key probes shapes never raise in formatters.

Covers ``format_osdetect_report_markdown`` and ``format_osdetect_report_csv`` with
the hostile shapes for the ``probes`` field (which crashed with
``TypeError: 'int' object is not iterable`` when fed a non-list value).
"""
from __future__ import annotations

import csv
import io
from typing import Any, cast

import pytest

from ethscan.osdetect import (
    format_osdetect_report_csv,
    format_osdetect_report_json,
    format_osdetect_report_markdown,
)


PROBES_HOSTILE: tuple[object, ...] = (
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
    [{"port": 80, "probe_type": "SYN", "connected": True}],
)


@pytest.mark.parametrize("shape", PROBES_HOSTILE)
def test_format_osdetect_report_markdown_hostile_probes(shape: object) -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 5.0,
        "ports_probed": 0,
        "inferred_os": [],
        "os_matches": [],
        "inferred_os_count": 0,
        "banners_provided": False,
        "notes": [],
        "probes": shape,
    }
    md = format_osdetect_report_markdown(cast(Any, data))
    assert isinstance(md, str)
    assert "ethscan OS Detection Report" in md


@pytest.mark.parametrize("shape", PROBES_HOSTILE)
def test_format_osdetect_report_csv_hostile_probes(shape: object) -> None:
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 5.0,
        "ports_probed": 0,
        "inferred_os": [],
        "os_matches": [],
        "inferred_os_count": 0,
        "banners_provided": False,
        "notes": [],
        "probes": shape,
    }
    csv_text = format_osdetect_report_csv(cast(Any, data))
    assert isinstance(csv_text, str)
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert reader[0][0] == "target"


@pytest.mark.parametrize("shape", PROBES_HOSTILE)
def test_format_osdetect_report_json_hostile_probes(shape: object) -> None:
    import json

    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 5.0,
        "ports_probed": 0,
        "inferred_os": [],
        "os_matches": [],
        "inferred_os_count": 0,
        "banners_provided": False,
        "notes": [],
        "probes": shape,
    }
    parsed = json.loads(format_osdetect_report_json(cast(Any, data)))
    assert isinstance(parsed, dict)


def test_format_osdetect_report_markdown_well_formed_preserved() -> None:
    """Well-formed probe lists render verbatim."""
    entry = {
        "port": 80,
        "probe_type": "SYN",
        "connected": True,
        "response": "SYN-ACK",
        "flags_observed": "SYN-ACK",
        "error": None,
    }
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 5.0,
        "ports_probed": 1,
        "inferred_os": ["Linux"],
        "os_matches": ["Linux"],
        "inferred_os_count": 1,
        "banners_provided": False,
        "notes": [],
        "probes": [entry],
    }
    md = format_osdetect_report_markdown(cast(Any, data))
    assert "80" in md
    assert "SYN" in md
    assert "SYN-ACK" in md
    assert "Linux" in md


def test_format_osdetect_report_csv_well_formed_preserved() -> None:
    """Well-formed probe lists render verbatim in CSV."""
    entry = {
        "port": 80,
        "probe_type": "SYN",
        "connected": True,
        "response": "SYN-ACK",
        "flags_observed": "SYN-ACK",
        "error": None,
    }
    data = {
        "target": "example.com",
        "host": "example.com",
        "timeout": 5.0,
        "ports_probed": 1,
        "inferred_os": ["Linux"],
        "os_matches": ["Linux"],
        "inferred_os_count": 1,
        "banners_provided": False,
        "notes": [],
        "probes": [entry],
    }
    csv_text = format_osdetect_report_csv(cast(Any, data))
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert reader[0][0] == "target"
    # Find the data row (skip header and inferred_os rows)
    data_rows = [row for row in reader if row[3] == "SYN"]
    assert data_rows
    row = data_rows[0]
    assert row[0] == "example.com"
    assert row[2] == "80"
    assert row[3] == "SYN"
    assert row[4] == "true"
    assert row[5] == "SYN-ACK"