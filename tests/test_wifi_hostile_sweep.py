"""Hostile-shape sweep for wifi report formatters."""

from __future__ import annotations

import json

from ethscan import wifi

HOSTILE_TOP_LEVEL = (None, [], "x", 123, 1.5, True, b"bytes")


def test_wifi_formatters_never_raise_on_hostile_top_level() -> None:
    for bad in HOSTILE_TOP_LEVEL:
        json.loads(wifi.format_wifi_report_json(bad))
        md = wifi.format_wifi_report_markdown(bad)
        csv_text = wifi.format_wifi_report_csv(bad)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
        assert "# Wi-Fi Reconnaissance Report" in md


def test_wifi_formatters_hostile_nested_shapes_never_raise() -> None:
    cases = [
        {"interfaces": None},
        {"interfaces": 5},
        {"interfaces": "x"},
        {"access_points": None},
        {"access_points": "notalist"},
        {"access_points": 42},
        {"notes": None},
        {"notes": 42},
        {"notes": "x"},
        {"interfaces": [{"interface": "wlan0"}], "access_points": [{"ssid": "foo"}]},
    ]
    for data in cases:
        json.loads(wifi.format_wifi_report_json(data))
        md = wifi.format_wifi_report_markdown(data)
        csv_text = wifi.format_wifi_report_csv(data)
        assert isinstance(md, str)
        assert isinstance(csv_text, str)
