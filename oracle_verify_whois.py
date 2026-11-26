#!/usr/bin/env python3
"""Independent oracle verification for ethscan.whois pure parsers.

This script verifies the pure parser functions in ethscan.whois against
stdlib oracles (re) over a hostile input matrix.

Functions verified:
- parse_whois
- extract_referral_server

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import random
import re
import sys

from ethscan.whois import (
    extract_referral_server,
    parse_whois,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only (re-implements the spec from scratch)
# ──────────────────────────────────────────────────────────────────────────────

# The value must sit on the same line as its label: [ \t]* (not \s*)
# keeps the match from spilling across a newline and capturing the
# next line's leading label.
ORACLE_PATTERNS = {
    "registrar": [
        r"(?<!Sponsoring )Registrar:[ \t]*(.+)",
        r"Registrar Name:[ \t]*(.+)",
        r"Sponsoring Registrar:[ \t]*(.+)",
    ],
    "creation_date": [
        r"Creation Date:[ \t]*(.+)",
        r"Created:[ \t]*(.+)",
        r"Registration Date:[ \t]*(.+)",
        r"Domain Registration Date:[ \t]*(.+)",
    ],
    "expiration_date": [
        r"Expiration Date:[ \t]*(.+)",
        r"Expiry Date:[ \t]*(.+)",
        r"Registry Expiry Date:[ \t]*(.+)",
    ],
    "registrant_org": [
        r"Registrant Organization:[ \t]*(.+)",
        r"Registrant Org:[ \t]*(.+)",
        r"Organization:[ \t]*(.+)",
    ],
}

ORACLE_REFERRAL_PATTERNS = [
    r"Registrar WHOIS Server:[ \t]*(\S+)",
    r"WHOIS Server:[ \t]*(\S+)",
    r"Referral Server:[ \t]*(\S+)",
    r"Refer:[ \t]*(\S+)",
    r"Registrar URL:[ \t]*whois://(\S+)",
]


def oracle_parse_whois(raw: str) -> dict[str, object]:
    """Oracle for parse_whois using stdlib only."""
    result: dict[str, object] = {
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "nameservers": [],
        "registrant_org": None,
        "status_codes": [],
        "raw": raw,
    }

    for field, field_patterns in ORACLE_PATTERNS.items():
        for pattern in field_patterns:
            match = re.search(pattern, raw, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
                break

    nameserver_matches = re.findall(
        r"Name Server:[ \t]*(\S+)", raw, re.IGNORECASE
    )
    if nameserver_matches:
        result["nameservers"] = sorted({ns.strip().rstrip(".") for ns in nameserver_matches})

    status_matches = re.findall(
        r"Status:[ \t]*(\S+)", raw, re.IGNORECASE
    )
    if status_matches:
        result["status_codes"] = sorted({status.strip() for status in status_matches})

    return result


def oracle_extract_referral_server(raw: str) -> str | None:
    """Oracle for extract_referral_server using stdlib only."""
    candidates = []
    for idx, pattern in enumerate(ORACLE_REFERRAL_PATTERNS):
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            candidates.append((match.start(), idx, match))
    candidates.sort()
    for _pos, _idx, match in candidates:
        server = match.group(1).strip().rstrip(".")
        if server.lower().startswith("whois://"):
            server = server[len("whois://"):]
        server = server.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        hostname = server.split(":", 1)[0].lower()
        if server and hostname != "whois.iana.org":
            return server.lower()
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_hostile_whois_raw() -> list[str]:
    """Generate a comprehensive matrix of hostile WHOIS raw responses."""
    raw_list = []

    # Empty/whitespace
    raw_list.extend(["", "   ", "\t\n", " \t \n "])

    # Valid single fields
    raw_list.extend([
        "Registrar: Example Registrar, Inc.\n",
        "Creation Date: 2020-01-15T10:30:00Z\n",
        "Expiration Date: 2025-01-15T10:30:00Z\n",
        "Registrant Organization: Example Corp\n",
        "Name Server: ns1.example.com\n",
        "Name Server: ns2.example.com\n",
        "Status: clientTransferProhibited\n",
        "Status: clientUpdateProhibited\n",
    ])

    # Multiple fields
    raw_list.extend([
        "Registrar: Example Registrar, Inc.\nCreation Date: 2020-01-15T10:30:00Z\nExpiration Date: 2025-01-15T10:30:00Z\nRegistrant Organization: Example Corp\nName Server: ns1.example.com\nName Server: ns2.example.com\nStatus: clientTransferProhibited\nStatus: clientUpdateProhibited\n",
    ])

    # Case insensitivity
    raw_list.extend([
        "registrar: test registrar\nCREATION DATE: 2020-01-01\n",
        "Registrar: Test Registrar\ncreation date: 2020-01-01\n",
    ])

    # Priority order tests (Registrar > Registrar Name > Sponsoring Registrar)
    raw_list.extend([
        "Sponsoring Registrar: Registrar A\nRegistrar Name: Registrar B\n",
        "Sponsoring Registrar: Spons Registrar LLC\nRegistrar: Real Registrar Inc\n",
        "Sponsoring Registrar: Spons Registrar LLC\n",
    ])

    # Empty same-line values (must not cross lines)
    raw_list.extend([
        "Creation Date: \nRegistrar: Example Inc\n",
        "Registrar: \nCreation Date: 2020-01-01\n",
        "Name Server: \nStatus: ok\n",
        "Status: \nRegistrar: Example\n",
    ])

    # Whitespace stripping
    raw_list.extend([
        "Registrar:   Example Registrar, Inc.   \n",
        "Registrar:   \n",
    ])

    # Multiple nameservers with duplicates and trailing dots
    raw_list.extend([
        "Name Server: NS1.EXAMPLE.COM\nName Server: ns2.example.com.\nName Server: NS1.EXAMPLE.COM\n",
    ])

    # Multiple status codes with duplicates
    raw_list.extend([
        "Status: clientTransferProhibited\nStatus: clientUpdateProhibited\nStatus: clientTransferProhibited\n",
    ])

    # Special characters in values
    raw_list.extend([
        'Registrar: "Test, Registrar" Inc.\n',
    ])

    # Newlines in values (should capture up to newline)
    raw_list.extend([
        "Registrar: Test Registrar\nExtra line\n",
    ])

    # Tab characters
    raw_list.extend([
        "Registrar:\tTest Registrar\t\n",
    ])

    # Referral server patterns
    raw_list.extend([
        "Registrar WHOIS Server: whois.example.com\n",
        "WHOIS Server: whois.registrar.net\n",
        "Referral Server: whois.test.org\n",
        "Refer: whois.example.com\n",
        "Registrar URL: whois://whois.example.com\n",
        "registrar whois server: whois.example.com\n",
        "whois server: whois.example.com\n",
        "Registrar WHOIS Server: whois.example.com.\n",
        "Refer: whois.example.com.\n",
        "Registrar WHOIS Server: WHOIS.EXAMPLE.COM\n",
        "Refer: whois://whois.example.com\n",
        "Referral Server: whois://whois.example.com.\n",
        "WHOIS Server: WHOIS://WHOIS.EXAMPLE.COM\n",
        "Registrar WHOIS Server:\twhois://whois.first.com.\n",
        "Refer: whois://whois.iana.org\n",
        "Refer: whois://whois.example.com/path/to/server\n",
        "Refer: whois://whois.example.com?query=1\n",
        "Registrar URL: whois://whois.example.com/path\n",
        "WHOIS Server: whois://whois.example.com:43/\n",
        "Refer: whois://whois.iana.org:43\n",
        "Refer: whois://whois.iana.org:43/path\n",
        "Registrar WHOIS Server: whois.iana.org:43\n",
        "WHOIS Server: whois.iana.org:43\n",
        "Referral Server: WHOIS.IANA.ORG:43\n",
        "Refer: whois.iana.org:43\n",
    ])

    # First match wins
    raw_list.extend([
        "Registrar WHOIS Server: whois.first.com\nWHOIS Server: whois.second.com\n",
    ])

    # No match
    raw_list.extend([
        "Some other text without referral\n",
        "   \n",
    ])

    # Extra whitespace
    raw_list.extend([
        "Registrar WHOIS Server:   whois.example.com   \n",
    ])

    # Empty value on label line must not capture next line
    raw_list.extend([
        "Registrar WHOIS Server: \nWHOIS Server: whois.other.com\n",
        "Registrar WHOIS Server:\nRefer: whois.other.com\n",
        "Refer:\nwhois.other.com\n",
    ])

    # Very long inputs
    long_value = "a" * 1000
    raw_list.extend([
        f"Registrar: {long_value}\n",
        f"Creation Date: {long_value}\n",
    ])

    # Non-ASCII
    raw_list.extend([
        "Registrar: 日本語レジストラ\n",
        "Creation Date: 2020-01-01\n",
    ])

    # Mixed case
    raw_list.extend([
        "REGISTRAR: TEST REGISTRAR\n",
        "creation date: 2020-01-01\n",
        "Name Server: NS1.EXAMPLE.COM\n",
        "STATUS: OK\n",
    ])

    # Control characters
    controls = ["\x00", "\x01", "\x09", "\x0a", "\x0d", "\x1f", "\x7f"]
    for c in controls:
        raw_list.extend([
            f"Registrar: Test{c}Registrar\n",
            f"Creation Date: 2020-01-01{c}\n",
        ])

    # Random noise
    raw_list.extend([
        "random garbage without any matching patterns",
        "Not a WHOIS response at all",
        "HTTP/1.1 200 OK",
        "SSH-2.0-OpenSSH_8.9",
    ])

    return raw_list


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_parse_whois() -> list[tuple[str, dict, dict]]:
    """Verify parse_whois against oracle.

    Returns list of mismatches: (raw, our_result, oracle_result)
    """
    mismatches = []
    raw_inputs = generate_hostile_whois_raw()

    # Add random combinations for broader coverage
    rng = random.Random(20261126)
    fields = [
        "Registrar: {}\n",
        "Creation Date: {}\n",
        "Expiration Date: {}\n",
        "Registrant Organization: {}\n",
        "Name Server: {}\n",
        "Status: {}\n",
    ]
    values = [
        "example.com", "test registrar", "2020-01-01", "2025-01-01",
        "Example Corp", "ns1.example.com", "clientTransferProhibited",
        "a" * 100, "日本語", "test\x00value", "value with spaces",
    ]

    for _ in range(2000):
        num_fields = rng.randint(1, 6)
        selected_fields = rng.sample(fields, num_fields)
        raw = "".join(f.format(rng.choice(values)) for f in selected_fields)
        raw_inputs.append(raw)

    for raw in raw_inputs:
        try:
            our_result = parse_whois(raw)
        except Exception as e:
            mismatches.append((raw, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_parse_whois(raw)

        # Compare key fields
        key_fields = ["registrar", "creation_date", "expiration_date", "registrant_org", "nameservers", "status_codes"]
        for field in key_fields:
            if our_result.get(field) != oracle_result.get(field):
                mismatches.append((raw, dict(our_result), dict(oracle_result)))
                break

    return mismatches


def verify_extract_referral_server() -> list[tuple[str, str | None, str | None]]:
    """Verify extract_referral_server against oracle.

    Returns list of mismatches: (raw, our_result, oracle_result)
    """
    mismatches = []
    raw_inputs = generate_hostile_whois_raw()

    # Add random referral combinations
    rng = random.Random(20261126 + 1)
    referral_patterns = [
        "Registrar WHOIS Server: {}\n",
        "WHOIS Server: {}\n",
        "Referral Server: {}\n",
        "Refer: {}\n",
        "Registrar URL: whois://{}\n",
    ]
    referral_values = [
        "whois.example.com",
        "whois.registrar.net",
        "whois.test.org",
        "whois.example.com.",
        "WHOIS.EXAMPLE.COM",
        "whois://whois.example.com",
        "whois://whois.example.com.",
        "WHOIS://WHOIS.EXAMPLE.COM",
        "whois://whois.first.com.",
        "whois://whois.iana.org",
        "whois://whois.example.com/path/to/server",
        "whois://whois.example.com?query=1",
        "whois://whois.example.com/path",
        "whois://whois.example.com:43/",
        "whois://whois.iana.org:43",
        "whois://whois.iana.org:43/path",
        "whois.iana.org:43",
        "WHOIS.IANA.ORG:43",
        "whois.iana.org:43",
    ]

    for _ in range(2000):
        num_refs = rng.randint(1, 3)
        selected_patterns = rng.sample(referral_patterns, num_refs)
        raw = "".join(p.format(rng.choice(referral_values)) for p in selected_patterns)
        raw_inputs.append(raw)

    for raw in raw_inputs:
        try:
            our_result = extract_referral_server(raw)
        except Exception as e:
            mismatches.append((raw, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_extract_referral_server(raw)

        if our_result != oracle_result:
            mismatches.append((raw, our_result, oracle_result))

    return mismatches


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches = []

    print("Verifying parse_whois...", file=sys.stderr)
    mismatches = verify_parse_whois()
    if mismatches:
        all_mismatches.extend([("parse_whois",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying extract_referral_server...", file=sys.stderr)
    mismatches = verify_extract_referral_server()
    if mismatches:
        all_mismatches.extend([("extract_referral_server",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    if all_mismatches:
        print(f"\n=== TOTAL MISMATCHES: {len(all_mismatches)} ===", file=sys.stderr)
        for func, inp, ours, oracle in all_mismatches[:20]:
            print(f"  {func}({inp!r}) => ours={ours!r}, oracle={oracle!r}", file=sys.stderr)
        if len(all_mismatches) > 20:
            print(f"  ... and {len(all_mismatches) - 20} more", file=sys.stderr)
        return 1

    print("\n=== ALL VERIFICATIONS PASSED ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())