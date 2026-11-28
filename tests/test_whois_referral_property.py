"""Property-based tests for ethscan.whois.extract_referral_server.

``extract_referral_server`` parses untrusted WHOIS responses to extract the
first referral server hostname (by position in the text), lowercased and
stripped of trailing dots, ``whois://`` scheme, and any path/query/fragment,
while excluding ``whois.iana.org``. A regression in the pattern set, the
position-based priority, the scheme stripping, or the ``whois.iana.org``
exclusion would silently return the wrong referral server (or none). The
existing tests only cover a few fixed examples, so these lock the behaviour
against an INDEPENDENT from-scratch oracle that does not call any ethscan
helper.
"""
import random
import re

from ethscan.whois import extract_referral_server

_SEED = 20261128

_LABELS = [
    "Registrar WHOIS Server:",
    "WHOIS Server:",
    "Referral Server:",
    "Refer:",
    "Registrar URL:",
]

_HOSTS = [
    "whois.example.com",
    "whois.registrar.net",
    "whois.test.org",
    "whois.iana.org",
    "whois.iana.org:43",
    "WHOIS.EXAMPLE.COM",
    "whois.example.com.",
    "whois.example.com:43",
    "host-1.example.com",
    "192.0.2.1",
]

_PATHS = ["", "/path/to/server", "?query=1", "#frag", "/p?q#f", ":43/", ":43?x", ":43#y"]

_NOISE = [
    "",
    "registrar: Example Inc\n",
    "Creation Date: 2020-01-01\n",
    "Registry Expiry Date: 2021-01-01\n",
    "Some other text without referral\n",
    "Registrar WHOIS Server: \n",
    "Refer:\n",
]


def _oracle(raw: str) -> str | None:
    """Independent from-scratch recomputation of extract_referral_server.

    Does not import or call any ethscan helper.
    """
    patterns = [
        r"Registrar WHOIS Server:[ \t]*(\S+)",
        r"WHOIS Server:[ \t]*(\S+)",
        r"Referral Server:[ \t]*(\S+)",
        r"Refer:[ \t]*(\S+)",
        r"Registrar URL:[ \t]*whois://(\S+)",
    ]
    candidates: list[tuple[int, int, str]] = []
    for idx, pat in enumerate(patterns):
        match = re.search(pat, raw, re.IGNORECASE)
        if match:
            candidates.append((match.start(), idx, match.group(1)))
    candidates.sort()
    for _pos, _idx, value in candidates:
        server = value.strip().rstrip(".")
        if server.lower().startswith("whois://"):
            server = server[len("whois://"):]
        server = server.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        hostname = server.split(":", 1)[0].lower()
        if server and hostname != "whois.iana.org":
            return server.lower()
    return None


def _gen_segment(rng: random.Random) -> str:
    if rng.random() < 0.7:
        label = rng.choice(_LABELS)
        if rng.random() < 0.3:
            label = label.upper()
        elif rng.random() < 0.3:
            label = label.lower()
        host = rng.choice(_HOSTS)
        scheme = "whois://" if rng.random() < 0.5 else ""
        path = rng.choice(_PATHS)
        if scheme:
            value = scheme + host + path
        else:
            value = host + path
        sep = rng.choice([":", ": ", ":\t", ":  "])
        return label + sep + value
    return rng.choice(_NOISE)


def _gen_raw(rng: random.Random) -> str:
    segments = [_gen_segment(rng) for _ in range(rng.randint(0, 4))]
    if rng.random() < 0.5:
        segments.append(rng.choice(_NOISE))
    return "\n".join(segments)


def test_extract_referral_server_matches_oracle_random() -> None:
    rng = random.Random(_SEED)
    for _ in range(6000):
        raw = _gen_raw(rng)
        assert extract_referral_server(raw) == _oracle(raw), raw


def test_extract_referral_server_each_label() -> None:
    cases = [
        ("Registrar WHOIS Server: whois.example.com", "whois.example.com"),
        ("WHOIS Server: whois.registrar.net", "whois.registrar.net"),
        ("Referral Server: whois.test.org", "whois.test.org"),
        ("Refer: whois.example.com", "whois.example.com"),
        ("Registrar URL: whois://whois.example.com", "whois.example.com"),
    ]
    for raw, expected in cases:
        assert extract_referral_server(raw) == expected, raw


def test_extract_referral_server_case_insensitive_labels() -> None:
    assert extract_referral_server("registrar whois server: whois.example.com") == "whois.example.com"
    assert extract_referral_server("WHOIS SERVER: whois.example.com") == "whois.example.com"
    assert extract_referral_server("Referral Server: WHOIS.EXAMPLE.COM") == "whois.example.com"


def test_extract_referral_server_trailing_dot_and_lowercasing() -> None:
    assert extract_referral_server("Registrar WHOIS Server: whois.example.com.") == "whois.example.com"
    assert extract_referral_server("Refer: WHOIS.EXAMPLE.COM.") == "whois.example.com"


def test_extract_referral_server_whois_iana_org_excluded() -> None:
    # whois.iana.org (with or without port, with or without scheme) is never a
    # referral.
    assert extract_referral_server("Registrar WHOIS Server: whois.iana.org") is None
    assert extract_referral_server("WHOIS Server: whois.iana.org:43") is None
    assert extract_referral_server("Referral Server: WHOIS.IANA.ORG:43") is None
    assert extract_referral_server("Refer: whois://whois.iana.org") is None
    assert extract_referral_server("Refer: whois://whois.iana.org:43/path") is None
    assert extract_referral_server("Registrar URL: whois://whois.iana.org") is None


def test_extract_referral_server_first_match_by_position_wins() -> None:
    # Position in the text wins over pattern priority: a lower-priority pattern
    # that appears earlier in the response is returned.
    raw = "WHOIS Server: whois.second.com\nRegistrar WHOIS Server: whois.first.com"
    assert extract_referral_server(raw) == "whois.second.com"
    raw2 = "Registrar WHOIS Server: whois.first.com\nWHOIS Server: whois.second.com"
    assert extract_referral_server(raw2) == "whois.first.com"


def test_extract_referral_server_url_scheme_and_path_stripped() -> None:
    assert extract_referral_server("Refer: whois://whois.example.com/path/to/server") == "whois.example.com"
    assert extract_referral_server("Refer: whois://whois.example.com?query=1") == "whois.example.com"
    assert extract_referral_server("Registrar URL: whois://whois.example.com/path") == "whois.example.com"
    assert extract_referral_server("WHOIS Server: whois://whois.example.com:43/") == "whois.example.com:43"
    assert extract_referral_server("Registrar WHOIS Server:\twhois://whois.first.com.") == "whois.first.com"


def test_extract_referral_server_empty_value_does_not_cross_lines() -> None:
    raw = "Registrar WHOIS Server: \nWHOIS Server: whois.other.com\n"
    assert extract_referral_server(raw) == "whois.other.com"
    raw2 = "Registrar WHOIS Server:\nRefer: whois.other.com\n"
    assert extract_referral_server(raw2) == "whois.other.com"
    assert extract_referral_server("Refer:\nwhois.other.com\n") is None


def test_extract_referral_server_no_match() -> None:
    assert extract_referral_server("Some other text without referral") is None
    assert extract_referral_server("") is None
    assert extract_referral_server("   ") is None
    assert extract_referral_server("Registrar: Example Inc\nCreation Date: 2020-01-01\n") is None
