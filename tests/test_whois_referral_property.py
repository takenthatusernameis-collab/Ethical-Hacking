"""Property-based tests for ethscan.whois.extract_referral_server.

``extract_referral_server`` pulls a referral WHOIS server hostname out of an
untrusted raw WHOIS response. It must reduce a URL referral (``whois://host``)
to a bare hostname, drop any path/query/fragment and trailing dot, exclude
``whois.iana.org`` (with or without a port), match case-insensitively, and pick
the referral that appears earliest in the text (position, not pattern priority).
A regression in any of these heuristics would silently return the wrong server
(or a value ``getaddrinfo`` cannot resolve). The existing tests only cover a few
fixed examples, so these lock the behaviour against an INDEPENDENT from-scratch
oracle that does not call any ethscan helper.
"""
import random
import re

from ethscan.whois import extract_referral_server

_SEED = 20261128

_HOSTS = [
    "whois.example.com",
    "whois.registrar.net",
    "WHOIS.EXAMPLE.COM",
    "whois.example.com.",
    "whois.iana.org",
    "WHOIS.IANA.ORG",
    "whois.iana.org:43",
    "whois.example.com:43",
    "whois.first.com",
    "whois.second.com",
    "whois.other.com",
    "x",
    "a.b.c.d",
    "under_score.example.com",
    "host-1.example.com",
]

_VALUE_FORMS = [
    "{h}",
    "{h}.",
    "whois://{h}",
    "WHOIS://{h}",
    "whois://{h}.",
    "whois://{h}/path/to/server",
    "whois://{h}?query=1",
    "whois://{h}#frag",
    "whois://{h}:43/",
    "whois://{h}:43",
    "  {h}  ",
    "\t{h}",
    "{h}/path",
    "{h}?q=1",
    "",
    "   ",
]

_LABELS = [
    "Registrar WHOIS Server",
    "WHOIS Server",
    "Referral Server",
    "Refer",
    "Registrar URL",
]

_NOISE = [
    "Domain Name: example.com",
    "Some other text without referral",
    "Registrar: Example Inc",
    "   ",
    "",
    "WHOIS Server:",
]


def _oracle(raw: str) -> str | None:
    """INDEPENDENT recomputation of the documented behaviour (no ethscan calls)."""
    patterns = [
        re.compile(r"Registrar WHOIS Server:[ \t]*(\S+)", re.IGNORECASE),
        re.compile(r"WHOIS Server:[ \t]*(\S+)", re.IGNORECASE),
        re.compile(r"Referral Server:[ \t]*(\S+)", re.IGNORECASE),
        re.compile(r"Refer:[ \t]*(\S+)", re.IGNORECASE),
        re.compile(r"Registrar URL:[ \t]*whois://(\S+)", re.IGNORECASE),
    ]
    found: list[tuple[int, int, str]] = []
    for order, pattern in enumerate(patterns):
        match = pattern.search(raw)
        if match is not None:
            found.append((match.start(), order, match.group(1)))
    found.sort(key=lambda item: (item[0], item[1]))
    for _start, _order, value in found:
        server = value.strip().rstrip(".")
        if server.lower().startswith("whois://"):
            server = server[len("whois://"):]
        for sep in ("/", "?", "#"):
            cut = server.find(sep)
            if cut != -1:
                server = server[:cut]
        hostname = server.split(":", 1)[0].lower()
        if server and hostname != "whois.iana.org":
            return server.lower()
    return None


def _gen_value(rng: random.Random) -> str:
    return rng.choice(_VALUE_FORMS).format(h=rng.choice(_HOSTS))


def _gen_line(rng: random.Random) -> str:
    label = rng.choice(_LABELS)
    sep = rng.choice([": ", ":", ":\t", ":   ", ": \t"])
    return f"{label}{sep}{_gen_value(rng)}"


def _gen_raw(rng: random.Random) -> str:
    lines = [_gen_line(rng) for _ in range(rng.randint(0, 6))]
    if rng.random() < 0.4:
        lines.insert(rng.randint(0, len(lines)), rng.choice(_NOISE))
    sep = rng.choice(["\n", "\r\n"])
    text = sep.join(lines)
    if rng.random() < 0.5:
        text += sep
    return text


def test_extract_referral_server_matches_oracle_random() -> None:
    rng = random.Random(_SEED)
    for _ in range(5000):
        raw = _gen_raw(rng)
        assert extract_referral_server(raw) == _oracle(raw), raw


def test_extract_referral_server_strips_scheme_port_path() -> None:
    # A URL referral is reduced to its bare hostname (and optional port).
    assert extract_referral_server("Refer: whois://whois.example.com") == "whois.example.com"
    assert extract_referral_server("WHOIS Server: whois://whois.example.com:43/") == (
        "whois.example.com:43"
    )
    assert extract_referral_server("Refer: whois://whois.example.com/path/to/server") == (
        "whois.example.com"
    )
    assert extract_referral_server("Refer: whois://whois.example.com?query=1") == (
        "whois.example.com"
    )
    assert extract_referral_server("Refer: whois://whois.example.com#frag") == "whois.example.com"


def test_extract_referral_server_excludes_iana() -> None:
    # whois.iana.org is excluded with or without scheme/port/path.
    assert extract_referral_server("Registrar WHOIS Server: whois.iana.org") is None
    assert extract_referral_server("Refer: whois://whois.iana.org") is None
    assert extract_referral_server("Refer: whois://whois.iana.org:43") is None
    assert extract_referral_server("Refer: whois://whois.iana.org:43/path") is None
    assert extract_referral_server("Registrar WHOIS Server: whois.iana.org:43") is None
    assert extract_referral_server("Referral Server: WHOIS.IANA.ORG:43") is None


def test_extract_referral_server_case_insensitive_and_trailing_dot() -> None:
    assert extract_referral_server("registrar whois server: whois.example.com") == (
        "whois.example.com"
    )
    assert extract_referral_server("Registrar WHOIS Server: WHOIS.EXAMPLE.COM.") == (
        "whois.example.com"
    )
    assert extract_referral_server("Registrar URL: whois://whois.example.com") == (
        "whois.example.com"
    )


def test_extract_referral_server_first_by_position_not_pattern_priority() -> None:
    # The earliest referral in the text wins even if a "higher-priority" pattern
    # matches a later line.
    raw = "WHOIS Server: whois.second.com\nRegistrar WHOIS Server: whois.first.com"
    assert extract_referral_server(raw) == "whois.second.com"
    raw2 = "Registrar WHOIS Server: whois.first.com\nWHOIS Server: whois.second.com"
    assert extract_referral_server(raw2) == "whois.first.com"


def test_extract_referral_server_empty_value_does_not_cross_lines() -> None:
    # A label with an empty same-line value must not capture the next line's
    # leading keyword as the referral hostname.
    assert extract_referral_server("Registrar WHOIS Server: \nWHOIS Server: whois.other.com\n") == (
        "whois.other.com"
    )
    assert extract_referral_server("Registrar WHOIS Server:\nRefer: whois.other.com\n") == (
        "whois.other.com"
    )
    assert extract_referral_server("Refer:\nwhois.other.com\n") is None


def test_extract_referral_server_no_match() -> None:
    assert extract_referral_server("Some other text without referral") is None
    assert extract_referral_server("") is None
    assert extract_referral_server("   ") is None