"""Permanent sweep test: hostile wifi formatter inputs are rendered, never raised.

Covers ``format_wifi_report_json``, ``format_wifi_report_markdown`` and
``format_wifi_report_csv`` against hostile top-level shapes and hostile
nested values in key report sections (``interfaces``, ``access_points``,
``notes``). Every shape yields a string and never raises, and the JSON formatter
always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.wifi import (
    format_wifi_report_csv,
    format_wifi_report_json,
    format_wifi_report_markdown,
)

WIFI_FORMATTERS: list[Callable[[Any], str]] = [
    format_wifi_report_json,
    format_wifi_report_markdown,
    format_wifi_report_csv,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("platform", []),
    ("platform", {}),
    ("platform", 1),
    ("platform", None),
    ("platform_supported", "yes"),
    ("platform_supported", []),
    ("platform_supported", {}),
    ("platform_supported", 1),
    ("interfaces", "x"),
    ("interfaces", None),
    ("interfaces", {}),
    ("interfaces", 1),
    ("interfaces", 1.5),
    ("access_points", "x"),
    ("access_points", None),
    ("access_points", {}),
    ("access_points", 1),
    ("access_points", 1.5),
    ("notes", "x"),
    ("notes", None),
    ("notes", {}),
    ("notes", 1),
    ("notes", 1.5),
]

HOSTILE_INTERFACE_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"interface": []},
    {"interface": {}},
    {"interface": 1},
    {"interface": None},
    {"status": "x"},
    {"status": None},
    {"status": []},
    {"status": {}},
    {"link_quality": "x"},
    {"link_quality": None},
    {"link_quality": []},
    {"link_quality": {}},
    {"signal_level": "x"},
    {"signal_level": None},
    {"signal_level": []},
    {"signal_level": {}},
    {"noise_level": "x"},
    {"noise_level": None},
    {"noise_level": []},
    {"noise_level": {}},
]

HOSTILE_ACCESS_POINT_ENTRY: list[object] = [
    None,
    1,
    "x",
    {},
    {"bssid": []},
    {"bssid": {}},
    {"bssid": 1},
    {"bssid": None},
    {"ssid": []},
    {"ssid": {}},
    {"ssid": 1},
    {"ssid": None},
    {"ssid": ""},
    {"channel": "x"},
    {"channel": None},
    {"channel": []},
    {"channel": {}},
    {"frequency": "x"},
    {"frequency": None},
    {"frequency": []},
    {"frequency": {}},
    {"frequency": float("nan")},
    {"encryption": []},
    {"encryption": {}},
    {"encryption": 1},
    {"encryption": None},
    {"signal_dbm": "x"},
    {"signal_dbm": None},
    {"signal_dbm": []},
    {"signal_dbm": {}},
    {"quality": []},
    {"quality": {}},
    {"quality": 1},
    {"quality": None},
    {"interface": []},
    {"interface": {}},
    {"interface": 1},
]

HOSTILE_NOTES: list[object] = [
    [None],
    [1],
    [{}],
    [[]],
    [1.5],
    [b"bytes"],
]

HOSTILE_LIST: list[object] = [
    None,
    1,
    "x",
    {},
    [None, 1, {}, "not-a-dict", []],
]

WELL_FORMED = {
    "platform": "Linux",
    "platform_supported": True,
    "interfaces": [
        {
            "interface": "wlan0",
            "status": 0,
            "link_quality": 45.0,
            "signal_level": -45.0,
            "noise_level": -95.0,
        }
    ],
    "access_points": [
        {
            "interface": "wlan0",
            "bssid": "00:11:22:33:44:55",
            "ssid": "TestNet",
            "channel": 6,
            "frequency": 2.437,
            "encryption": "wpa2",
            "signal_dbm": -60,
            "quality": "50/70",
        },
        {
            "interface": "wlan0",
            "bssid": "AA:BB:CC:DD:EE:FF",
            "ssid": "",
            "channel": None,
            "frequency": None,
            "encryption": "open",
            "signal_dbm": None,
            "quality": None,
        },
    ],
    "notes": ["No scan results for interface 'wlan1' (tools may be unavailable or require root)."],
}

WELL_FORMED_MINIMAL = {
    "platform": "Darwin",
    "platform_supported": False,
    "interfaces": [],
    "access_points": [],
    "notes": ["Platform not supported: Wi-Fi scanning only implemented for Linux."],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_wifi_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_wifi_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_INTERFACE_ENTRY)
def test_wifi_formatters_tolerate_hostile_interface_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"interfaces": [entry]})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("entry", HOSTILE_ACCESS_POINT_ENTRY)
def test_wifi_formatters_tolerate_hostile_access_point_entries(
    formatter: Callable[[Any], str], entry: object
) -> None:
    output = formatter({"access_points": [entry]})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_wifi_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_wifi_formatters_tolerate_hostile_interfaces_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"interfaces": lst})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("lst", HOSTILE_LIST)
def test_wifi_formatters_tolerate_hostile_access_points_lists(
    formatter: Callable[[Any], str], lst: object
) -> None:
    output = formatter({"access_points": lst})
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
def test_wifi_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "platform": [],
            "platform_supported": "x",
            "interfaces": [None, 1, {"interface": []}, "not-a-dict"],
            "access_points": [None, {"ssid": {}}, {"frequency": "x"}, 1],
            "notes": [None, {}, []],
        }
    )
    assert isinstance(output, str)
    if formatter is format_wifi_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
def test_wifi_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_wifi_report_markdown:
        assert "# Wi-Fi Reconnaissance Report" in output
        assert "## Platform" in output
        assert "## Wireless Interfaces" in output
        assert "## Access Points" in output
        assert "wlan0" in output
        assert "00:11:22:33:44:55" in output
        assert "TestNet" in output
        assert "<hidden>" in output
        assert "## Notes" in output
    elif formatter is format_wifi_report_csv:
        assert "platform" in output
        assert "wlan0" in output
        assert "00:11:22:33:44:55" in output
        assert "TestNet" in output
        assert "<hidden>" in output
        assert "note" in output
    else:
        parsed = json.loads(output)
        assert parsed["platform"] == "Linux"
        assert parsed["platform_supported"] is True
        assert len(parsed["interfaces"]) == 1
        assert len(parsed["access_points"]) == 2
        assert parsed["access_points"][0]["ssid"] == "TestNet"


@pytest.mark.parametrize("formatter", WIFI_FORMATTERS, ids=_formatter_id)
def test_wifi_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_wifi_report_markdown:
        assert "# Wi-Fi Reconnaissance Report" in output
        assert "## Platform" in output
        assert "*No wireless interfaces found.*" in output
        assert "*No access points discovered.*" in output
        assert "Platform not supported" in output
    elif formatter is format_wifi_report_csv:
        assert "platform" in output
        assert "Darwin" in output
        assert "false" in output
        assert "note" in output
    else:
        parsed = json.loads(output)
        assert parsed["platform"] == "Darwin"
        assert parsed["platform_supported"] is False
        assert parsed["interfaces"] == []
        assert parsed["access_points"] == []
