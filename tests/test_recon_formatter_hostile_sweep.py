"""Permanent sweep test: hostile recon formatter inputs are rendered, never raised.

Covers ``format_recon_report_markdown``, ``format_recon_report_csv`` and
``format_recon_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``modules_run``, ``notes``, ``subdomains``,
``dns``, ``whois``, ``geo``, ``trace`` and their nested structures). Every
shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.recon import (
    format_recon_report_csv,
    format_recon_report_json,
    format_recon_report_markdown,
)

RECON_FORMATTERS: list[Callable[[Any], str]] = [
    format_recon_report_markdown,
    format_recon_report_csv,
    format_recon_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", None),
    ("target", 1),
    ("domain", []),
    ("modules_run", "x"),
    ("modules_run", None),
    ("modules_run", [None, 1, {}]),
    ("notes", "x"),
    ("notes", None),
    ("notes", [None, {}, []]),
    ("subdomains", "x"),
    ("dns", "x"),
    ("whois", "x"),
    ("geo", "x"),
    ("trace", "x"),
]

HOSTILE_SUBDOMAINS: list[object] = [
    None,
    1,
    "x",
    {"resolved": "x"},
    {"resolved": [None, "x", 1, {"hostname": None, "ip": 1, "subdomain": []}]},
    {"subdomains_tested": "many", "resolved_count": None, "resolver": 1},
]

HOSTILE_DNS: list[object] = [
    None,
    1,
    "x",
    {"record_types_queried": "x", "records": "x", "dnspython_available": "yes"},
    {"records": {"A": "x", "MX": [None, 1], None: [1]}},
    {"records": [("A", ["1.2.3.4"])]},
]

HOSTILE_WHOIS: list[object] = [
    None,
    1,
    "x",
    {"parsed": "x", "server": None, "port": "x"},
    {
        "parsed": {
            "registrar": [],
            "creation_date": {},
            "expiration_date": 1,
            "registrant_org": None,
            "nameservers": "x",
            "status_codes": [None, 1, {}],
        }
    },
]

HOSTILE_GEO: list[object] = [
    None,
    1,
    "x",
    {"geolocation": "x"},
    {"geolocation": {"status": 1, "error": [], "lat": {}, "country": None}},
    {"geolocation": {"status": "fail", "error": "boom"}},
]

HOSTILE_TRACE: list[object] = [
    None,
    1,
    "x",
    {"hops": "x", "raw_socket_available": "x", "destination_reached": "y"},
    {
        "hops": [
            None,
            "x",
            {
                "hop": "x",
                "ip": [],
                "rtt_avg_ms": {},
                "rtt_ms": [],
                "response_type": 1,
                "reached_destination": "yes",
            },
        ]
    },
]

WELL_FORMED = {
    "target": "example.com",
    "domain": "example.com",
    "modules_run": ["subdomains", "dns", "whois", "geo", "trace"],
    "subdomains": {
        "subdomains_tested": 2,
        "resolved_count": 1,
        "resolver": None,
        "dnspython_available": False,
        "resolved": [
            {"subdomain": "www.example.com", "hostname": "www.example.com", "ip": "1.2.3.4"}
        ],
    },
    "dns": {
        "record_types_queried": ["A", "MX"],
        "dnspython_available": False,
        "records": {"A": ["1.2.3.4"], "MX": ["10 mail.example.com"]},
    },
    "whois": {
        "server": "whois.iana.org",
        "port": 43,
        "parsed": {
            "registrar": "Example Registrar",
            "creation_date": "2000-01-01",
            "expiration_date": "2030-01-01",
            "registrant_org": "Example Org",
            "nameservers": ["ns1.example.com"],
            "status_codes": ["clientTransferProhibited"],
        },
    },
    "geo": {
        "geolocation": {
            "status": "success",
            "query": "1.2.3.4",
            "country": "United States",
            "countryCode": "US",
            "regionName": "California",
            "city": "Los Angeles",
            "lat": 34.05,
            "lon": -118.24,
            "isp": "Example ISP",
            "org": "Example Org",
            "as": "AS12345 Example",
        }
    },
    "trace": {
        "port": 80,
        "max_hops": 30,
        "probes_per_hop": 3,
        "raw_socket_available": False,
        "destination_reached": True,
        "hops": [{"hop": 1, "ip": "10.0.0.1", "rtt_avg_ms": 1.2, "response_type": "icmp", "reached_destination": False}],
    },
    "notes": ["all good"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_recon_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_recon_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_recon_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("subdomains", HOSTILE_SUBDOMAINS)
def test_recon_formatters_tolerate_hostile_subdomains(
    formatter: Callable[[Any], str], subdomains: object
) -> None:
    output = formatter({"subdomains": subdomains})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("dns", HOSTILE_DNS)
def test_recon_formatters_tolerate_hostile_dns(
    formatter: Callable[[Any], str], dns: object
) -> None:
    output = formatter({"dns": dns})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("whois", HOSTILE_WHOIS)
def test_recon_formatters_tolerate_hostile_whois(
    formatter: Callable[[Any], str], whois: object
) -> None:
    output = formatter({"whois": whois})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("geo", HOSTILE_GEO)
def test_recon_formatters_tolerate_hostile_geo(
    formatter: Callable[[Any], str], geo: object
) -> None:
    output = formatter({"geo": geo})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("trace", HOSTILE_TRACE)
def test_recon_formatters_tolerate_hostile_trace(
    formatter: Callable[[Any], str], trace: object
) -> None:
    output = formatter({"trace": trace})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", RECON_FORMATTERS, ids=_formatter_id)
def test_recon_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_recon_report_markdown:
        assert "example.com" in output
        assert "Subdomain Enumeration" in output
        assert "DNS Record Enumeration" in output
        assert "WHOIS Lookup" in output
        assert "IP Geolocation" in output
        assert "TCP Traceroute" in output
        assert "www.example.com" in output
        assert "Example Registrar" in output
        assert "all good" in output
    elif formatter is format_recon_report_csv:
        assert "example.com" in output
        assert "subdomains" in output
        assert "dns" in output
        assert "whois" in output
        assert "geo" in output
        assert "trace" in output
        assert "all good" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["domain"] == "example.com"
        assert "subdomains" in parsed["modules_run"]
        assert parsed["dns"]["records"]["A"] == ["1.2.3.4"]
