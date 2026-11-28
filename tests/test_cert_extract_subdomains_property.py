"""Property-based tests for ethscan.cert._extract_subdomains.

``_extract_subdomains`` parses untrusted Certificate Transparency ``name_value``
/ ``common_name`` fields (possibly multiline, mixed case, padded) into a unique,
sorted list of subdomains. A regression in the ``or`` fallback, the multiline
split, the case-folding, the de-duplication, or the final sort would silently
report the wrong subdomains. The existing tests only cover a few fixed examples,
so these lock the behaviour against an INDEPENDENT from-scratch oracle that does
not call any ethscan helper.
"""
import random

from ethscan.cert import _extract_subdomains

_SEED = 20261128

_HOST_TOKENS = [
    "example.com",
    "www.example.com",
    "api.example.com",
    "EXAMPLE.COM",
    "  spaced.example.com  ",
    "a.b.c",
    "x",
    "",
    "  ",
    "under_score",
    "host-1.example.com",
    "host-2.example.com",
]


def _oracle(cert_data: dict[str, object]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    entries = cert_data.get("entries") or []
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name_value") or entry.get("common_name") or ""
            if not name:
                continue
            for token in str(name).splitlines():
                token = token.strip().lower()
                if token and token not in seen:
                    seen.add(token)
                    names.append(token)
    return sorted(names)


def _gen_entry(rng: random.Random) -> object:
    if rng.random() < 0.1:
        return rng.choice([None, 123, "notadict", ["x"], 3.14])
    entry: dict[str, object] = {}
    nv: object = rng.choice([*_HOST_TOKENS, None, 0, 123])
    cn: object = rng.choice([*_HOST_TOKENS, None, ""])
    if rng.random() < 0.8:
        entry["name_value"] = nv
    if rng.random() < 0.5:
        entry["common_name"] = cn
    if isinstance(nv, str) and rng.random() < 0.3:
        entry["name_value"] = nv + "\n" + rng.choice(_HOST_TOKENS)
    return entry


def test_extract_subdomains_matches_oracle_random() -> None:
    rng = random.Random(_SEED)
    for _ in range(3000):
        entries = [_gen_entry(rng) for _ in range(rng.randint(0, 6))]
        if rng.random() < 0.1:
            cert_data: dict[str, object] = {"entries": rng.choice([None, {}, 5, "x"])}
        else:
            cert_data = {"entries": entries}
        assert _extract_subdomains(cert_data) == _oracle(cert_data), cert_data


def test_extract_subdomains_dedupes_and_sorts_case_insensitively() -> None:
    cert_data = {
        "entries": [
            {"name_value": "WWW.Example.com"},
            {"name_value": "www.example.com"},
            {"name_value": "api.example.com"},
        ]
    }
    assert _extract_subdomains(cert_data) == ["api.example.com", "www.example.com"]


def test_extract_subdomains_multiline_name_value() -> None:
    cert_data = {"entries": [{"name_value": "b.example.com\r\na.example.com\n\n  c.example.com  "}]}
    assert _extract_subdomains(cert_data) == ["a.example.com", "b.example.com", "c.example.com"]


def test_extract_subdomains_common_name_fallback() -> None:
    # Empty name_value falls back to common_name.
    assert _extract_subdomains({"entries": [{"name_value": "", "common_name": "Fallback.com"}]}) == [
        "fallback.com"
    ]
    # A present name_value wins over common_name.
    assert _extract_subdomains(
        {"entries": [{"name_value": "primary.com", "common_name": "secondary.com"}]}
    ) == ["primary.com"]


def test_extract_subdomains_ignores_non_dict_and_non_list_entries() -> None:
    assert _extract_subdomains({"entries": [{"name_value": "ok.com"}, 42, "x", None]}) == ["ok.com"]
    assert _extract_subdomains({"entries": None}) == []
    assert _extract_subdomains({"entries": {"name_value": "ok.com"}}) == []


def test_extract_subdomains_empty_and_missing() -> None:
    assert _extract_subdomains({}) == []
    assert _extract_subdomains({"entries": []}) == []