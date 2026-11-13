"""Permanent sweep test: hostile WHOIS formatter inputs are rendered, never raised.

Covers ``format_whois_report_markdown`` and ``format_whois_report_csv`` against
hostile ``parsed`` values (non-dict scalars, lists of non-dict elements),
hostile ``parsed.nameservers`` / ``parsed.status_codes`` (non-list/tuple
scalars, lists with non-string elements), and hostile ``recursive_hops``
(non-list/tuple scalars, lists of non-dict elements). Every shape yields a
string and never raises.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from ethscan.whois import (
    format_whois_report_csv,
    format_whois_report_markdown,
)

WHOIS_FORMATTERS: list[Callable[[dict[str, Any]], str]] = [
    format_whois_report_markdown,
    format_whois_report_csv,
]


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


NON_ITERABLE_SCALARS: list[object] = [None, 1, 0, True, 3.14, "string", {"x": 1}]

HOSTILE_LISTS: list[list[object]] = [
    [None],
    [1],
    ["ok", None, 1, 2.5, ["nested"]],
]


@pytest.mark.parametrize("formatter", WHOIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("parsed", NON_ITERABLE_SCALARS + HOSTILE_LISTS)
def test_whois_formatters_tolerate_non_dict_parsed(
    formatter: Callable[[dict[str, Any]], str], parsed: object
) -> None:
    output = formatter({"parsed": parsed})
    assert isinstance(output, str)
    assert "Example Registrar" not in output


@pytest.mark.parametrize("formatter", WHOIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("nameservers", NON_ITERABLE_SCALARS + HOSTILE_LISTS)
def test_whois_formatters_tolerate_hostile_nameservers(
    formatter: Callable[[dict[str, Any]], str], nameservers: object
) -> None:
    output = formatter({"parsed": {"nameservers": nameservers}})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WHOIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("status_codes", NON_ITERABLE_SCALARS + HOSTILE_LISTS)
def test_whois_formatters_tolerate_hostile_status_codes(
    formatter: Callable[[dict[str, Any]], str], status_codes: object
) -> None:
    output = formatter({"parsed": {"status_codes": status_codes}})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WHOIS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("hops", NON_ITERABLE_SCALARS + HOSTILE_LISTS)
def test_whois_formatters_tolerate_hostile_recursive_hops(
    formatter: Callable[[dict[str, Any]], str], hops: object
) -> None:
    output = formatter({"recursive": True, "recursive_hops": hops})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", WHOIS_FORMATTERS, ids=_formatter_id)
def test_whois_formatters_still_render_well_formed_fields(
    formatter: Callable[[dict[str, Any]], str]
) -> None:
    output = formatter({
        "parsed": {
            "registrar": "Example Registrar",
            "nameservers": ["ns1.example.com", "ns2.example.com"],
            "status_codes": ["clientTransferProhibited"],
        },
        "recursive": True,
        "recursive_hops": [
            {
                "depth": 1,
                "server": "whois.registrar.example",
                "port": 43,
                "parsed": {"registrar": "Example Registrar"},
                "referral_server": "whois.registrar.example",
                "error": None,
            },
        ],
    })
    assert isinstance(output, str)
    assert "Example Registrar" in output
    assert "ns1.example.com" in output
    assert "clientTransferProhibited" in output