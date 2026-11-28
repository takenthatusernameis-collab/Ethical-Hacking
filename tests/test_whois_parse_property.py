"""Property-based tests for ethscan.whois.parse_whois.

``parse_whois`` pulls registrar, creation/expiration date, registrant
organisation, nameservers and status codes out of an untrusted raw WHOIS
response. The registrar field follows a documented priority order
(Registrar > Registrar Name > Sponsoring Registrar) guarded by a negative
lookbehind so ``Registrar:`` never matches the substring inside
``Sponsoring Registrar:``; nameservers and status codes are deduplicated and
sorted. A regression in any of these heuristics silently returns the wrong
field. The existing tests cover a few fixed examples, so these lock the
behaviour against an INDEPENDENT from-scratch oracle that does not call any
ethscan helper.
"""
import random
import re

from ethscan.whois import parse_whois

_SEED = 20261128

_REGISTRAR_PATTERNS = [
    re.compile(r"(?<!Sponsoring )Registrar:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Registrar Name:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Sponsoring Registrar:[ \t]*(.+)", re.IGNORECASE),
]
_CREATION_PATTERNS = [
    re.compile(r"Creation Date:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Created:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Registration Date:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Domain Registration Date:[ \t]*(.+)", re.IGNORECASE),
]
_EXPIRATION_PATTERNS = [
    re.compile(r"Expiration Date:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Expiry Date:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Registry Expiry Date:[ \t]*(.+)", re.IGNORECASE),
]
_ORG_PATTERNS = [
    re.compile(r"Registrant Organization:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Registrant Org:[ \t]*(.+)", re.IGNORECASE),
    re.compile(r"Organization:[ \t]*(.+)", re.IGNORECASE),
]
_NAMESERVER_PATTERN = re.compile(r"Name Server:[ \t]*(\S+)", re.IGNORECASE)
_STATUS_PATTERN = re.compile(r"Status:[ \t]*(\S+)", re.IGNORECASE)

_KEYS = [
    "Registrar", "Registrar Name", "Sponsoring Registrar", "Creation Date",
    "Created", "Registration Date", "Domain Registration Date",
    "Expiration Date", "Expiry Date", "Registry Expiry Date",
    "Registrant Organization", "Registrant Org", "Organization",
    "Name Server", "Status", "Random Key",
]
_VALUES = [
    "whois.example.com", "WHOIS.EXAMPLE.COM", "2020-01-01", "ns1.example.com",
    "clientDeleteProhibited", "Example Org", "whois.iana.org", "x",
    "  spaced  ", "Example.Com.", "",
]


def _first(patterns, raw):
    """Return the stripped value of the first matching pattern, or None."""
    for pattern in patterns:
        match = pattern.search(raw)
        if match is not None:
            return match.group(1).strip()
    return None


def _all(pattern, raw, transform):
    """Deduplicate, transform and sort every match of a single pattern."""
    return sorted({transform(match) for match in pattern.findall(raw)})


def _oracle(raw):
    """INDEPENDENT recomputation of parse_whois (no ethscan calls)."""
    return {
        "registrar": _first(_REGISTRAR_PATTERNS, raw),
        "creation_date": _first(_CREATION_PATTERNS, raw),
        "expiration_date": _first(_EXPIRATION_PATTERNS, raw),
        "registrant_org": _first(_ORG_PATTERNS, raw),
        "nameservers": _all(_NAMESERVER_PATTERN, raw,
                            lambda s: s.strip().rstrip(".")),
        "status_codes": _all(_STATUS_PATTERN, raw, lambda s: s.strip()),
    }


def _gen_raw(rng):
    lines = [f"{rng.choice(_KEYS)}: {rng.choice(_VALUES)}"
             for _ in range(rng.randint(0, 6))]
    return "\n".join(lines)


def test_parse_whois_matches_oracle_random():
    rng = random.Random(_SEED)
    for _ in range(20000):
        raw = _gen_raw(rng)
        impl = parse_whois(raw)
        oracle = _oracle(raw)
        for field in ("registrar", "creation_date", "expiration_date",
                      "registrant_org", "nameservers", "status_codes"):
            assert impl[field] == oracle[field], (raw, field, impl[field], oracle[field])


def test_parse_whois_registrar_priority_and_lookbehind():
    # Documented priority: Registrar > Registrar Name > Sponsoring Registrar.
    assert parse_whois("Sponsoring Registrar: Sponsor Inc\n")["registrar"] == "Sponsor Inc"
    assert parse_whois("Registrar Name: Name Inc\nRegistrar: Plain Inc\n")["registrar"] == "Plain Inc"
    assert parse_whois("Registrar Name: Name Inc\nSponsoring Registrar: Sponsor Inc\n")["registrar"] == "Name Inc"
    # The plain pattern must not match the substring inside Sponsoring Registrar.
    assert parse_whois("Sponsoring Registrar: Only Sponsor\n")["registrar"] == "Only Sponsor"
    assert parse_whois("Registrar: Plain\nSponsoring Registrar: Sponsor\n")["registrar"] == "Plain"


def test_parse_whois_date_priority():
    # Pattern priority is absolute: pattern 1 wins if it matches anywhere in
    # the text, even when a lower-priority pattern appears earlier in the text.
    assert parse_whois("Creation Date: 2020-05-05\nCreated: 2020-01-01\n")["creation_date"] == "2020-05-05"
    assert parse_whois("Created: 2020-01-01\nCreation Date: 2020-05-05\n")["creation_date"] == "2020-05-05"
    # Pattern 2 is used only when pattern 1 matches nowhere.
    assert parse_whois("Created: 2020-01-01\n")["creation_date"] == "2020-01-01"
    assert parse_whois("Expiry Date: 2021-02-02\nExpiration Date: 2021-01-01\n")["expiration_date"] == "2021-01-01"
    assert parse_whois("Expiration Date: 2021-01-01\nExpiry Date: 2021-02-02\n")["expiration_date"] == "2021-01-01"
    assert parse_whois("Expiry Date: 2021-02-02\n")["expiration_date"] == "2021-02-02"


def test_parse_whois_registrant_org():
    assert parse_whois("Registrant Organization: Example Org\n")["registrant_org"] == "Example Org"
    assert parse_whois("Organization: Short Org\n")["registrant_org"] == "Short Org"
    assert parse_whois("No org here\n")["registrant_org"] is None


def test_parse_whois_nameservers_dedup_sorted_strip_dot():
    raw = "Name Server: ns2.example.com.\nName Server: ns1.example.com\nName Server: ns1.example.com\n"
    assert parse_whois(raw)["nameservers"] == ["ns1.example.com", "ns2.example.com"]


def test_parse_whois_status_codes_dedup_sorted():
    raw = "Status: clientDeleteProhibited\nStatus: clientUpdateProhibited\nStatus: clientDeleteProhibited\n"
    assert parse_whois(raw)["status_codes"] == ["clientDeleteProhibited", "clientUpdateProhibited"]


def test_parse_whois_empty_same_line_value_does_not_cross_lines():
    # ``(.+)`` needs at least one character: a whitespace-only same-line value
    # still matches (one space) and strips to "", so it does NOT fall back to
    # the next pattern; a truly empty value (label at end of line) does.
    assert parse_whois("Registrar: \nRegistrar Name: Real Registrar\n")["registrar"] == ""
    assert parse_whois("Registrar: \n")["registrar"] == ""
    assert parse_whois("Registrar:\nRegistrar Name: Real Registrar\n")["registrar"] == "Real Registrar"
    assert parse_whois("Registrar:\n")["registrar"] is None


def test_parse_whois_case_insensitive():
    # Labels match case-insensitively, but captured values keep their case
    # (only stripped); nameservers/status are not lowercased.
    raw = "registrar: lower.inc\nCREATION DATE: 1999-01-01\nnAmE sErVeR: NS.EXAMPLE.COM\nstatus: LOCKED\n"
    assert parse_whois(raw)["registrar"] == "lower.inc"
    assert parse_whois(raw)["creation_date"] == "1999-01-01"
    assert parse_whois(raw)["nameservers"] == ["NS.EXAMPLE.COM"]
    assert parse_whois(raw)["status_codes"] == ["LOCKED"]


def test_parse_whois_no_match():
    assert parse_whois("") == {
        "registrar": None, "creation_date": None, "expiration_date": None,
        "registrant_org": None, "nameservers": [], "status_codes": [],
        "raw": "",
    }
    noisy = "Just noise without labels\n"
    parsed = parse_whois(noisy)
    assert parsed["registrar"] is None
    assert parsed["creation_date"] is None
    assert parsed["expiration_date"] is None
    assert parsed["registrant_org"] is None
    assert parsed["nameservers"] == []
    assert parsed["status_codes"] == []
    assert parsed["raw"] == noisy
    # The returned dict always carries the original input under "raw".
    assert parse_whois("anything at all")["raw"] == "anything at all"
