"""JWT (JSON Web Token) inspection for ethscan.

Decodes and analyzes JWT tokens without verifying the signature.
Stdlib only; fully offline.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import time
from typing import cast

KNOWN_ALGORITHMS = {
    "none": "none",
    "HS256": "symmetric",
    "HS384": "symmetric",
    "HS512": "symmetric",
    "RS256": "asymmetric",
    "RS384": "asymmetric",
    "RS512": "asymmetric",
    "ES256": "asymmetric",
    "ES384": "asymmetric",
    "ES512": "asymmetric",
    "PS256": "asymmetric",
    "PS384": "asymmetric",
    "PS512": "asymmetric",
    "EdDSA": "asymmetric",
}

STANDARD_CLAIMS = ("iss", "sub", "aud", "exp", "iat", "nbf", "jti")

LONG_LIVED_THRESHOLD_SECONDS = 365 * 24 * 3600  # 1 year


def _b64url_decode(segment: str) -> bytes | None:
    """Decode a base64url-encoded JWT segment."""
    if not segment:
        return None
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except (ValueError, TypeError):
        return None


def _decode_json_segment(segment: str) -> dict | None:
    """Decode a base64url-encoded JSON object segment."""
    raw = _b64url_decode(segment)
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def parse_jwt(token: str) -> dict[str, object]:
    """Parse a JWT into its segments without verifying the signature.

    Returns a dict with ``valid_structure``, ``parts``, ``header``,
    ``payload`` and ``has_signature`` keys.
    """
    token = token.strip()
    parts = token.split(".")
    if len(parts) not in (2, 3):
        return {
            "valid_structure": False,
            "parts": len(parts),
            "header": None,
            "payload": None,
            "has_signature": False,
        }
    return {
        "valid_structure": True,
        "parts": len(parts),
        "header": _decode_json_segment(parts[0]),
        "payload": _decode_json_segment(parts[1]),
        "has_signature": bool(parts[2]) if len(parts) == 3 else False,
    }


def _format_timestamp(timestamp: float) -> str:
    """Format a Unix timestamp as an ISO-8601 UTC string."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown tables."""
    return value.replace("|", "\\|")


def _format_value(value: object) -> str:
    """Render a claim value as a compact string."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def run_jwt(token: str, now: float | None = None) -> dict[str, object]:
    """Inspect a JWT (JSON Web Token) without verifying the signature.

    Args:
        token: The JWT string (two or three dot-separated segments).
        now: Current time override for deterministic testing.

    Returns:
        Structured results with header, claims, and security findings.
    """
    current_time = time.time() if now is None else now
    token = token.strip()
    parsed = parse_jwt(token)

    result: dict[str, object] = {
        "valid_structure": parsed["valid_structure"],
        "segment_count": parsed["parts"],
        "has_signature": parsed["has_signature"],
        "token_length": len(token),
        "algorithm": None,
        "algorithm_type": None,
        "token_type": None,
        "header": parsed["header"],
        "claims": parsed["payload"],
        "standard_claims": {},
        "other_claims": {},
        "exp_status": None,
        "nbf_status": None,
        "iat_status": None,
        "findings": [],
        "finding_count": 0,
        "notes": [],
    }

    findings: list[str] = []

    if not parsed["valid_structure"]:
        findings.append(
            "Invalid JWT structure: expected 2 or 3 dot-separated base64url segments"
        )
        result["error"] = "Invalid JWT structure"
        result["findings"] = findings
        result["finding_count"] = len(findings)
        return result

    header_raw = parsed["header"]
    payload_raw = parsed["payload"]
    header = header_raw if isinstance(header_raw, dict) else None
    payload = payload_raw if isinstance(payload_raw, dict) else None

    if header is None:
        findings.append("Could not decode header segment (invalid base64url or non-JSON)")
    if payload is None:
        findings.append("Could not decode payload segment (invalid base64url or non-JSON)")
    if not parsed["has_signature"]:
        findings.append("Token has no signature segment (unsigned token)")

    if header is not None:
        alg = header.get("alg")
        result["algorithm"] = alg
        result["token_type"] = header.get("typ")
        if alg == "none":
            result["algorithm_type"] = "none"
            findings.append("Unsigned token (alg=none): signature verification is impossible")
        elif alg in KNOWN_ALGORITHMS:
            result["algorithm_type"] = KNOWN_ALGORITHMS[cast(str, alg)]
        elif alg is None:
            findings.append("Header has no alg claim")
        else:
            result["algorithm_type"] = "unknown"
            findings.append(f"Unknown algorithm: {alg}")

    if payload is not None:
        standard_claims_result: dict[str, object] = result["standard_claims"]  # type: ignore[assignment]
        other_claims_result: dict[str, object] = result["other_claims"]  # type: ignore[assignment]
        for key in STANDARD_CLAIMS:
            if key in payload:
                standard_claims_result[key] = payload[key]
        for key, value in payload.items():
            if key not in STANDARD_CLAIMS:
                other_claims_result[key] = value

        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            result["exp_status"] = "expired" if exp < current_time else "valid"
            if exp < current_time:
                findings.append("Token is expired")
        else:
            findings.append("Token has no expiration (exp) claim")

        nbf = payload.get("nbf")
        if isinstance(nbf, (int, float)):
            result["nbf_status"] = "not-yet-valid" if nbf > current_time else "valid"
            if nbf > current_time:
                findings.append("Token is not yet valid (nbf is in the future)")

        iat = payload.get("iat")
        if isinstance(iat, (int, float)):
            result["iat_status"] = "not-yet-valid" if iat > current_time else "valid"
            if iat > current_time:
                findings.append("Issued-at (iat) is in the future")
            if isinstance(exp, (int, float)) and exp - iat > LONG_LIVED_THRESHOLD_SECONDS:
                findings.append("Long-lived token (lifetime exceeds 1 year)")

    result["findings"] = findings
    result["finding_count"] = len(findings)
    return result


def format_jwt_report_json(data: dict[str, object]) -> str:
    """Format JWT inspection results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_jwt_report_markdown(data: dict[str, object]) -> str:
    """Format JWT inspection results as Markdown."""
    lines = ["# ethscan JWT Inspection Report", ""]
    lines.append(f"- **Valid Structure:** {'Yes' if data.get('valid_structure') else 'No'}")
    lines.append(f"- **Segments:** {data.get('segment_count')}")
    lines.append(f"- **Has Signature:** {'Yes' if data.get('has_signature') else 'No'}")
    lines.append(f"- **Token Length:** {data.get('token_length')}")
    lines.append("")

    if not data.get("valid_structure"):
        lines.append(f"*Error: {data.get('error', 'unknown error')}*")
        lines.append("")
        lines.append("## Findings")
        findings_err = data.get("findings") or []
        if isinstance(findings_err, list):
            for finding in findings_err:
                if isinstance(finding, str):
                    lines.append(f"- {finding}")
        lines.append("")
        return "\n".join(lines)

    header_raw = data.get("header") or {}
    header = header_raw if isinstance(header_raw, dict) else {}
    lines.append("## Header")
    lines.append(f"- **Algorithm:** {header.get('alg', '-')}")
    lines.append(f"- **Algorithm Type:** {data.get('algorithm_type') or '-'}")
    if header.get("typ"):
        lines.append(f"- **Type:** {header['typ']}")
    if header.get("kid"):
        lines.append(f"- **Key ID:** {header['kid']}")
    header_others = {k: v for k, v in header.items() if k not in ("alg", "typ", "kid")}
    if header_others:
        lines.append("")
        lines.append("| Header Field | Value |")
        lines.append("|--------------|-------|")
        for key, value in sorted(header_others.items()):
            lines.append(f"| {_escape(str(key))} | {_escape(_format_value(value))} |")
    lines.append("")

    claims_raw = data.get("claims") or {}
    claims = claims_raw if isinstance(claims_raw, dict) else {}
    lines.append("## Claims")
    if "iss" in claims:
        lines.append(f"- **Issuer (iss):** {_escape(_format_value(claims['iss']))}")
    if "sub" in claims:
        lines.append(f"- **Subject (sub):** {_escape(_format_value(claims['sub']))}")
    if "aud" in claims:
        lines.append(f"- **Audience (aud):** {_escape(_format_value(claims['aud']))}")
    if "jti" in claims:
        lines.append(f"- **JWT ID (jti):** {_escape(_format_value(claims['jti']))}")
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        status = data.get("exp_status") or "valid"
        lines.append(f"- **Expiration (exp):** {_format_timestamp(exp)} ({status})")
    iat = claims.get("iat")
    if isinstance(iat, (int, float)):
        status = data.get("iat_status") or "valid"
        lines.append(f"- **Issued At (iat):** {_format_timestamp(iat)} ({status})")
    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)):
        status = data.get("nbf_status") or "valid"
        lines.append(f"- **Not Before (nbf):** {_format_timestamp(nbf)} ({status})")
    lines.append("")

    other_claims_raw = data.get("other_claims") or {}
    other_claims = other_claims_raw if isinstance(other_claims_raw, dict) else {}
    if other_claims:
        lines.append("## Other Claims")
        lines.append("| Claim | Value |")
        lines.append("|-------|-------|")
        for key, value in sorted(other_claims.items()):
            lines.append(f"| {_escape(str(key))} | {_escape(_format_value(value))} |")
        lines.append("")

    lines.append("## Findings")
    findings = data.get("findings") or []
    if findings and isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, str):
                lines.append(f"- {finding}")
    else:
        lines.append("- No issues detected")
    lines.append("")

    return "\n".join(lines)


def format_jwt_report_csv(data: dict[str, object]) -> str:
    """Format JWT inspection results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["field", "value"])
    writer.writerow(["valid_structure", "true" if data.get("valid_structure") else "false"])
    writer.writerow(["segment_count", data.get("segment_count", 0)])
    writer.writerow(["has_signature", "true" if data.get("has_signature") else "false"])
    writer.writerow(["token_length", data.get("token_length", 0)])
    writer.writerow(["algorithm", data.get("algorithm") or ""])
    writer.writerow(["algorithm_type", data.get("algorithm_type") or ""])
    writer.writerow(["token_type", data.get("token_type") or ""])

    if data.get("error"):
        writer.writerow(["error", data.get("error")])

    standard_claims_raw = data.get("standard_claims") or {}
    standard_claims = standard_claims_raw if isinstance(standard_claims_raw, dict) else {}
    if standard_claims:
        writer.writerow([])
        writer.writerow(["standard_claim", "value"])
        for key, value in sorted(standard_claims.items()):
            writer.writerow([key, value])

    other_claims_raw = data.get("other_claims") or {}
    other_claims = other_claims_raw if isinstance(other_claims_raw, dict) else {}
    if other_claims:
        writer.writerow([])
        writer.writerow(["other_claim", "value"])
        for key, value in sorted(other_claims.items()):
            writer.writerow([key, value])

    findings = data.get("findings") or []
    if findings and isinstance(findings, list):
        writer.writerow([])
        writer.writerow(["finding"])
        for finding in findings:
            if isinstance(finding, str):
                writer.writerow([finding])

    return output.getvalue().rstrip("\r\n")
