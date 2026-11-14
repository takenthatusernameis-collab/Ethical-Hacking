"""Permanent sweep test: hostile radix formatter inputs are rendered, never raised.

Covers ``format_radix_report_markdown``, ``format_radix_report_csv`` and
``format_radix_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``radix_tree``, ``contains``,
``diff``). Every shape yields a string and never raises, and the JSON
formatter always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.radix import (
    format_radix_report_csv,
    format_radix_report_json,
    format_radix_report_markdown,
)

RADIX_FORMATTERS: list[Callable[[Any], str]] = [
    format_radix_report_markdown,
    format_radix_report_csv,
    format_radix_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("cidrs", None),
    ("cidrs", 1),
    ("cidrs", "x"),
    ("cidrs", [None, 1, {}]),
    ("network_count", "x"),
    ("network_count", None),
    ("merged_network_count", "x"),
    ("merged_network_count", []),
    ("merged", "x"),
    ("merged", None),
    ("merged", [1, None, {}]),
    ("total_input_addresses", "x"),
    ("total_merged_addresses", "x"),
    ("compression_ratio", "x"),
    ("merge_enabled", "yes"),
    ("max_depth", "x"),
    ("radix_tree", "x"),
    ("radix_tree", None),
    ("radix_tree", [1]),
    ("contains", "x"),
    ("contains", None),
    ("contains", [1]),
    ("diff", "x"),
    ("diff", None),
    ("diff", [1]),
]

HOSTILE_RADIX_TREE: list[object] = [
    None,
    1,
    "x",
    [],
    {},
    {"prefix": None},
    {"prefix": 1},
    {"prefix": []},
    {"networks": None},
    {"networks": "x"},
    {"networks": [1, {}, []]},
    {"children": None},
    {"children": "x"},
    {"children": [1]},
    {"children": [{"node": 1}]},
    {"children": [{"side": 1, "node": {"prefix": "10.0.0.0/8"}}]},
    {
        "prefix": "10.0.0.0/8",
        "start_address": [],
        "end_address": {},
        "total_addresses": "x",
        "networks": [None],
        "children": [{"side": "left", "node": None}],
    },
]

HOSTILE_CONTAINS: list[object] = [
    None,
    1,
    "x",
    {},
    {"ip": None},
    {"ip": []},
    {"in_network": "yes"},
    {"matched_network": []},
    {"ip": "1.2.3.4", "in_network": None, "matched_network": 1},
]

HOSTILE_DIFF: list[object] = [
    None,
    1,
    "x",
    {},
    {"diff_network_count": "x"},
    {"diff_merged_network_count": "x"},
    {"difference_network_count": "x"},
    {"total_diff_addresses": "x"},
    {"diff_cidrs": None},
    {"diff_cidrs": 5},
    {"diff_cidrs": "x"},
    {"diff_cidrs": [None, 1, {}]},
    {"difference": None},
    {"difference": "x"},
    {"difference": [1]},
    {"difference": [None, "not-a-cidr", "10.0.0.0/8"]},
]

WELL_FORMED = {
    "cidrs": ["10.0.0.0/8", "10.0.1.0/24"],
    "network_count": 2,
    "merged_network_count": 1,
    "merged": ["10.0.0.0/8"],
    "total_input_addresses": 500,
    "total_merged_addresses": 256,
    "compression_ratio": 0.5,
    "merge_enabled": True,
    "max_depth": 3,
    "radix_tree": {
        "prefix": "10.0.0.0/8",
        "start_address": "10.0.0.0",
        "end_address": "10.255.255.255",
        "total_addresses": 16777216,
        "networks": ["10.0.0.0/8"],
        "children": [
            {
                "side": "left",
                "node": {
                    "prefix": "10.0.0.0/9",
                    "networks": [],
                    "children": [],
                },
            }
        ],
    },
    "contains": {
        "ip": "10.0.0.1",
        "in_network": True,
        "matched_network": "10.0.0.0/8",
    },
    "diff": {
        "diff_cidrs": ["10.0.0.0/9"],
        "diff_network_count": 1,
        "diff_merged_network_count": 1,
        "diff_merged": ["10.0.0.0/8"],
        "difference": ["10.0.0.0/9"],
        "difference_network_count": 1,
        "total_diff_addresses": 8192,
    },
}

WELL_FORMED_MINIMAL = {
    "cidrs": ["10.0.0.0/8"],
    "network_count": 1,
    "merged_network_count": 1,
    "merged": ["10.0.0.0/8"],
    "total_input_addresses": 256,
    "total_merged_addresses": 256,
    "compression_ratio": 1.0,
    "merge_enabled": False,
    "max_depth": 1,
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_radix_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_radix_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("radix_tree", HOSTILE_RADIX_TREE)
def test_radix_formatters_tolerate_hostile_radix_tree(
    formatter: Callable[[Any], str], radix_tree: object
) -> None:
    output = formatter({"cidrs": ["10.0.0.0/8"], "radix_tree": radix_tree})
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("contains", HOSTILE_CONTAINS)
def test_radix_formatters_tolerate_hostile_contains(
    formatter: Callable[[Any], str], contains: object
) -> None:
    output = formatter({"cidrs": ["10.0.0.0/8"], "contains": contains})
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("diff", HOSTILE_DIFF)
def test_radix_formatters_tolerate_hostile_diff(
    formatter: Callable[[Any], str], diff: object
) -> None:
    output = formatter({"cidrs": ["10.0.0.0/8"], "diff": diff})
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
def test_radix_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "cidrs": [None, {}],
            "network_count": "x",
            "merged_network_count": None,
            "merged": [1, "not-a-cidr", "10.0.0.0/8"],
            "total_input_addresses": {},
            "total_merged_addresses": [],
            "compression_ratio": "high",
            "merge_enabled": "yes",
            "max_depth": "deep",
            "radix_tree": {
                "prefix": [],
                "networks": [None],
                "children": [1, {"node": 1, "side": []}],
            },
            "contains": {"ip": [], "in_network": [], "matched_network": []},
            "diff": {
                "diff_network_count": "x",
                "diff_cidrs": 5,
                "difference": [None, {}],
            },
        }
    )
    assert isinstance(output, str)
    if formatter is format_radix_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
def test_radix_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_radix_report_markdown:
        assert "# ethscan Radix Tree Report" in output
        assert "**Networks Provided:** 2" in output
        assert "**Merged Networks:** 1" in output
        assert "**Total Input Addresses:** 500" in output
        assert "**Total Merged Addresses:** 256" in output
        assert "**Compression Ratio:** 0.5" in output
        assert "**Merge Enabled:** True" in output
        assert "## Merged Networks" in output
        assert "10.0.0.0/8" in output
        assert "## Radix Tree" in output
        assert "10.0.0.0/8" in output
        assert "10.0.0.0/9" in output
        assert "## Membership Test" in output
        assert "**IP Tested:** 10.0.0.1" in output
        assert "**In Network:** Yes" in output
        assert "**Matched Network:** 10.0.0.0/8" in output
        assert "## Set Difference (In First, Not In Second)" in output
        assert "**Difference Networks:** 1" in output
    elif formatter is format_radix_report_csv:
        assert "original_cidr,merged_cidr,compression_ratio,diff_cidr" in output
        assert "10.0.0.0/8" in output
        assert "10.0.1.0/24" in output
    else:
        parsed = json.loads(output)
        assert parsed["cidrs"] == ["10.0.0.0/8", "10.0.1.0/24"]
        assert parsed["network_count"] == 2
        assert parsed["merged"] == ["10.0.0.0/8"]
        assert parsed["radix_tree"]["prefix"] == "10.0.0.0/8"
        assert parsed["contains"]["ip"] == "10.0.0.1"
        assert parsed["diff"]["difference"] == ["10.0.0.0/9"]


@pytest.mark.parametrize("formatter", RADIX_FORMATTERS, ids=_formatter_id)
def test_radix_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_radix_report_markdown:
        assert "# ethscan Radix Tree Report" in output
        assert "**Networks Provided:** 1" in output
        assert "**Merge Enabled:** False" in output
        assert "## Merged Networks" in output
        assert "10.0.0.0/8" in output
    elif formatter is format_radix_report_csv:
        assert "original_cidr,merged_cidr,compression_ratio" in output
        assert "10.0.0.0/8" in output
        assert "diff_cidr" not in output
    else:
        parsed = json.loads(output)
        assert parsed["cidrs"] == ["10.0.0.0/8"]
        assert parsed["network_count"] == 1
        assert "radix_tree" not in parsed
