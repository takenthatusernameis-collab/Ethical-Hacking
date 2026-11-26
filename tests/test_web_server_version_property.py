"""Property-based oracle test for ``ethscan.web._assess_web_server_version``.

``_assess_web_server_version`` extracts server name and version from a Server header
and flags versions below minimum supported major versions. This test checks the
implementation against an independent oracle over a seeded random matrix of
server header strings.
"""

from __future__ import annotations

import random

import pytest

from ethscan.web import _WEB_SERVER_VERSION_RE, _assess_web_server_version

# Minimum supported major versions per server (from _assess_web_server_version)
_MIN_VERSIONS: dict[str, int] = {
    "apache": 2,
    "nginx": 1,
    "lighttpd": 1,
    "iis": 10,
}

# Known server names the regex recognises
_SERVER_NAMES = ["Apache", "nginx", "lighttpd", "IIS", "Microsoft-IIS"]


def _oracle_assess(server_header: str | None) -> list[str]:
    """Independent oracle for _assess_web_server_version.

    Re-implements the logic from scratch using the same specification:
    1. Extract server name and version using the same regex
    2. Normalise server name (lowercase, remove hyphens, microsoftiis -> iis)
    3. Parse major version (first dot-separated component)
    4. If major < minimum for that server, emit "Old web server version..." finding
    5. Always emit "Web server version: {version}" finding if parsed successfully
    """
    findings: list[str] = []
    if not server_header:
        return findings

    match = _WEB_SERVER_VERSION_RE.search(server_header)
    if not match:
        return findings

    server_name, version = match.group(1), match.group(2)

    # Parse major version
    try:
        major = int(version.split(".")[0])
    except (ValueError, IndexError):
        return findings

    findings.append(f"Web server version: {version}")

    # Normalise server name
    name_lower = server_name.lower().replace("-", "")
    if name_lower == "microsoftiis":
        name_lower = "iis"

    # Check against minimum
    min_major = _MIN_VERSIONS.get(name_lower)
    if min_major is not None and major < min_major:
        findings.append(
            f"Old web server version detected (version {version}; "
            "out of support, may lack security updates)"
        )

    return findings


# Seeded random matrix for reproducible property checking
_RNG = random.Random(20261126)

# Token pool for generating server header strings
_VERSION_COMPONENTS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "100", "abc", "1.2.3", "999"]
_SERVER_VARIANTS = [
    "Apache", "apache", "APACHE",
    "nginx", "NGINX", "Nginx",
    "lighttpd", "LIGHTTPD",
    "IIS", "iis", "Iis",
    "Microsoft-IIS", "microsoft-iis", "Microsoft-IIS/10.0",
    "UnknownServer", "Custom/1.0",
    "", "Apache/", "/1.0",
]


def _gen_server_header() -> str | None:
    """Generate a random server header string."""
    choice = _RNG.random()
    if choice < 0.1:
        return None
    if choice < 0.2:
        return ""
    # Build a realistic-ish header
    server = _RNG.choice(_SERVER_VARIANTS)
    if server in ("", "Apache/", "/1.0"):
        return server
    version = _RNG.choice(_VERSION_COMPONENTS)
    return f"{server}/{version}"


@pytest.mark.parametrize(
    "server_header",
    [
        # Explicit edge cases
        None,
        "",
        "Apache/1.3.42",
        "Apache/2.4.1",
        "nginx/0.9.0",
        "nginx/1.2.0",
        "lighttpd/0.9.0",
        "lighttpd/1.4.0",
        "IIS/5.0",
        "IIS/10.0",
        "Microsoft-IIS/5.0",
        "Microsoft-IIS/10.0",
        "Apache/abc",
        "Something/1.0",
        "Apache/2.4.41-ubuntu",
        "nginx/1.18.0 (Ubuntu)",
        "Apache/2.4.52 (Debian)",
        "IIS/10.0.19041",
        "Microsoft-IIS/6.0",
        "lighttpd/1.4.59",
        "Apache/0.9",
        "nginx/0.0.1",
        "IIS/9.0",
        "Microsoft-IIS/9.0",
        # Case variations
        "apache/1.0",
        "APACHE/1.0",
        "ApAcHe/1.0",
        "NGINX/0.5",
        "LiGhTtPd/0.1",
        "iis/5.0",
        "microsoft-iis/5.0",
        # Multiple dots
        "Apache/2.4.41",
        "nginx/1.20.1",
        "IIS/10.0.19041.1",
        # Extra text after version
        "Apache/2.4.41 (Unix)",
        "nginx/1.18.0 Ubuntu",
        "Server: Apache/2.4.1",
    ],
    ids=lambda v: str(v) if v is not None else "None",
)
def test_assess_web_server_version_explicit(server_header: str | None) -> None:
    """Explicit edge cases matching existing tests + new variations."""
    result = _assess_web_server_version(server_header)
    expected = _oracle_assess(server_header)
    assert result == expected, (
        f"Mismatch for {server_header!r}: got {result!r}, expected {expected!r}"
    )


def test_assess_web_server_version_random_matrix() -> None:
    """Seeded property test: implementation matches oracle across random inputs."""
    mismatches = []
    for _i in range(5000):
        header = _gen_server_header()
        result = _assess_web_server_version(header)
        expected = _oracle_assess(header)
        if result != expected:
            mismatches.append((header, result, expected))
            if len(mismatches) >= 10:
                break

    if mismatches:
        details = "\n".join(
            f"  {h!r}: got {r!r}, expected {e!r}" for h, r, e in mismatches
        )
        pytest.fail(f"Found {len(mismatches)} mismatches in random matrix:\n{details}")


def test_assess_web_server_version_version_parsing_edge_cases() -> None:
    """Test version parsing with edge cases that could diverge from oracle."""
    edge_cases = [
        # Non-numeric major version
        "Apache/abc",
        "Apache/x.y.z",
        "nginx/foo.bar",
        # Empty version
        "Apache/",
        "nginx/",
        # Leading zeros
        "Apache/01.0",
        "Apache/002.0",
        # Very large numbers
        "Apache/999999.0",
        "nginx/1000000.0",
        # Negative (not valid but check handling)
        "Apache/-1.0",
        # Plus sign
        "Apache/+2.0",
        # Decimal in major (not valid)
        "Apache/1.5.0",
    ]
    for header in edge_cases:
        result = _assess_web_server_version(header)
        expected = _oracle_assess(header)
        assert result == expected, (
            f"Mismatch for {header!r}: got {result!r}, expected {expected!r}"
        )


def test_assess_web_server_version_server_name_edge_cases() -> None:
    """Test server name matching edge cases."""
    edge_cases = [
        # Case variations with hyphens
        "Microsoft-IIS/5.0",
        "microsoft-iis/5.0",
        "MICROSOFT-IIS/5.0",
        "MiCrOsOfT-iIs/5.0",
        # Unknown servers
        "Unknown/1.0",
        "CustomServer/2.0",
        "ApacheTomcat/9.0",  # Contains "Apache" but not exact match
        "nginx-plus/1.0",    # Contains "nginx" but not exact match
        # Empty server name
        "/1.0",
        # Server name with spaces
        "Apache HTTPD/2.4",
    ]
    for header in edge_cases:
        result = _assess_web_server_version(header)
        expected = _oracle_assess(header)
        assert result == expected, (
            f"Mismatch for {header!r}: got {result!r}, expected {expected!r}"
        )