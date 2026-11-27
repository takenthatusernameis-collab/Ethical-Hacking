"""Property tests for ethscan.urlcheck pure helpers vs stdlib oracles."""

from __future__ import annotations

import random
import string
from urllib.parse import urlparse

import pytest

from ethscan.urlcheck import _normalize_url

_PROPERTY_SEED = 20261127


def _rand_hostname(rnd: random.Random) -> str:
    """Generate a random valid hostname-like string."""
    labels = []
    for _ in range(rnd.randint(1, 4)):
        length = rnd.randint(1, 10)
        label = "".join(rnd.choices(string.ascii_lowercase + string.digits, k=length))
        if label[0].isdigit():
            label = "a" + label[1:]
        labels.append(label)
    return ".".join(labels)


def _rand_ipv4(rnd: random.Random) -> str:
    return ".".join(str(rnd.randint(0, 255)) for _ in range(4))


def _rand_ipv6(rnd: random.Random) -> str:
    return ":".join(f"{rnd.randint(0, 65535):x}" for _ in range(8))


def _rand_path(rnd: random.Random) -> str:
    if rnd.random() < 0.3:
        return ""
    segments = rnd.randint(1, 4)
    parts = []
    for _ in range(segments):
        length = rnd.randint(1, 8)
        part = "".join(rnd.choices(string.ascii_letters + string.digits + "-_", k=length))
        parts.append(part)
    return "/" + "/".join(parts)


def _rand_query(rnd: random.Random) -> str:
    if rnd.random() < 0.5:
        return ""
    params = rnd.randint(1, 3)
    parts = []
    for _ in range(params):
        k = "".join(rnd.choices(string.ascii_lowercase, k=rnd.randint(1, 5)))
        v = "".join(rnd.choices(string.ascii_letters + string.digits, k=rnd.randint(1, 8)))
        parts.append(f"{k}={v}")
    return "?" + "&".join(parts)


def _rand_fragment(rnd: random.Random) -> str:
    if rnd.random() < 0.7:
        return ""
    return "#" + "".join(rnd.choices(string.ascii_letters + string.digits, k=rnd.randint(1, 6)))


def _rand_port(rnd: random.Random) -> str:
    if rnd.random() < 0.3:
        return ""
    return ":" + str(rnd.randint(1, 65535))


def _gen_target_with_scheme(rnd: random.Random) -> str:
    """Generate a target that already has a scheme."""
    scheme = rnd.choice(["http://", "https://", "ftp://", "ftps://"])
    host_type = rnd.choice(["hostname", "ipv4", "ipv6"])
    if host_type == "hostname":
        host = _rand_hostname(rnd)
    elif host_type == "ipv4":
        host = _rand_ipv4(rnd)
    else:
        host = f"[{_rand_ipv6(rnd)}]"
    port = _rand_port(rnd)
    path = _rand_path(rnd)
    query = _rand_query(rnd)
    fragment = _rand_fragment(rnd)
    return f"{scheme}{host}{port}{path}{query}{fragment}"


def _gen_target_without_scheme(rnd: random.Random) -> str:
    """Generate a target without a scheme."""
    host_type = rnd.choice(["hostname", "ipv4", "ipv6", "hostname_port"])
    if host_type == "hostname":
        host = _rand_hostname(rnd)
    elif host_type == "ipv4":
        host = _rand_ipv4(rnd)
    elif host_type == "ipv6":
        host = f"[{_rand_ipv6(rnd)}]"
    else:
        host = _rand_hostname(rnd) + _rand_port(rnd)
    path = _rand_path(rnd)
    query = _rand_query(rnd)
    fragment = _rand_fragment(rnd)
    return f"{host}{path}{query}{fragment}"


def _gen_whitespace_target(rnd: random.Random) -> str:
    """Generate a target with random leading/trailing whitespace."""
    inner = rnd.choice([_gen_target_with_scheme, _gen_target_without_scheme])(rnd)
    ws_chars = " \t\n\r"
    leading = "".join(rnd.choices(ws_chars, k=rnd.randint(0, 3)))
    trailing = "".join(rnd.choices(ws_chars, k=rnd.randint(0, 3)))
    return leading + inner + trailing


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_always_parses_with_scheme(seed: int) -> None:
    """_normalize_url output must always parse to a URL with a non-empty scheme."""
    rnd = random.Random(seed)
    for _ in range(2000):
        # Mix of targets with and without schemes, plus whitespace
        gen = rnd.choice([
            _gen_target_with_scheme,
            _gen_target_without_scheme,
            _gen_whitespace_target,
        ])
        target = gen(rnd)
        normalized = _normalize_url(target)
        parsed = urlparse(normalized)
        assert parsed.scheme, f"Empty scheme for target {target!r} -> {normalized!r}"
        # netloc can be empty for edge case of empty input -> "https://"
        # but scheme must be present


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_preserves_existing_scheme(seed: int) -> None:
    """If input already has a scheme, _normalize_url must preserve it."""
    rnd = random.Random(seed + 1)
    for _ in range(1000):
        target = _gen_target_with_scheme(rnd)
        # Ensure it has a scheme by construction
        parsed_in = urlparse(target)
        assert parsed_in.scheme
        normalized = _normalize_url(target)
        parsed_out = urlparse(normalized)
        assert parsed_out.scheme == parsed_in.scheme, (
            f"Scheme changed: {target!r} -> {normalized!r} "
            f"(expected {parsed_in.scheme}, got {parsed_out.scheme})"
        )


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_adds_https_when_missing(seed: int) -> None:
    """If input lacks a scheme, _normalize_url must add https://."""
    rnd = random.Random(seed + 2)
    for _ in range(1000):
        target = _gen_target_without_scheme(rnd)
        # Input may or may not look like it has a scheme; the function checks for "://"
        if "://" not in target.strip():
            normalized = _normalize_url(target)
            parsed_out = urlparse(normalized)
            assert parsed_out.scheme == "https", (
                f"Expected https scheme for {target!r}, got {parsed_out.scheme!r} in {normalized!r}"
            )


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_preserves_netloc_and_path(seed: int) -> None:
    """_normalize_url must preserve netloc and path when scheme already present."""
    rnd = random.Random(seed + 3)
    for _ in range(1000):
        target = _gen_target_with_scheme(rnd)
        normalized = _normalize_url(target)
        parsed_in = urlparse(target)
        parsed_out = urlparse(normalized)
        assert parsed_out.netloc == parsed_in.netloc, (
            f"Netloc changed: {target!r} -> {normalized!r} "
            f"(expected {parsed_in.netloc!r}, got {parsed_out.netloc!r})"
        )
        assert parsed_out.path == parsed_in.path, (
            f"Path changed: {target!r} -> {normalized!r} "
            f"(expected {parsed_in.path!r}, got {parsed_out.path!r})"
        )
        assert parsed_out.query == parsed_in.query
        assert parsed_out.fragment == parsed_in.fragment


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_strips_whitespace(seed: int) -> None:
    """_normalize_url must strip leading/trailing whitespace."""
    rnd = random.Random(seed + 4)
    for _ in range(500):
        inner = rnd.choice([_gen_target_with_scheme, _gen_target_without_scheme])(rnd)
        ws_chars = " \t\n\r"
        leading = "".join(rnd.choices(ws_chars, k=rnd.randint(0, 3)))
        trailing = "".join(rnd.choices(ws_chars, k=rnd.randint(0, 3)))
        target = leading + inner + trailing
        normalized = _normalize_url(target)
        # Should not start or end with whitespace
        assert not normalized[:1].isspace() if normalized else True
        assert not normalized[-1:].isspace() if normalized else True
        # And should equal normalize_url(inner)
        assert normalized == _normalize_url(inner)


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_idempotent(seed: int) -> None:
    """_normalize_url(_normalize_url(x)) == _normalize_url(x)."""
    rnd = random.Random(seed + 5)
    for _ in range(1000):
        gen = rnd.choice([
            _gen_target_with_scheme,
            _gen_target_without_scheme,
            _gen_whitespace_target,
        ])
        target = gen(rnd)
        first = _normalize_url(target)
        second = _normalize_url(first)
        assert first == second, f"Not idempotent: {target!r} -> {first!r} -> {second!r}"


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_empty_input(seed: int) -> None:
    """Empty input yields 'https://' (scheme present, netloc empty)."""
    normalized = _normalize_url("")
    parsed = urlparse(normalized)
    assert parsed.scheme == "https"
    assert parsed.netloc == ""


@pytest.mark.parametrize("seed", [_PROPERTY_SEED])
def test_normalize_url_only_whitespace(seed: int) -> None:
    """Whitespace-only input yields 'https://'."""
    for ws in [" ", "\t", "\n", "\r", "  \t\n  "]:
        normalized = _normalize_url(ws)
        parsed = urlparse(normalized)
        assert parsed.scheme == "https"
        assert parsed.netloc == ""


# Known-vectors regression tests
def test_normalize_url_known_vectors() -> None:
    """Fixed known vectors to lock current behavior."""
    vectors = [
        ("example.com", "https://example.com"),
        ("https://example.com", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("https://example.com:8443", "https://example.com:8443"),
        ("example.com/path", "https://example.com/path"),
        ("example.com:8080/path", "https://example.com:8080/path"),
        ("  example.com  ", "https://example.com"),
        ("", "https://"),
        ("https://[::1]", "https://[::1]"),
        ("[::1]", "https://[::1]"),
        ("http://user:pass@example.com", "http://user:pass@example.com"),
        ("ftp://files.example.com", "ftp://files.example.com"),
        ("example.com?query=1", "https://example.com?query=1"),
        ("example.com#frag", "https://example.com#frag"),
    ]
    for inp, expected in vectors:
        assert _normalize_url(inp) == expected, f"Vector failed: {inp!r} -> {_normalize_url(inp)!r} (expected {expected!r})"


# Mutation test: if we change the scheme from https to http, the "adds https" test should fail
# (This is verified by the test_normalize_url_adds_https_when_missing test above)