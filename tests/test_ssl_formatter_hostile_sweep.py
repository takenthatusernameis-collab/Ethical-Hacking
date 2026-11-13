"""Permanent sweep test: hostile SSL formatter inputs are rendered, never raised.

Covers ``format_ssl_report_markdown``, ``format_ssl_report_csv`` and
``format_ssl_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``cert``, ``sans``, ``target``, ``host``,
``port``, ``timeout``, ``error``, ``chain_length``, ``valid``,
``days_remaining``, ``subject``, ``issuer``, ``not_before``, ``not_after``,
``signature_algorithm``, ``key_size``). Every shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.ssl import (
    format_ssl_report_csv,
    format_ssl_report_json,
    format_ssl_report_markdown,
)

SSL_FORMATTERS: list[Callable[[Any], str]] = [
    format_ssl_report_markdown,
    format_ssl_report_csv,
    format_ssl_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_CERT: list[object] = [
    None,
    1,
    "x",
    True,
    [None, 1],
    {"subject": None, "issuer": 1, "sans": "not-a-list", "not_before": None, "not_after": [], "signature_algorithm": {}, "key_size": "x"},
]

HOSTILE_SANS: list[object] = [
    None,
    1,
    "x",
    True,
    {"a": 1},
    [None, 1, True, 3.14, {"nested": True}],
]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", 1),
    ("host", None),
    ("port", "x"),
    ("timeout", [1]),
    ("error", {}),
    ("chain_length", "x"),
    ("valid", "y"),
    ("days_remaining", None),
]

HOSTILE_CERT_FIELDS: list[tuple[str, object]] = [
    ("subject", 1),
    ("issuer", []),
    ("not_before", {}),
    ("not_after", True),
    ("signature_algorithm", None),
    ("key_size", "x"),
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "port": 443,
    "timeout": 5.0,
    "error": None,
    "chain_length": 1,
    "cert": {
        "subject": "CN=example.com",
        "subject_dict": {"commonName": "example.com"},
        "issuer": "CN=Let's Encrypt",
        "issuer_dict": {"commonName": "Let's Encrypt"},
        "sans": ["example.com", "www.example.com"],
        "not_before": "Jan  1 00:00:00 2024 GMT",
        "not_after": "Dec 31 23:59:59 2024 GMT",
        "signature_algorithm": "sha256WithRSAEncryption",
        "key_size": 2048,
    },
    "valid": True,
    "days_remaining": 30,
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_ssl_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_ssl_report_json:
        # JSON formatter serializes any value directly; verify valid JSON
        json.loads(output)


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("cert", HOSTILE_CERT)
def test_ssl_formatters_tolerate_hostile_cert(
    formatter: Callable[[Any], str], cert: object
) -> None:
    output = formatter({"cert": cert})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("sans", HOSTILE_SANS)
def test_ssl_formatters_tolerate_hostile_sans(
    formatter: Callable[[Any], str], sans: object
) -> None:
    output = formatter({"cert": {"sans": sans}})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_ssl_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_CERT_FIELDS)
def test_ssl_formatters_tolerate_hostile_cert_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({"cert": {field: val}})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", SSL_FORMATTERS, ids=_formatter_id)
def test_ssl_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_ssl_report_markdown:
        assert "example.com" in output
        assert "Let's Encrypt" in output
        assert "sha256WithRSAEncryption" in output
        assert "2048" in output
        assert "Subject Alternative Names" in output
    elif formatter is format_ssl_report_csv:
        assert "example.com" in output
        assert "Let's Encrypt" in output
        assert "sha256WithRSAEncryption" in output
        assert "2048" in output
        assert "example.com;www.example.com" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "example.com"
        assert parsed["cert"]["subject"] == "CN=example.com"
        assert parsed["cert"]["sans"] == ["example.com", "www.example.com"]
        assert parsed["cert"]["key_size"] == 2048