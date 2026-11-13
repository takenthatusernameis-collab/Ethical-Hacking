"""Permanent sweep test: hostile per-key record shapes never raise in formatters.

Covers ``format_cidr_report_markdown`` and ``format_cidr_report_csv`` with the
hostile shapes enumerated in the handoff. The formatters must never raise; they
should render something reasonable (empty or stringified). The previously
unguarded ``diff.difference`` field (which crashed with ``TypeError: 'int'
object is not iterable`` when fed a non-list value) is now normalized via
``_normalize_difference``.
"""
from __future__ import annotations

import csv
import io
from typing import Any, cast

import pytest

from ethscan.cidr import (
    _normalize_difference,
    format_cidr_report_csv,
    format_cidr_report_json,
    format_cidr_report_markdown,
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
    [None, 1, "two", 3.0],
    [{"a": 1}, {"b": 2}],
)


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_cidr_report_markdown_hostile_difference(shape: object) -> None:
    data = {
        "cidr": "192.168.1.0/24",
        "ip_version": "IPv4",
        "network": {
            "network_address": "192.168.1.0",
            "netmask": "255.255.255.0",
            "broadcast_address": "192.168.1.255",
            "wildcard_mask": "0.0.0.255",
            "first_host": "192.168.1.1",
            "last_host": "192.168.1.254",
            "usable_host_count": 254,
            "total_addresses": 256,
            "prefixlen": 24,
            "is_private": True,
        },
        "diff": {
            "diff_cidr": "192.168.1.0/25",
            "difference": shape,
            "difference_network_count": 1,
            "total_diff_addresses": 128,
        },
    }
    md = format_cidr_report_markdown(cast(Any, data))
    assert isinstance(md, str)
    assert "ethscan CIDR Network Calculator Report" in md


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_cidr_report_csv_hostile_difference(shape: object) -> None:
    data = {
        "cidr": "192.168.1.0/24",
        "ip_version": "IPv4",
        "network": {
            "network_address": "192.168.1.0",
            "netmask": "255.255.255.0",
            "broadcast_address": "192.168.1.255",
            "wildcard_mask": "0.0.0.255",
            "first_host": "192.168.1.1",
            "last_host": "192.168.1.254",
            "usable_host_count": 254,
            "total_addresses": 256,
            "prefixlen": 24,
            "is_private": True,
        },
        "diff": {
            "diff_cidr": "192.168.1.0/25",
            "difference": shape,
            "difference_network_count": 1,
            "total_diff_addresses": 128,
        },
    }
    csv_text = format_cidr_report_csv(cast(Any, data))
    assert isinstance(csv_text, str)
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert reader[0][0] == "cidr"


@pytest.mark.parametrize("shape", RECORD_HOSTILE)
def test_format_cidr_report_json_hostile_difference(shape: object) -> None:
    import json

    data = {
        "cidr": "192.168.1.0/24",
        "ip_version": "IPv4",
        "network": {
            "network_address": "192.168.1.0",
            "netmask": "255.255.255.0",
            "broadcast_address": "192.168.1.255",
            "wildcard_mask": "0.0.0.255",
            "first_host": "192.168.1.1",
            "last_host": "192.168.1.254",
            "usable_host_count": 254,
            "total_addresses": 256,
            "prefixlen": 24,
            "is_private": True,
        },
        "diff": {
            "diff_cidr": "192.168.1.0/25",
            "difference": shape,
            "difference_network_count": 1,
            "total_diff_addresses": 128,
        },
    }
    parsed = json.loads(format_cidr_report_json(cast(Any, data)))
    assert isinstance(parsed, dict)


def test_normalize_difference_hostile_shapes() -> None:
    """Direct unit test for the normalization helper."""
    assert _normalize_difference(None) == []
    assert _normalize_difference(1) == []
    assert _normalize_difference(True) == []
    assert _normalize_difference(1.5) == []
    assert _normalize_difference("string") == []
    assert _normalize_difference(b"bytes") == []
    assert _normalize_difference([]) == []
    assert _normalize_difference([1, 2, 3]) == ["1", "2", "3"]
    assert _normalize_difference({"a": 1}) == []
    assert _normalize_difference((1, 2)) == ["1", "2"]
    assert _normalize_difference([None, 1, "two", 3.0]) == ["None", "1", "two", "3.0"]
    assert _normalize_difference([{"a": 1}, {"b": 2}]) == ["{'a': 1}", "{'b': 2}"]


def test_format_cidr_report_markdown_well_formed_preserved() -> None:
    """Well-formed difference lists render verbatim."""
    data = {
        "cidr": "192.168.1.0/24",
        "ip_version": "IPv4",
        "network": {
            "network_address": "192.168.1.0",
            "netmask": "255.255.255.0",
            "broadcast_address": "192.168.1.255",
            "wildcard_mask": "0.0.0.255",
            "first_host": "192.168.1.1",
            "last_host": "192.168.1.254",
            "usable_host_count": 254,
            "total_addresses": 256,
            "prefixlen": 24,
            "is_private": True,
        },
        "diff": {
            "diff_cidr": "192.168.1.0/25",
            "difference": ["192.168.1.128/25"],
            "difference_network_count": 1,
            "total_diff_addresses": 128,
        },
    }
    md = format_cidr_report_markdown(cast(Any, data))
    assert "192.168.1.128/25" in md
    assert "192.168.1.128 - 192.168.1.255" in md
    assert "128" in md


def test_format_cidr_report_csv_well_formed_preserved() -> None:
    """Well-formed difference lists render verbatim in CSV."""
    data = {
        "cidr": "192.168.1.0/24",
        "ip_version": "IPv4",
        "network": {
            "network_address": "192.168.1.0",
            "netmask": "255.255.255.0",
            "broadcast_address": "192.168.1.255",
            "wildcard_mask": "0.0.0.255",
            "first_host": "192.168.1.1",
            "last_host": "192.168.1.254",
            "usable_host_count": 254,
            "total_addresses": 256,
            "prefixlen": 24,
            "is_private": True,
        },
        "diff": {
            "diff_cidr": "192.168.1.0/25",
            "difference": ["192.168.1.128/25"],
            "difference_network_count": 1,
            "total_diff_addresses": 128,
        },
    }
    csv_text = format_cidr_report_csv(cast(Any, data))
    reader = list(csv.reader(io.StringIO(csv_text)))
    # diff_first and diff_last should be the CIDR string
    assert reader[1][13] == "192.168.1.128/25"  # diff_first
    assert reader[1][14] == "192.168.1.128/25"  # diff_last