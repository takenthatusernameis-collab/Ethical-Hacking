#!/usr/bin/env python3
"""Independent oracle verification for ethscan.target pure helpers.

This script verifies the pure helper functions in ethscan.target against
stdlib oracles (ipaddress, urllib.parse, re) over a hostile input matrix.

Functions verified:
- normalize_host
- parse_url
- check_port
- check_target_host
- check_target_path
- strip_userinfo
- format_host_header

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import ipaddress
import random
import re
import sys
from urllib.parse import urlparse, SplitResult

from ethscan.target import (
    TargetSpecError,
    check_port,
    check_target_host,
    check_target_path,
    format_host_header,
    normalize_host,
    parse_url,
    strip_userinfo,
    url_port,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only
# ──────────────────────────────────────────────────────────────────────────────

_DISALLOWED_HOST_RE = re.compile(r"[\x00-\x20\x7f]")


def oracle_normalize_host(target: str, default_scheme: str = "https://") -> str | None:
    """Oracle for normalize_host using stdlib only.

    Returns the normalized host, or None if the target has no usable host.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = default_scheme + normalized

    try:
        parsed = urlparse(normalized)
    except ValueError:
        return None

    # Handle unbracketed IPv6 in authority (stdlib misparses this)
    netloc = parsed.netloc
    if netloc and "[" not in netloc:
        # Check if netloc is an IPv6 literal (possibly with port)
        port_part = None
        host_part = netloc
        if ":" in netloc:
            head, _, tail = netloc.rpartition(":")
            if tail and tail.isdigit():
                port_part = tail
                host_part = head
        candidates = [host_part, netloc]
        for candidate in candidates:
            try:
                ip = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if isinstance(ip, ipaddress.IPv6Address):
                # Rebuild netloc with bracketed IPv6
                if candidate == netloc:
                    new_netloc = f"[{candidate}]"
                else:
                    new_netloc = f"[{candidate}]:{port_part or ''}"
                parsed = parsed._replace(netloc=new_netloc)
                break

    host = (parsed.hostname or "").lower()
    return host if host else None


def oracle_parse_url(url: str) -> SplitResult | None:
    """Oracle for parse_url using stdlib only.

    Returns the parsed URL with IPv6 bracketing applied, or None if unparsable.
    Does NOT validate the port - that's done by url_port separately.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    netloc = parsed.netloc
    if netloc and "[" not in netloc:
        port_part = None
        host_part = netloc
        if ":" in netloc:
            head, _, tail = netloc.rpartition(":")
            if tail and tail.isdigit():
                port_part = tail
                host_part = head
        candidates = [host_part, netloc]
        for candidate in candidates:
            try:
                ip = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if isinstance(ip, ipaddress.IPv6Address):
                if candidate == netloc:
                    new_netloc = f"[{candidate}]"
                else:
                    new_netloc = f"[{candidate}]:{port_part or ''}"
                parsed = parsed._replace(netloc=new_netloc)
                break

    return parsed


def oracle_check_port(port: int | str) -> int | None:
    """Oracle for check_port using stdlib only.

    Returns the port number if valid, None if invalid.
    """
    try:
        if isinstance(port, str):
            value = int(port)
        else:
            value = port
    except ValueError:
        return None

    if value < 0 or value > 65535:
        return None

    return value


def oracle_check_target_host(target: str) -> bool:
    """Oracle for check_target_host using stdlib only.

    Returns True if host is acceptable (no spaces/control chars), False otherwise.
    """
    from urllib.parse import unquote

    authority = target.strip()
    scheme_re = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
    scheme = scheme_re.match(authority)
    if scheme is not None:
        authority = authority[scheme.end():]
    for delimiter in ("/", "?", "#"):
        index = authority.find(delimiter)
        if index != -1:
            authority = authority[:index]

    if _DISALLOWED_HOST_RE.search(authority):
        return False
    if _DISALLOWED_HOST_RE.search(unquote(authority)):
        return False
    return True


def oracle_check_target_path(target: str) -> bool:
    """Oracle for check_target_path using stdlib only.

    Returns True if path is acceptable, False otherwise.
    """
    remainder = target.strip()
    scheme_re = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
    scheme = scheme_re.match(remainder)
    if scheme is not None:
        remainder = remainder[scheme.end():]

    # Find start of path
    slash = remainder.find("/")
    if slash != -1:
        fragment = remainder.find("#", slash)
        if fragment != -1:
            path_part = remainder[slash:fragment]
        else:
            path_part = remainder[slash:]
    else:
        query = remainder.find("?")
        if query != -1:
            fragment = remainder.find("#", query)
            if fragment != -1:
                path_part = remainder[query:fragment]
            else:
                path_part = remainder[query:]
        else:
            path_part = ""

    if path_part and _DISALLOWED_HOST_RE.search(path_part):
        return False
    return True


def oracle_strip_userinfo(url: str) -> str:
    """Oracle for strip_userinfo using stdlib only."""
    scheme, separator, remainder = url.partition("://")
    if not separator:
        scheme, remainder = "", url
    end = len(remainder)
    for delimiter in ("/", "?", "#"):
        index = remainder.find(delimiter)
        if index != -1 and index < end:
            end = index
    authority = remainder[:end]
    if "@" not in authority:
        return url
    host = authority.rsplit("@", 1)[1]
    return f"{scheme}{separator}{host}{remainder[end:]}"


def oracle_format_host_header(host: str) -> str:
    """Oracle for format_host_header using stdlib only."""
    candidate = host.strip()
    if not candidate or candidate.startswith("["):
        return candidate
    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return host
    if isinstance(ip, ipaddress.IPv6Address):
        return f"[{candidate}]"
    return host


def oracle_url_port(parsed: SplitResult) -> int | None:
    """Oracle for url_port using stdlib only.

    Returns the port number if valid, None if invalid (no port or unparsable).
    """
    try:
        return parsed.port
    except ValueError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_hostile_targets() -> list[str]:
    """Generate a comprehensive matrix of hostile target strings."""
    targets = []

    # Empty/whitespace
    targets.extend(["", "   ", "\t\n", " \t \n "])

    # Schemes without hosts
    targets.extend([
        "http://", "https://", "redis://", "ftp://", "ssh://",
        "://", ":///", "://?", "://#",
    ])

    # Hosts with spaces
    targets.extend([
        "host name", "host\tname", "host\nname", "host\rname",
        " https://host name", "http://host name", "redis://host name",
        "host name:443", "https://host name:8443",
    ])

    # Hosts with control characters
    controls = ["\x00", "\x01", "\x09", "\x0a", "\x0d", "\x1f", "\x7f"]
    for c in controls:
        targets.extend([
            f"host{c}name",
            f"https://host{c}name",
            f"host{c}name:443",
            f"https://host{c}name:8443",
        ])

    # Percent-encoded control characters in host
    encoded_controls = ["%00", "%09", "%0a", "%0d", "%20", "%7f"]
    for ec in encoded_controls:
        targets.extend([
            f"{ec}host",
            f"host{ec}",
            f"host{ec}:443",
            f"https://{ec}host",
            f"https://host{ec}:8443",
        ])

    # IPv6 literals (bracketed and unbracketed)
    ipv6_literals = [
        "::1", "2001:db8::1", "fe80::1", "::ffff:192.0.2.1",
        "2001:db8:85a3::8a2e:370:7334",  # ends with :7334
        "[::1]", "[2001:db8::1]", "[fe80::1]",
        "[::1]:443", "[2001:db8::1]:8080",
    ]
    for ip in ipv6_literals:
        targets.extend([
            ip,
            f"https://{ip}",
            f"http://{ip}:8080",
            f"redis://{ip}:6379",
            f"{ip}/path",
            f"https://{ip}/path?q=1#frag",
        ])

    # IPv6 with zone IDs
    targets.extend([
        "fe80::1%eth0",
        "[fe80::1%eth0]",
        "https://fe80::1%eth0",
        "https://[fe80::1%eth0]:443",
    ])

    # IPv4 literals
    ipv4_literals = ["127.0.0.1", "192.168.1.1", "10.0.0.1", "0.0.0.0", "255.255.255.255"]
    for ip in ipv4_literals:
        targets.extend([
            ip,
            f"https://{ip}",
            f"http://{ip}:8080",
            f"{ip}:443",
            f"https://{ip}:8443/path",
        ])

    # DNS names (valid and edge cases)
    dns_names = [
        "example.com", "sub.example.com", "localhost",
        "host-with-dash.com", "sub.domain.example.co.uk",
        "xn--bcher-kva.ch",  # IDN
        "a", "a.b", "a.b.c",
        "example..com",  # malformed
        "....",  # malformed
    ]
    for name in dns_names:
        targets.extend([
            name,
            f"https://{name}",
            f"http://{name}:8080",
            f"{name}:443",
            f"https://{name}/path?q=1#frag",
        ])

    # Userinfo in authority
    userinfo_cases = [
        "user:pass@example.com",
        "user@example.com",
        "user:@example.com",
        "https://user:pass@example.com",
        "https://user@example.com/path?q=1#frag",
        "ftp://user:pass@files.example.com",
        "ssh://git@github.com/user/repo",
    ]
    targets.extend(userinfo_cases)

    # Path/query with spaces and control chars
    path_hostile = [
        "https://example.com/a b",
        "https://example.com/a\tb",
        "https://example.com/a\nb",
        "https://example.com/ho\x00st",
        "https://example.com/path\x7f",
        "https://example.com/?q=a b",
        "https://example.com/?q=a\tb",
        "http://example.com/a b",
        "example.com/a b",
        "https://example.com?q=a b",
    ]
    targets.extend(path_hostile)

    # Valid paths (should be accepted)
    path_valid = [
        "https://example.com/path",
        "https://example.com/a%20b",
        "https://example.com/?q=1",
        "https://example.com/path?query=1",
        "https://example.com/path#frag",
        "https://example.com/path?query=1#frag",
        "https://example.com?q=1",
        "https://example.com?q=1#frag",
    ]
    targets.extend(path_valid)

    # Port edge cases
    port_cases = [
        "host:0", "host:1", "host:80", "host:443", "host:65535",
        "host:65536", "host:99999", "host:-1",
        "host:notaport", "host:1.5", "host: ", "host:\t",
        "[::1]:0", "[::1]:65535", "[::1]:65536",
        "https://host:0", "https://host:65535", "https://host:65536",
    ]
    targets.extend(port_cases)

    # Unparseable URLs (unmatched brackets)
    targets.extend([
        "http://[::1",
        "https://[::1",
        "http://example.com]",
        "http://[::1/path",
        "https://[2001:db8::1",
    ])

    # Very long inputs
    long_host = "a" * 1000 + ".com"
    targets.extend([
        long_host,
        f"https://{long_host}",
        "https://example.com/" + "a" * 5000,
        "https://example.com/?" + "q=" + "a" * 5000,
    ])

    # Non-ASCII
    targets.extend([
        "https://exämple.com",
        "https://例子.测试",
        "https://xn--bcher-kva.ch",
        "https://example.com/日本語",
    ])

    # Mixed case
    targets.extend([
        "HTTPS://EXAMPLE.COM",
        "Http://Example.Com:8080",
        "ReDiS://LoCaLhOsT:6379",
    ])

    return targets


def generate_hostile_ports() -> list[int | str]:
    """Generate hostile port inputs."""
    ports = []

    # Valid range
    ports.extend(range(-10, 65545))  # covers boundaries

    # String forms
    for p in (-1, 0, 1, 80, 443, 65535, 65536, 99999):
        ports.append(str(p))

    # Non-numeric strings
    ports.extend(["notaport", "1.5", "", " ", "\t", "\n", "80\x00", "①②③"])

    # Unicode digits (accepted by Python's int())
    ports.extend(["１２３", "٠١٢", "०१२"])  # fullwidth, Arabic-Indic, Devanagari

    # Very large numbers
    ports.extend([10**10, 10**20, str(10**10), str(10**20)])

    # Negative strings
    ports.extend(["-1", "-100", "-65536"])

    return ports


def generate_hostile_hosts() -> list[str]:
    """Generate hostile host inputs for check_target_host."""
    hosts = []

    # Empty/whitespace
    hosts.extend(["", "   ", "\t\n"])

    # With spaces
    hosts.extend(["host name", " host", "host ", "hos t", "h o s t"])

    # With control characters
    controls = ["\x00", "\x01", "\x09", "\x0a", "\x0d", "\x1f", "\x7f"]
    for c in controls:
        hosts.extend([f"host{c}name", f"{c}host", f"host{c}"])

    # Percent-encoded
    encoded = ["%00", "%09", "%0a", "%0d", "%20", "%7f"]
    for e in encoded:
        hosts.extend([f"{e}host", f"host{e}", f"https://{e}host", f"host{e}:443"])

    # Valid hosts
    hosts.extend([
        "example.com", "localhost", "127.0.0.1", "::1", "[::1]",
        "sub.example.com", "host-with-dash.com", "fe80::1%eth0",
    ])

    # With schemes
    for h in ["example.com", "host name", "host\x00name"]:
        hosts.extend([f"https://{h}", f"http://{h}:8080", f"redis://{h}"])

    # Very long
    hosts.append("a" * 10000)

    return hosts


def generate_hostile_paths() -> list[str]:
    """Generate hostile path inputs for check_target_path."""
    paths = []

    # Valid paths (should pass)
    paths.extend([
        "example.com",
        "https://example.com",
        "https://example.com/",
        "https://example.com/path",
        "https://example.com/a%20b",
        "https://example.com/?q=1",
        "https://example.com/path?query=1",
        "https://example.com/path#frag",
        "https://example.com/path?query=1#frag",
    ])

    # Paths with spaces
    paths.extend([
        "https://example.com/a b",
        "https://example.com/a\tb",
        "https://example.com/a\nb",
        "https://example.com/a\rb",
        "https://example.com/ho\x00st",
        "https://example.com/path\x7f",
        "http://example.com/a b",
        "example.com/a b",
    ])

    # Query strings with spaces
    paths.extend([
        "https://example.com/?q=a b",
        "https://example.com/?q=a\tb",
        "https://example.com/path?q=a b",
        "https://example.com?q=a b",
    ])

    # Fragments with spaces (should be accepted - not sent to server)
    paths.extend([
        "https://example.com/path#has space",
        "https://example.com/path#tab\there",
        "https://example.com/#frag ment",
    ])

    # Percent-encoded in path (should be accepted - raw check only)
    paths.extend([
        "https://example.com/%00encoded",
        "https://example.com/a%20b",
        "https://example.com/%00%09%0a",
    ])

    # Very long
    paths.append("https://example.com/" + "a" * 10000)

    return paths


def generate_hostile_urls_for_strip_userinfo() -> list[str]:
    """Generate hostile URLs for strip_userinfo."""
    urls = []

    # Basic cases
    urls.extend([
        "http://user:pass@example.com",
        "https://user:pass@example.com/path?q=1#frag",
        "https://user@example.com",
        "user:pass@example.com",
        "user@example.com",
        "https://example.com",
        "https://example.com/path",
        "https://example.com:8443",
        "https://[::1]:443",
        "https://example.com/a@b",
        "example.com",
    ])

    # Edge cases
    urls.extend([
        "http://:@example.com",  # empty user, empty pass
        "http://user:@example.com",  # empty pass
        "http://:pass@example.com",  # empty user
        "https://user:pass@example.com:8080/path?q=1#frag",
        "ftp://user:pass@files.example.com",
        "ssh://git@github.com/user/repo",
        "https://user:pass@[::1]:443",
        "https://user:pass@fe80::1%eth0",
    ])

    # Multiple @ in path (should only strip first @ in authority)
    urls.extend([
        "https://example.com/user@domain.com",
        "https://user:pass@example.com/path@more",
        "https://example.com/a@b/c@d",
    ])

    # No scheme
    urls.extend([
        "user:pass@example.com/path",
        "user@example.com?query=1",
    ])

    return urls


def generate_hostile_hosts_for_format() -> list[str]:
    """Generate hostile host inputs for format_host_header."""
    hosts = []

    # IPv6 literals (should be bracketed)
    hosts.extend(["::1", "2001:db8::1", "fe80::1", "::ffff:192.0.2.1"])

    # Already bracketed (should stay same)
    hosts.extend(["[::1]", "[2001:db8::1]", "[fe80::1]"])

    # IPv6 with zone IDs (zone should be stripped)
    hosts.extend(["fe80::1%eth0", "fe80::1%en0", "[fe80::1%eth0]"])

    # IPv4 literals (should stay same)
    hosts.extend(["127.0.0.1", "192.168.1.1", "10.0.0.1", "0.0.0.0", "255.255.255.255"])

    # DNS names (should stay same)
    hosts.extend(["example.com", "localhost", "sub.example.com", "host-with-dash.com"])

    # Empty/whitespace
    hosts.extend(["", "   ", "\t\n"])

    # Invalid/weird
    hosts.extend(["notanip", "2001:db8::1::2", ":::", "host\x00name"])

    # Already bracketed with zone ID (weird but handle gracefully)
    hosts.extend(["[fe80::1%eth0]", "[::1%eth0]"])

    return hosts


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_normalize_host() -> list[tuple[str, str, str]]:
    """Verify normalize_host against oracle.

    Returns list of mismatches: (target, our_result, oracle_result)
    """
    mismatches = []
    targets = generate_hostile_targets()

    # Add random targets for broader coverage
    rng = random.Random(20261126)
    schemes = ("http", "https", "redis", "ftp", "ssh", "ldap", "smtp", "mongodb")
    hosts = (
        "example.com", "sub.example.com", "localhost", "127.0.0.1",
        "192.168.1.1", "[::1]", "[2001:db8::1]", "[fe80::1]",
        "host-with-dash.com", "xn--bcher-kva.ch",
    )
    paths = ("", "/", "/path", "/path?q=1", "/path?q=1#frag", "?q=1", "#frag")
    ports = ("", ":80", ":443", ":6379", ":8443", ":8080", ":9999")
    userinfos = ("", "user:", "user:pass", "user@")

    for _ in range(5000):
        scheme = rng.choice(schemes)
        host = rng.choice(hosts)
        port = rng.choice(ports)
        path = rng.choice(paths)
        userinfo = rng.choice(userinfos)

        if userinfo:
            auth = f"{userinfo}@{host}{port}"
        else:
            auth = f"{host}{port}"
        url = f"{scheme}://{auth}{path}"
        targets.append(url)

    for target in targets:
        try:
            our_result = normalize_host(target)
        except TargetSpecError:
            our_result = None
        except Exception as e:
            mismatches.append((target, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_normalize_host(target)

        if our_result != oracle_result:
            mismatches.append((target, str(our_result), str(oracle_result)))

    return mismatches


def verify_parse_url() -> list[tuple[str, str, str]]:
    """Verify parse_url against oracle.

    Returns list of mismatches: (url, our_netloc, oracle_netloc)
    """
    mismatches = []
    targets = generate_hostile_targets()

    # Add more URL-specific cases
    rng = random.Random(20261126 + 1)
    schemes = ("http", "https", "redis", "ftp", "ssh", "ldap", "smtp", "mongodb")
    hosts = (
        "example.com", "sub.example.com", "localhost", "127.0.0.1",
        "192.168.1.1", "[::1]", "[2001:db8::1]", "[fe80::1]",
        "host-with-dash.com", "xn--bcher-kva.ch", "2001:db8::1", "::1", "fe80::1",
    )
    paths = ("", "/", "/path", "/path?q=1", "/path?q=1#frag", "?q=1", "#frag")
    ports = ("", ":80", ":443", ":6379", ":8443", ":8080", ":9999")
    userinfos = ("", "user:", "user:pass", "user@")

    for _ in range(5000):
        scheme = rng.choice(schemes)
        host = rng.choice(hosts)
        port = rng.choice(ports)
        path = rng.choice(paths)
        userinfo = rng.choice(userinfos)

        if userinfo:
            auth = f"{userinfo}@{host}{port}"
        else:
            auth = f"{host}{port}"
        url = f"{scheme}://{auth}{path}"
        targets.append(url)

    for url in targets:
        try:
            our_parsed = parse_url(url)
            # Don't access .port here - that's validated by url_port separately
            our_result = (our_parsed.scheme, our_parsed.netloc, our_parsed.path,
                         our_parsed.query, our_parsed.fragment, our_parsed.hostname)
        except TargetSpecError:
            our_result = None
        except Exception as e:
            mismatches.append((url, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_parsed = oracle_parse_url(url)
        if oracle_parsed is None:
            oracle_result = None
        else:
            oracle_result = (oracle_parsed.scheme, oracle_parsed.netloc, oracle_parsed.path,
                           oracle_parsed.query, oracle_parsed.fragment, oracle_parsed.hostname)

        if our_result != oracle_result:
            mismatches.append((url, str(our_result), str(oracle_result)))

    return mismatches


def verify_check_port() -> list[tuple[str, str, str]]:
    """Verify check_port against oracle.

    Returns list of mismatches: (port_input, our_result, oracle_result)
    """
    mismatches = []
    ports = generate_hostile_ports()

    for port in ports:
        port_str = repr(port)

        try:
            our_result = check_port(port)
        except TargetSpecError:
            our_result = None
        except Exception as e:
            mismatches.append((port_str, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_check_port(port)

        if our_result != oracle_result:
            mismatches.append((port_str, str(our_result), str(oracle_result)))

    return mismatches


def verify_url_port() -> list[tuple[str, str, str]]:
    """Verify url_port against oracle.

    Returns list of mismatches: (url, our_result, oracle_result)
    """
    mismatches = []
    targets = generate_hostile_targets()

    # Add more URL-specific cases
    rng = random.Random(20261126 + 2)
    schemes = ("http", "https", "redis", "ftp", "ssh", "ldap", "smtp", "mongodb")
    hosts = (
        "example.com", "sub.example.com", "localhost", "127.0.0.1",
        "192.168.1.1", "[::1]", "[2001:db8::1]", "[fe80::1]",
        "host-with-dash.com", "xn--bcher-kva.ch", "2001:db8::1", "::1", "fe80::1",
    )
    paths = ("", "/", "/path", "/path?q=1", "/path?q=1#frag", "?q=1", "#frag")
    ports = ("", ":80", ":443", ":6379", ":8443", ":8080", ":9999", ":notaport", ":65536", ":-1")
    userinfos = ("", "user:", "user:pass", "user@")

    for _ in range(5000):
        scheme = rng.choice(schemes)
        host = rng.choice(hosts)
        port = rng.choice(ports)
        path = rng.choice(paths)
        userinfo = rng.choice(userinfos)

        if userinfo:
            auth = f"{userinfo}@{host}{port}"
        else:
            auth = f"{host}{port}"
        url = f"{scheme}://{auth}{path}"
        targets.append(url)

    for url in targets:
        try:
            our_parsed = parse_url(url)
            try:
                our_result = url_port(our_parsed)
            except TargetSpecError:
                our_result = None
        except TargetSpecError:
            # parse_url failed, so url_port wouldn't be called
            our_result = "PARSE_FAILED"
        except Exception as e:
            mismatches.append((url, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_parsed = oracle_parse_url(url)
        if oracle_parsed is None:
            oracle_result = "PARSE_FAILED"
        else:
            oracle_result = oracle_url_port(oracle_parsed)

        if our_result != oracle_result:
            mismatches.append((url, str(our_result), str(oracle_result)))

    return mismatches


def verify_check_target_host() -> list[tuple[str, str, str]]:
    """Verify check_target_host against oracle.

    Returns list of mismatches: (target, our_result, oracle_result)
    where result is True (accepted) or False (rejected)
    """
    mismatches = []
    targets = generate_hostile_hosts()

    for target in targets:
        try:
            check_target_host(target)
            our_result = True
        except TargetSpecError:
            our_result = False
        except Exception as e:
            mismatches.append((target, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_check_target_host(target)

        if our_result != oracle_result:
            mismatches.append((target, str(our_result), str(oracle_result)))

    return mismatches


def verify_check_target_path() -> list[tuple[str, str, str]]:
    """Verify check_target_path against oracle.

    Returns list of mismatches: (target, our_result, oracle_result)
    where result is True (accepted) or False (rejected)
    """
    mismatches = []
    targets = generate_hostile_paths()

    for target in targets:
        try:
            check_target_path(target)
            our_result = True
        except TargetSpecError:
            our_result = False
        except Exception as e:
            mismatches.append((target, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_check_target_path(target)

        if our_result != oracle_result:
            mismatches.append((target, str(our_result), str(oracle_result)))

    return mismatches


def verify_strip_userinfo() -> list[tuple[str, str, str]]:
    """Verify strip_userinfo against oracle.

    Returns list of mismatches: (url, our_result, oracle_result)
    """
    mismatches = []
    urls = generate_hostile_urls_for_strip_userinfo()

    for url in urls:
        try:
            our_result = strip_userinfo(url)
        except Exception as e:
            mismatches.append((url, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_strip_userinfo(url)

        if our_result != oracle_result:
            mismatches.append((url, our_result, oracle_result))

    return mismatches


def verify_format_host_header() -> list[tuple[str, str, str]]:
    """Verify format_host_header against oracle.

    Returns list of mismatches: (host, our_result, oracle_result)
    """
    mismatches = []
    hosts = generate_hostile_hosts_for_format()

    for host in hosts:
        try:
            our_result = format_host_header(host)
        except Exception as e:
            mismatches.append((host, f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_format_host_header(host)

        if our_result != oracle_result:
            mismatches.append((host, our_result, oracle_result))

    return mismatches


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches = []

    print("Verifying normalize_host...", file=sys.stderr)
    mismatches = verify_normalize_host()
    if mismatches:
        all_mismatches.extend([("normalize_host",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying parse_url...", file=sys.stderr)
    mismatches = verify_parse_url()
    if mismatches:
        all_mismatches.extend([("parse_url",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying check_port...", file=sys.stderr)
    mismatches = verify_check_port()
    if mismatches:
        all_mismatches.extend([("check_port",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying url_port...", file=sys.stderr)
    mismatches = verify_url_port()
    if mismatches:
        all_mismatches.extend([("url_port",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying check_target_host...", file=sys.stderr)
    mismatches = verify_check_target_host()
    if mismatches:
        all_mismatches.extend([("check_target_host",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying check_target_path...", file=sys.stderr)
    mismatches = verify_check_target_path()
    if mismatches:
        all_mismatches.extend([("check_target_path",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying strip_userinfo...", file=sys.stderr)
    mismatches = verify_strip_userinfo()
    if mismatches:
        all_mismatches.extend([("strip_userinfo",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying format_host_header...", file=sys.stderr)
    mismatches = verify_format_host_header()
    if mismatches:
        all_mismatches.extend([("format_host_header",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    if all_mismatches:
        print(f"\n=== TOTAL MISMATCHES: {len(all_mismatches)} ===", file=sys.stderr)
        for func, inp, ours, oracle in all_mismatches[:20]:  # Show first 20
            print(f"  {func}({inp!r}) => ours={ours!r}, oracle={oracle!r}", file=sys.stderr)
        if len(all_mismatches) > 20:
            print(f"  ... and {len(all_mismatches) - 20} more", file=sys.stderr)
        return 1

    print("\n=== ALL VERIFICATIONS PASSED ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())