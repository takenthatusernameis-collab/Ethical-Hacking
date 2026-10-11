"""Tests for the ethscan jwt module."""

import base64
import json
import time

from ethscan.jwt import (
    KNOWN_ALGORITHMS,
    LONG_LIVED_THRESHOLD_SECONDS,
    STANDARD_CLAIMS,
    format_jwt_report_json,
    format_jwt_report_markdown,
    parse_jwt,
    run_jwt,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_token(header: dict, payload: dict, with_sig: bool = True) -> str:
    token = (
        _b64url(json.dumps(header).encode())
        + "."
        + _b64url(json.dumps(payload).encode())
    )
    if with_sig:
        token += "." + _b64url(b"fake-signature-bytes")
    return token


NOW = 1_700_000_000.0  # 2023-11-14T22:13:20Z


def test_known_algorithms() -> None:
    assert KNOWN_ALGORITHMS["HS256"] == "symmetric"
    assert KNOWN_ALGORITHMS["RS256"] == "asymmetric"
    assert KNOWN_ALGORITHMS["none"] == "none"
    assert KNOWN_ALGORITHMS["EdDSA"] == "asymmetric"


def test_standard_claims_constant() -> None:
    assert "exp" in STANDARD_CLAIMS
    assert "sub" in STANDARD_CLAIMS


def test_b64url_decode_roundtrip() -> None:
    from ethscan.jwt import _b64url_decode

    raw = b'{"alg":"HS256"}'
    encoded = _b64url(raw)
    assert _b64url_decode(encoded) == raw


def test_b64url_decode_empty() -> None:
    from ethscan.jwt import _b64url_decode

    assert _b64url_decode("") is None


def test_b64url_decode_invalid() -> None:
    from ethscan.jwt import _b64url_decode

    assert _b64url_decode("!!!not-base64!!!") is None


def test_parse_jwt_three_part() -> None:
    token = _make_token({"alg": "HS256", "typ": "JWT"}, {"sub": "user1"})
    parsed = parse_jwt(token)
    assert parsed["valid_structure"] is True
    assert parsed["parts"] == 3
    assert parsed["header"] == {"alg": "HS256", "typ": "JWT"}
    assert parsed["payload"] == {"sub": "user1"}
    assert parsed["has_signature"] is True


def test_parse_jwt_two_part_unsigned() -> None:
    token = _make_token({"alg": "none"}, {"sub": "user1"}, with_sig=False)
    parsed = parse_jwt(token)
    assert parsed["valid_structure"] is True
    assert parsed["parts"] == 2
    assert parsed["has_signature"] is False


def test_parse_jwt_invalid_segment_count() -> None:
    parsed = parse_jwt("only-one-segment")
    assert parsed["valid_structure"] is False
    assert parsed["parts"] == 1


def test_parse_jwt_too_many_segments() -> None:
    parsed = parse_jwt("a.b.c.d")
    assert parsed["valid_structure"] is False
    assert parsed["parts"] == 4


def test_parse_jwt_empty() -> None:
    parsed = parse_jwt("")
    assert parsed["valid_structure"] is False


def test_parse_jwt_garbage_segments() -> None:
    parsed = parse_jwt("!!!.@@@.###")
    assert parsed["valid_structure"] is True
    assert parsed["header"] is None
    assert parsed["payload"] is None


def test_parse_jwt_non_object_segment() -> None:
    token = _b64url(b"[1,2,3]") + "." + _b64url(b"{}") + "." + _b64url(b"")
    parsed = parse_jwt(token)
    assert parsed["valid_structure"] is True
    assert parsed["header"] is None


def test_run_jwt_hs256_full_claims() -> None:
    token = _make_token(
        {"alg": "HS256", "typ": "JWT"},
        {
            "iss": "example.com",
            "sub": "user1",
            "aud": "api.example.com",
            "exp": NOW + 3600,
            "iat": NOW - 60,
            "jti": "abc-123",
        },
    )
    data = run_jwt(token, now=NOW)
    assert data["valid_structure"] is True
    assert data["algorithm"] == "HS256"
    assert data["algorithm_type"] == "symmetric"
    assert data["token_type"] == "JWT"
    assert data["has_signature"] is True
    assert data["standard_claims"]["iss"] == "example.com"
    assert data["standard_claims"]["sub"] == "user1"
    assert data["exp_status"] == "valid"
    assert data["iat_status"] == "valid"
    assert data["finding_count"] == 0
    assert data["findings"] == []


def test_run_jwt_none_algorithm() -> None:
    token = _make_token({"alg": "none", "typ": "JWT"}, {"sub": "user1"}, with_sig=False)
    data = run_jwt(token, now=NOW)
    assert data["algorithm"] == "none"
    assert data["algorithm_type"] == "none"
    assert data["has_signature"] is False
    findings = data["findings"]
    assert any("alg=none" in f for f in findings)
    assert any("no signature segment" in f for f in findings)


def test_run_jwt_expired() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"exp": NOW - 10, "iat": NOW - 7200},
    )
    data = run_jwt(token, now=NOW)
    assert data["exp_status"] == "expired"
    assert any("expired" in f.lower() for f in data["findings"])


def test_run_jwt_missing_exp() -> None:
    token = _make_token({"alg": "HS256"}, {"sub": "user1"})
    data = run_jwt(token, now=NOW)
    assert any("expiration" in f.lower() for f in data["findings"])


def test_run_jwt_not_yet_valid() -> None:
    token = _make_token(
        {"alg": "RS256"},
        {"nbf": NOW + 3600, "exp": NOW + 7200},
    )
    data = run_jwt(token, now=NOW)
    assert data["nbf_status"] == "not-yet-valid"
    assert any("not yet valid" in f.lower() for f in data["findings"])


def test_run_jwt_iat_in_future() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"iat": NOW + 3600, "exp": NOW + 7200},
    )
    data = run_jwt(token, now=NOW)
    assert data["iat_status"] == "not-yet-valid"
    assert any("issued-at" in f.lower() for f in data["findings"])


def test_run_jwt_long_lived() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"iat": NOW, "exp": NOW + LONG_LIVED_THRESHOLD_SECONDS + 60},
    )
    data = run_jwt(token, now=NOW)
    assert any("long-lived" in f.lower() for f in data["findings"])


def test_run_jwt_unknown_algorithm() -> None:
    token = _make_token({"alg": "XYZ999"}, {"sub": "user1"})
    data = run_jwt(token, now=NOW)
    assert data["algorithm_type"] == "unknown"
    assert any("unknown algorithm" in f.lower() for f in data["findings"])


def test_run_jwt_missing_alg() -> None:
    token = _make_token({"typ": "JWT"}, {"sub": "user1"})
    data = run_jwt(token, now=NOW)
    assert data["algorithm"] is None
    assert any("no alg claim" in f.lower() for f in data["findings"])


def test_run_jwt_invalid_structure() -> None:
    data = run_jwt("not-a-jwt", now=NOW)
    assert data["valid_structure"] is False
    assert data["segment_count"] == 1
    assert data["finding_count"] == 1
    assert "error" in data


def test_run_jwt_undecodable_segments() -> None:
    data = run_jwt("!!!.@@@.###", now=NOW)
    assert data["valid_structure"] is True
    assert data["header"] is None
    assert data["claims"] is None
    assert any("header" in f.lower() for f in data["findings"])
    assert any("payload" in f.lower() for f in data["findings"])


def test_run_jwt_other_claims() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"sub": "user1", "exp": NOW + 60, "custom_role": "admin", "scope": ["read", "write"]},
    )
    data = run_jwt(token, now=NOW)
    assert data["other_claims"]["custom_role"] == "admin"
    assert data["other_claims"]["scope"] == ["read", "write"]
    assert "custom_role" not in data["standard_claims"]


def test_run_jwt_kid_header() -> None:
    token = _make_token(
        {"alg": "RS256", "kid": "key-2023", "typ": "JWT"},
        {"sub": "user1", "exp": NOW + 60},
    )
    data = run_jwt(token, now=NOW)
    assert data["header"]["kid"] == "key-2023"
    assert data["algorithm_type"] == "asymmetric"


def test_format_jwt_report_json() -> None:
    token = _make_token(
        {"alg": "HS256", "typ": "JWT"},
        {"iss": "example.com", "sub": "user1", "exp": NOW + 3600},
    )
    data = run_jwt(token, now=NOW)
    output = format_jwt_report_json(data)
    parsed = json.loads(output)
    assert parsed["valid_structure"] is True
    assert parsed["algorithm"] == "HS256"
    assert parsed["claims"]["sub"] == "user1"
    assert "example.com" in output


def test_format_jwt_report_markdown() -> None:
    token = _make_token(
        {"alg": "HS256", "typ": "JWT", "kid": "key-1"},
        {
            "iss": "example.com",
            "sub": "user1",
            "aud": "api",
            "exp": NOW + 3600,
            "iat": NOW - 60,
            "jti": "abc",
            "role": "admin",
        },
    )
    data = run_jwt(token, now=NOW)
    output = format_jwt_report_markdown(data)
    assert "# ethscan JWT Inspection Report" in output
    assert "## Header" in output
    assert "**Algorithm:** HS256" in output
    assert "**Algorithm Type:** symmetric" in output
    assert "**Key ID:** key-1" in output
    assert "## Claims" in output
    assert "**Issuer (iss):** example.com" in output
    assert "**Subject (sub):** user1" in output
    assert "**Audience (aud):** api" in output
    assert "**JWT ID (jti):** abc" in output
    assert "(valid)" in output
    assert "## Other Claims" in output
    assert "role" in output
    assert "admin" in output
    assert "## Findings" in output
    assert "No issues detected" in output


def test_format_jwt_report_markdown_invalid() -> None:
    data = run_jwt("garbage", now=NOW)
    output = format_jwt_report_markdown(data)
    assert "# ethscan JWT Inspection Report" in output
    assert "**Valid Structure:** No" in output
    assert "Invalid JWT structure" in output


def test_format_jwt_report_markdown_findings_listed() -> None:
    token = _make_token({"alg": "none"}, {"sub": "user1"}, with_sig=False)
    data = run_jwt(token, now=NOW)
    output = format_jwt_report_markdown(data)
    assert "alg=none" in output
    assert "unsigned token" in output.lower()


def test_format_jwt_report_markdown_pipe_escape() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"sub": "user1", "exp": NOW + 60, "note": "a|b|c"},
    )
    data = run_jwt(token, now=NOW)
    output = format_jwt_report_markdown(data)
    assert "a\\|b\\|c" in output


def test_format_jwt_report_json_invalid_structure() -> None:
    data = run_jwt("x.y.z.w", now=NOW)
    output = format_jwt_report_json(data)
    parsed = json.loads(output)
    assert parsed["valid_structure"] is False


def test_run_jwt_default_now() -> None:
    token = _make_token(
        {"alg": "HS256"},
        {"exp": int(time.time()) + 3600},
    )
    data = run_jwt(token)
    assert data["exp_status"] == "valid"
