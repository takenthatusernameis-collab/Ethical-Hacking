"""Permanent sweep test: hostile geo formatter inputs are rendered, never raised.

Covers ``format_geo_report_markdown``, ``format_geo_report_csv`` and
``format_geo_report_json`` against hostile top-level shapes and hostile
values for ``geolocation``, ``hops``, and ``notes``. Every shape yields a
string and never raises. The geo formatters already normalize hostile
payloads (``_normalize_geo`` / ``_normalize_hops``), so this is regression
coverage pinning that behavior.
"""
from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from ethscan.geo import (
    format_geo_report_csv,
    format_geo_report_json,
    format_geo_report_markdown,
)

GEO_FORMATTERS: list[Callable[[Any], str]] = [
    format_geo_report_markdown,
    format_geo_report_csv,
    format_geo_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_GEOLOCATION: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    [1, 2],
    {"a": 1},
    {"status": None},
    {"status": "fail", "error": 1},
    {"query": None, "country": ["nested"]},
    {"cached": {"nested": True}},
    {"offline_fallback": "yes"},
]

HOSTILE_HOPS: list[object] = [
    None,
    1,
    0,
    True,
    "x",
    3.14,
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, ["x"], "ok"],
    [{"not": "a dict"}, ["also", "not"]],
    [
        {
            "hop": 1,
            "ip": "8.8.8.8",
            "host": "dns.google",
            "response_type": "reply",
            "rtt_avg_ms": 1.5,
            "geolocation": {"country": "United States", "city": "Mountain View"},
        },
        {"ip": None, "geolocation": None},
        {"ip": 1, "host": "x", "response_type": None, "rtt_avg_ms": "y"},
    ],
]

HOSTILE_NOTES: list[object] = [
    None,
    1,
    0,
    True,
    "note",
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}, "cached"],
]

WELL_FORMED = {
    "target": "8.8.8.8",
    "host": "8.8.8.8",
    "ip": "8.8.8.8",
    "timeout": 5.0,
    "use_cache": True,
    "offline_fallback": True,
    "recursive": False,
    "max_depth": 30,
    "geolocation": {
        "status": "success",
        "query": "8.8.8.8",
        "country": "United States",
        "countryCode": "US",
        "region": "CA",
        "regionName": "California",
        "city": "Mountain View",
        "zip": "94035",
        "lat": 37.4056,
        "lon": -122.0775,
        "timezone": "America/Los_Angeles",
        "isp": "Google LLC",
        "org": "Google Public DNS",
        "as": "AS15169 Google LLC",
        "reverse": "dns.google",
        "cached": False,
    },
    "hops": [],
    "notes": ["Result served from cache"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", GEO_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_geo_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", GEO_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("geolocation", HOSTILE_GEOLOCATION)
def test_geo_formatters_tolerate_hostile_geolocation(
    formatter: Callable[[Any], str], geolocation: object
) -> None:
    output = formatter({"geolocation": geolocation})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", GEO_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("hops", HOSTILE_HOPS)
def test_geo_formatters_tolerate_hostile_hops(
    formatter: Callable[[Any], str], hops: object
) -> None:
    output = formatter({"hops": hops})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", GEO_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_geo_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", GEO_FORMATTERS, ids=_formatter_id)
def test_geo_formatters_render_well_formed(formatter: Callable[[Any], str]) -> None:
    output = formatter(WELL_FORMED)
    assert isinstance(output, str)
    if formatter is format_geo_report_markdown:
        assert "# ethscan IP Geolocation Report" in output
        assert "8.8.8.8" in output
        assert "United States" in output
        assert "Mountain View" in output
    elif formatter is format_geo_report_csv:
        assert "target,ip,country" in output
        assert "United States" in output
    else:
        import json

        parsed = json.loads(output)
        assert parsed["geolocation"]["country"] == "United States"
