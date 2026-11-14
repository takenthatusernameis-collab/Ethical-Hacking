"""Permanent sweep test: hostile jwt formatter inputs are rendered, never raised.

Covers ``format_jwt_report_markdown``, ``format_jwt_report_csv`` and
``format_jwt_report_json`` against hostile top-level shapes and hostile
nested values in the key report sections (``header``, ``claims``,
``standard_claims``, ``other_claims``, ``findings``). Every shape yields a
string and never raises, and the JSON formatter always emits parseable JSON.
"""
from __future__ import annotations

import json
from typing import Any, Callable, cast

import pytest

from ethscan.jwt import (
    format_jwt_report_csv,
    format_jwt_report_json,
    format_jwt_report_markdown,
)

JWT_FORMATTERS: list[Callable[[Any], str]] = [
    format_jwt_report_markdown,
    format_jwt_report_csv,
    format_jwt_report_json,
]

NON_MAPPING_TOP_LEVEL: list[object] = [None, 1, 0, True, "text", [1, 2], 3.14, b"bytes"]

HOSTILE_TOP_LEVEL_FIELDS: list[tuple[str, object]] = [
    ("valid_structure", "x"),
    ("valid_structure", None),
    ("valid_structure", []),
    ("segment_count", "x"),
    ("segment_count", None),
    ("segment_count", []),
    ("has_signature", "x"),
    ("has_signature", None),
    ("has_signature", []),
    ("token_length", "x"),
    ("token_length", None),
    ("token_length", []),
    ("algorithm", 1),
    ("algorithm", []),
    ("algorithm", {}),
    ("algorithm_type", 1),
    ("algorithm_type", []),
    ("token_type", 1),
    ("token_type", []),
    ("header", "x"),
    ("header", 1),
    ("header", [None, 1, {}]),
    ("claims", "x"),
    ("claims", 1),
    ("claims", [None, 1, {}]),
    ("standard_claims", "x"),
    ("standard_claims", 1),
    ("standard_claims", [None, 1, {}]),
    ("other_claims", "x"),
    ("other_claims", 1),
    ("other_claims", [None, 1, {}]),
    ("exp_status", 1),
    ("exp_status", []),
    ("nbf_status", 1),
    ("nbf_status", []),
    ("iat_status", 1),
    ("iat_status", []),
    ("findings", "x"),
    ("findings", 1),
    ("findings", {"a": 1}),
    ("finding_count", "x"),
    ("finding_count", None),
    ("finding_count", []),
    ("notes", "x"),
    ("notes", 1),
    ("notes", {"a": 1}),
    ("error", 1),
    ("error", []),
    ("error", {}),
]

HOSTILE_HEADER: list[object] = [
    None,
    1,
    "x",
    [],
    {"alg": None},
    {"alg": 1},
    {"alg": []},
    {"alg": {}},
    {"typ": 1},
    {"typ": []},
    {"kid": None},
    {"kid": []},
    {"unknown": "value"},
    {"custom": [1, None, {}]},
    {"nested": {"deep": "value"}},
]

HOSTILE_CLAIMS: list[object] = [
    None,
    1,
    "x",
    [],
    {"exp": "not a number"},
    {"exp": None},
    {"exp": []},
    {"exp": {}},
    {"exp": True},
    {"iat": "string"},
    {"nbf": "string"},
    {"iss": 123},
    {"sub": ["list"]},
    {"aud": 123},
    {"jti": {}},
    {"custom": object()},
    {"custom": set([1, 2, 3])},
    {"custom": b"bytes"},
    {"nested": {"deep": "value"}},
    {"exp": float("inf")},
    {"exp": float("-inf")},
    {"exp": float("nan")},
    {"iat": 1e30},
    {"nbf": -1e30},
]

HOSTILE_STANDARD_CLAIMS: list[object] = [
    None,
    1,
    "x",
    [],
    {"iss": None},
    {"exp": "x"},
    {"sub": []},
    {"aud": {}},
    {"jti": 123},
]

HOSTILE_OTHER_CLAIMS: list[object] = [
    None,
    1,
    "x",
    [],
    {"custom": None},
    {"custom": []},
    {"custom": {}},
    {"custom": [1, None, {}]},
    {"nested": {"deep": "value"}},
]

HOSTILE_FINDINGS: list[object] = [
    None,
    1,
    "x",
    "finding",
    True,
    3.14,
    [],
    [None, 1, "string", True, 3.14, {}, []],
    [{}, {"nested": "object"}, []],
    [object()],
    [b"bytes"],
    [set([1, 2])],
]

WELL_FORMED = {
    "valid_structure": True,
    "segment_count": 3,
    "has_signature": True,
    "token_length": 100,
    "algorithm": "HS256",
    "algorithm_type": "symmetric",
    "token_type": "JWT",
    "header": {"alg": "HS256", "typ": "JWT", "kid": "key-1"},
    "claims": {
        "iss": "https://example.com",
        "sub": "user123",
        "aud": ["api.example.com"],
        "exp": 1893456000,
        "iat": 1735689600,
        "nbf": 1735689600,
        "jti": "abc123",
        "custom_claim": "custom_value",
    },
    "standard_claims": {
        "iss": "https://example.com",
        "sub": "user123",
        "aud": ["api.example.com"],
        "exp": 1893456000,
        "iat": 1735689600,
        "nbf": 1735689600,
        "jti": "abc123",
    },
    "other_claims": {"custom_claim": "custom_value"},
    "exp_status": "valid",
    "nbf_status": "valid",
    "iat_status": "valid",
    "findings": ["Token uses symmetric algorithm (HS256)"],
    "finding_count": 1,
    "notes": [],
}

WELL_FORMED_MINIMAL = {
    "valid_structure": True,
    "segment_count": 2,
    "has_signature": False,
    "token_length": 50,
    "algorithm": "none",
    "algorithm_type": "none",
    "token_type": None,
    "header": {"alg": "none"},
    "claims": {"sub": "anonymous"},
    "standard_claims": {"sub": "anonymous"},
    "other_claims": {},
    "exp_status": None,
    "nbf_status": None,
    "iat_status": None,
    "findings": ["Unsigned token (alg=none): signature verification is impossible", "Token has no expiration (exp) claim"],
    "finding_count": 2,
    "notes": [],
}

WELL_FORMED_EXPIRED = {
    "valid_structure": True,
    "segment_count": 3,
    "has_signature": True,
    "token_length": 100,
    "algorithm": "RS256",
    "algorithm_type": "asymmetric",
    "token_type": "JWT",
    "header": {"alg": "RS256", "typ": "JWT"},
    "claims": {
        "iss": "https://example.com",
        "sub": "user123",
        "aud": "api.example.com",
        "exp": 1000000000,
        "iat": 900000000,
    },
    "standard_claims": {
        "iss": "https://example.com",
        "sub": "user123",
        "aud": "api.example.com",
        "exp": 1000000000,
        "iat": 900000000,
    },
    "other_claims": {},
    "exp_status": "expired",
    "nbf_status": None,
    "iat_status": "valid",
    "findings": ["Token is expired"],
    "finding_count": 1,
    "notes": [],
}


def _formatter_id(value: object) -> str:
    return getattr(value, "__name__", str(value))


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("bad", NON_MAPPING_TOP_LEVEL)
def test_jwt_formatters_tolerate_non_mapping_top_level(
    formatter: Callable[[Any], str], bad: object
) -> None:
    output = formatter(cast(Any, bad))
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("field,val", HOSTILE_TOP_LEVEL_FIELDS)
def test_jwt_formatters_tolerate_hostile_top_level_fields(
    formatter: Callable[[Any], str], field: str, val: object
) -> None:
    output = formatter({field: val})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("header", HOSTILE_HEADER)
def test_jwt_formatters_tolerate_hostile_header(
    formatter: Callable[[Any], str], header: object
) -> None:
    output = formatter({"valid_structure": True, "header": header})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("claims", HOSTILE_CLAIMS)
def test_jwt_formatters_tolerate_hostile_claims(
    formatter: Callable[[Any], str], claims: object
) -> None:
    output = formatter({"valid_structure": True, "claims": claims})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("standard_claims", HOSTILE_STANDARD_CLAIMS)
def test_jwt_formatters_tolerate_hostile_standard_claims(
    formatter: Callable[[Any], str], standard_claims: object
) -> None:
    output = formatter({"valid_structure": True, "standard_claims": standard_claims})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("other_claims", HOSTILE_OTHER_CLAIMS)
def test_jwt_formatters_tolerate_hostile_other_claims(
    formatter: Callable[[Any], str], other_claims: object
) -> None:
    output = formatter({"valid_structure": True, "other_claims": other_claims})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
@pytest.mark.parametrize("findings", HOSTILE_FINDINGS)
def test_jwt_formatters_tolerate_hostile_findings(
    formatter: Callable[[Any], str], findings: object
) -> None:
    output = formatter({"valid_structure": True, "findings": findings})
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
def test_jwt_formatters_tolerate_hostile_combined(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(
        {
            "valid_structure": "x",
            "segment_count": None,
            "has_signature": [],
            "token_length": {},
            "algorithm": 123,
            "algorithm_type": ["sym"],
            "token_type": ["JWT"],
            "header": {"alg": None, "typ": [], "kid": {}, "custom": [1, None]},
            "claims": {"exp": "x", "iat": [], "nbf": {}, "iss": 123, "custom": object()},
            "standard_claims": {"iss": None, "exp": "x"},
            "other_claims": {"custom": [None, {}]},
            "exp_status": "x",
            "nbf_status": [],
            "iat_status": {},
            "findings": [None, 1, {"nested": "obj"}, object()],
            "finding_count": "x",
            "notes": "x",
            "error": [],
        }
    )
    assert isinstance(output, str)
    if formatter is format_jwt_report_json:
        json.loads(output)


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
def test_jwt_formatters_render_well_formed(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED))
    assert isinstance(output, str)
    if formatter is format_jwt_report_markdown:
        assert "# ethscan JWT Inspection Report" in output
        assert "**Valid Structure:** Yes" in output
        assert "**Segments:** 3" in output
        assert "**Has Signature:** Yes" in output
        assert "**Algorithm:** HS256" in output
        assert "**Algorithm Type:** symmetric" in output
        assert "**Type:** JWT" in output
        assert "**Key ID:** key-1" in output
        assert "**Issuer (iss):** https://example.com" in output
        assert "**Subject (sub):** user123" in output
        assert "**Audience (aud):** [\"api.example.com\"]" in output
        assert "**JWT ID (jti):** abc123" in output
        assert "Expiration (exp)" in output
        assert "Issued At (iat)" in output
        assert "Not Before (nbf)" in output
        assert "## Other Claims" in output
        assert "custom_claim" in output
        assert "custom_value" in output
        assert "## Findings" in output
        assert "Token uses symmetric algorithm" in output
    elif formatter is format_jwt_report_csv:
        assert "field,value" in output
        assert "valid_structure,true" in output
        assert "segment_count,3" in output
        assert "algorithm,HS256" in output
        assert "standard_claim,value" in output
        assert "https://example.com" in output
        assert "other_claim,value" in output
        assert "custom_claim,custom_value" in output
        assert "finding" in output
        assert "Token uses symmetric algorithm" in output
    else:
        parsed = json.loads(output)
        assert parsed["valid_structure"] is True
        assert parsed["segment_count"] == 3
        assert parsed["algorithm"] == "HS256"
        assert parsed["header"]["alg"] == "HS256"
        assert parsed["claims"]["iss"] == "https://example.com"
        assert parsed["standard_claims"]["sub"] == "user123"
        assert parsed["other_claims"]["custom_claim"] == "custom_value"
        assert parsed["findings"] == ["Token uses symmetric algorithm (HS256)"]


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
def test_jwt_formatters_render_well_formed_minimal(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_MINIMAL))
    assert isinstance(output, str)
    if formatter is format_jwt_report_markdown:
        assert "# ethscan JWT Inspection Report" in output
        assert "**Valid Structure:** Yes" in output
        assert "**Segments:** 2" in output
        assert "**Has Signature:** No" in output
        assert "**Algorithm:** none" in output
        assert "**Algorithm Type:** none" in output
        assert "**Subject (sub):** anonymous" in output
        assert "## Findings" in output
        assert "Unsigned token (alg=none)" in output
        assert "Token has no expiration" in output
    elif formatter is format_jwt_report_csv:
        assert "field,value" in output
        assert "valid_structure,true" in output
        assert "segment_count,2" in output
        assert "algorithm,none" in output
        assert "standard_claim,value" in output
        assert "sub,anonymous" in output
        assert "finding" in output
        assert "Unsigned token" in output
    else:
        parsed = json.loads(output)
        assert parsed["valid_structure"] is True
        assert parsed["segment_count"] == 2
        assert parsed["algorithm"] == "none"
        assert parsed["claims"]["sub"] == "anonymous"
        assert "Token has no expiration" in parsed["findings"][1]


@pytest.mark.parametrize("formatter", JWT_FORMATTERS, ids=_formatter_id)
def test_jwt_formatters_render_well_formed_expired(
    formatter: Callable[[Any], str],
) -> None:
    output = formatter(cast(Any, WELL_FORMED_EXPIRED))
    assert isinstance(output, str)
    if formatter is format_jwt_report_markdown:
        assert "**Algorithm:** RS256" in output
        assert "**Algorithm Type:** asymmetric" in output
        assert "expired" in output.lower() or "expired" in output
        assert "Token is expired" in output
    elif formatter is format_jwt_report_csv:
        assert "algorithm,RS256" in output
        assert "finding" in output
        assert "expired" in output.lower()
    else:
        parsed = json.loads(output)
        assert parsed["algorithm"] == "RS256"
        assert parsed["exp_status"] == "expired"
        assert "Token is expired" in parsed["findings"]