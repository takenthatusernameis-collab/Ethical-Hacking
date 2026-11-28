"""Property tests for ethscan.whois.extract_referral_server.

Oracle is implemented from scratch here (no imports from ethscan helpers) to
independently lock the contract: scheme/port/path stripping, whois.iana.org
exclusion, case-insensitivity, priority-by-position.
"""
import random
import re

from ethscan.whois import extract_referral_server


PATTERNS = [
    r"Registrar WHOIS Server:[ \t]*(\S+)",
    r"WHOIS Server:[ \t]*(\S+)",
    r"Referral Server:[ \t]*(\S+)",
    r"Refer:[ \t]*(\S+)",
    r"Registrar URL:[ \t]*whois://(\S+)",
]


def oracle(raw: str) -> str | None:
    candidates = []
    for idx, pattern in enumerate(PATTERNS):
        for m in re.finditer(pattern, raw, re.IGNORECASE):
            candidates.append((m.start(), idx, m.group(1)))
    if not candidates:
        return None
    candidates.sort()
    # iterate in position order, but spec says first match by position among
    # all patterns; candidates sorted by (start, idx). However source uses
    # re.search per pattern then sorts by start (and idx as tiebreak). Replicate:
    # source collects one match per pattern (first occurrence), then sorts.
    # Re-run that exactly:
    cand2 = []
    for idx, pattern in enumerate(PATTERNS):
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            cand2.append((m.start(), idx, m.group(1)))
    cand2.sort()
    for _pos, _idx, val in cand2:
        server = val.strip().rstrip(".")
        if server.lower().startswith("whois://"):
            server = server[len("whois://"):]
        server = server.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        hostname = server.split(":", 1)[0].lower()
        if server and hostname != "whois.iana.org":
            return server.lower()
    return None


def test_matches_oracle_random():
    rng = random.Random(12345)
    labels = ["Registrar WHOIS Server", "WHOIS Server", "Referral Server",
              "Refer", "Registrar URL"]
    hosts = ["whois.example.com", "Whois.Example.COM.", "whois.iana.org",
             "whois.registrar.net", "WHOIS.IANA.ORG:43"]
    for _ in range(2000):
        # build a random raw response
        n_lines = rng.randint(1, 4)
        lines = []
        for _ in range(n_lines):
            if rng.random() < 0.6:
                label = rng.choice(labels)
                host = rng.choice(hosts)
                if "Registrar URL" in label:
                    lines.append(f"{label}: whois://{host}/path?x=1")
                else:
                    lines.append(f"{label}: {host}")
            else:
                lines.append("Some unrelated text here")
        raw = "\n".join(lines)
        assert extract_referral_server(raw) == oracle(raw), raw


def test_scheme_port_path_stripping():
    assert extract_referral_server("Refer: whois://whois.example.com/path/to/server") == "whois.example.com"
    assert extract_referral_server("Refer: whois://whois.example.com?query=1") == "whois.example.com"
    assert extract_referral_server("WHOIS Server: whois://whois.example.com:43/") == "whois.example.com:43"


def test_iana_exclusion():
    assert extract_referral_server("Refer: whois://whois.iana.org:43/path") is None
    assert extract_referral_server("Registrar WHOIS Server: WHOIS.IANA.ORG:43") is None


def test_case_insensitive():
    assert extract_referral_server("registrar whois server: WHOIS.EXAMPLE.COM") == "whois.example.com"


def test_priority_by_position():
    raw = "WHOIS Server: whois.second.com\nRegistrar WHOIS Server: whois.first.com"
    # first by position wins regardless of pattern priority
    assert extract_referral_server(raw) == "whois.second.com"


def test_empty():
    assert extract_referral_server("") is None
    assert extract_referral_server("   ") is None
