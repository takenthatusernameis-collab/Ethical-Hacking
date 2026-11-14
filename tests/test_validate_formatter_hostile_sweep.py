"""Permanent sweep test: hostile validate formatter inputs are rendered, never raised.

Covers ``format_validate_report_json``, ``format_validate_report_csv`` and
``format_validate_report_markdown`` against hostile top-level shapes and hostile
nested values in the key report sections (``ports``, ``cidrs``, ``summary``,
``notes``). Every shape yields a string and never raises, and the JSON formatter
always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.validate import (
    format_validate_report_csv,
    format_validate_report_json,
    format_validate_report_markdown,
)

VALIDATE_FORMATTERS: list[Callable[[Any], str]] = [
    format_validate_report_json,
    format_validate_report_markdown,
    format_validate_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("ports", "x"),
    ("ports", None),
    ("ports", []),
    ("ports", {}),
    ("ports", 1),
    ("ports", 1.5),
    ("cidrs", "x"),
    ("cidrs", None),
    ("cidrs", []),
    ("cidrs", {}),
    ("cidrs", 1),
    ("cidrs", 1.5),
    ("summary", "x"),
    ("summary", None),
    ("summary", []),
    ("summary", {}),
    ("summary", 1),
    ("summary", 1.5),
    ("notes", "x"),
    ("notes", None),
    ("notes", []),
    ("notes", {}),
    ("notes", 1),
    ("notes", 1.5),
]

HOSTILE_PORT_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"spec": None},
    {"spec": []},
    {"spec": {}},
    {"spec": 1.5},
    {"valid": None},
    {"valid": "x"},
    {"valid": []},
    {"valid": {}},
    {"ports": None},
    {"ports": "x"},
    {"ports": {}},
    {"ports": [None, "x", {}, []]},
    {"count": None},
    {"count": "x"},
    {"count": []},
    {"count": {}},
    {"error": None},
    {"error": []},
    {"error": {}},
    {"error": 1.5},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_CIDR_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"spec": None},
    {"spec": []},
    {"spec": {}},
    {"valid": None},
    {"valid": "x"},
    {"valid": []},
    {"canonical": None},
    {"canonical": []},
    {"canonical": {}},
    {"network": None},
    {"network": "x"},
    {"network": 1},
    {"network": {"canonical": None}},
    {"network": {"network_address": None}},
    {"network": {"broadcast_address": None}},
    {"network": {"first_host": None}},
    {"network": {"last_host": None}},
    {"network": {"total_addresses": None}},
    {"network": {"addresses": None}},
    {"network": {"addresses": "x"}},
    {"network": {"addresses": [None, "x", {}]}},
    {"error": None},
    {"error": []},
    {"error": {}},
    [None, 1, {}, "not-a-dict", []],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-dict", []],
]

WELL_FORMED = {
    "ports": [
        {
            "spec": "80,443,8000-9002",
            "valid": True,
            "ports": [80, 443, 8000, 8001, 8002],
            "count": 5,
            "error": None,
        }
    ],
    "cidrs": [
        {
            "spec": "192.168.1.0/30",
            "valid": True,
            "canonical": "192.168.1.0/30",
            "network": {
                "network_address": "192.168.1.0",
                "netmask": "255.255.255.252",
                "broadcast_address": "192.168.1.3",
                "wildcard_mask": "0.0.0.3",
                "first_host": "192.168.1.1",
                "last_host": "192.168.1.2",
                "usable_host_count": 2,
                "total_addresses": 4,
                "prefixlen": 30,
                "is_private": True,
                "addresses": [
                    "192.168.1.0",
                    "192.168.1.1",
                    "192.168.1.2",
                    "192.168.1.3",
                ],
            },
            "error": None,
        }
    ],
    "summary": {
        "ports_specified": 1,
        "ports_valid": 1,
        "ports_total": 5,
        "cidrs_specified": 1,
        "cidrs_valid": 1,
        "all_valid": True,
    },
    "notes": [
        "Validated 1 port specification(s).",
        "Validated 1 CIDR specification(s).",
        "All specifications valid.",
    ],
}

WELL_FORMED_MINIMAL = {
    "ports": [],
    "cidrs": [],
    "summary": {
        "ports_specified": 0,
        "ports_valid": 0,
        "ports_total": 0,
        "cidrs_specified": 0,
        "cidrs_valid": 0,
        "all_valid": False,
    },
    "notes": [
        "No port or CIDR specifications provided; nothing to validate.",
        "One or more specifications were invalid; see error fields.",
    ],
}