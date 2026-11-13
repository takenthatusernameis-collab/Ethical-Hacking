"""Permanent sweep test: hostile TLS formatter inputs are rendered, never raised.

Covers ``format_tls_report_markdown``, ``format_tls_report_csv`` and
``format_tls_report_json`` against hostile top-level shapes and hostile
nested values in key report fields (``target``, ``host``, ``port``,
``versions_tested``, ``ciphers_tested``, ``supported_versions``,
``supported_cipher_count``, ``notes``, ``versions`` and ``ciphers``).
Every shape yields a string and never raises.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.tls import (
    format_tls_report_csv,
    format_tls_report_json,
    format_tls_report_markdown,
)

TLS_FORMATTERS: list[Callable[[Any], str]] = [
    format_tls_report_markdown,
    format_tls_report_csv,
    format_tls_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14]

HOSTILE_VERSIONS: list[object] = [
    None,
    "x",
    1,
    {"a": 1},
    [None, 1, True, 3.14],
    [
        None,
        1,
        "x",
        {
            "version": None,
            "supported": "y",
            "negotiated_cipher": [],
            "negotiated_protocol": {},
            "error": [1],
        },
    ],
]

HOSTILE_CIPHERS: list[object] = [
    None,
    "x",
    1,
    {"a": 1},
    [None, 1, True, 3.14],
    [
        None,
        1,
        "x",
        {
            "cipher": None,
            "supported": 1,
            "negotiated_version": {},
            "error": [1],
        },
    ],
]

HOSTILE_NOTES: list[object] = [
    None,
    "x",
    1,
    {"a": 1},
    ["ok", 1, None, ["nested"]],
    ["\n", "|", "x" * 10000],
]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("target", 1),
    ("host", None),
    ("port", "x"),
    ("versions_tested", [1]),
    ("ciphers_tested", {}),
    ("supported_versions", "not-a-list"),
    ("supported_cipher_count", []),
    ("notes", {}),
]

WELL_FORMED = {
    "target": "example.com",
    "host": "example.com",
    "port": 443,
    "timeout": 5.0,
    "versions_tested": 2,
    "ciphers_tested": 1,
    "versions": [
        {
            "version": "TLSv1.2",
            "supported": True,
            "negotiated_cipher": "TLS_AES_128_GCM_SHA256",
            "negotiated_protocol": "TLSv1.2",
            "error": None,
        },
        {
            "version": "TLSv1.3",
            "supported": False,
            "negotiated_cipher": "",
            "negotiated_protocol": "",
            "error": "handshake failed",
        },
    ],
    "ciphers": [
        {
            "cipher": "TLS_AES_128_GCM_SHA256",
            "supported": True,
            "negotiated_version": "TLSv1.3",
            "error": None,
        },
    ],
    "supported_versions": ["TLSv1.2"],
    "supported_ciphers": ["TLS_AES_128_GCM_SHA256"],
    "supported_version_count": 1,
    "supported_cipher_count": 1,
    "notes": ["Obsolete protocol version supported: TLSv1.0"],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_tls_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_tls_report_json:
        # JSON formatter serializes any value directly; verify valid JSON
        json.loads(output)


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_tls_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("versions", HOSTILE_VERSIONS)
def test_tls_formatters_tolerate_hostile_versions(
    formatter: Callable[[Any], str], versions: object
) -> None:
    output = formatter({"versions": versions})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("ciphers", HOSTILE_CIPHERS)
def test_tls_formatters_tolerate_hostile_ciphers(
    formatter: Callable[[Any], str], ciphers: object
) -> None:
    output = formatter({"ciphers": ciphers})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("notes", HOSTILE_NOTES)
def test_tls_formatters_tolerate_hostile_notes(
    formatter: Callable[[Any], str], notes: object
) -> None:
    output = formatter({"notes": notes})
    assert isinstance(output, str)


@pytest.mark.parametrize("formatter", TLS_FORMATTERS, ids=_formatter_id)
def test_tls_formatters_render_well_formed(
    formatter: Callable[[Any], str]
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_tls_report_markdown:
        assert "example.com" in output
        assert "TLSv1.2" in output
        assert "TLS_AES_128_GCM_SHA256" in output
        assert "Obsolete protocol version supported" in output
    elif formatter is format_tls_report_csv:
        assert "example.com" in output
        assert "TLSv1.2" in output
        assert "TLS_AES_128_GCM_SHA256" in output
        assert "finding" in output
    else:
        parsed = json.loads(output)
        assert parsed["target"] == "example.com"
        assert parsed["host"] == "example.com"
        assert parsed["supported_versions"] == ["TLSv1.2"]
        assert parsed["notes"] == ["Obsolete protocol version supported: TLSv1.0"]