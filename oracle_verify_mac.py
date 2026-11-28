#!/usr/bin/env python3
"""Independent oracle verification for ethscan.mac pure helpers.

This script verifies the pure helper functions in ethscan.mac against
stdlib oracles (ipaddress, re) over a hostile input matrix.

Functions verified:
- _is_mac_address
- _strip_mac_port
- _is_ip_address
- _extract_oui
- _normalize_mac_for_api

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import ipaddress
import random
import re
import sys

from ethscan.mac import (
    _is_mac_address,
    _strip_mac_port,
    _is_ip_address,
    _extract_oui,
    _normalize_mac_for_api,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only
# ──────────────────────────────────────────────────────────────────────────────

_MAC_RE = re.compile(r"^[0-9a-fA-F]{12}$")
_MAC_SEPS = [":", "-", "."]


def oracle_is_mac_address(value: str) -> bool:
    """Oracle for _is_mac_address using stdlib only.

    A MAC address is 6 octets (12 hex digits) optionally separated by
    colons, dashes, or dots. Only ASCII hex digits are accepted.
    Whitespace, signs, and other characters are rejected.
    """
    if not isinstance(value, str):
        return False
    # Remove all valid separators
    cleaned = value.replace(":", "").replace("-", "").replace(".", "")
    if len(cleaned) != 12:
        return False
    # Only accept ASCII hex digits (strict, like the implementation)
    hex_digits = frozenset("0123456789abcdefABCDEF")
    return set(cleaned) <= hex_digits


def oracle_strip_mac_port(value: str) -> str:
    """Oracle for _strip_mac_port using stdlib only.

    Strips a trailing ':port' from a MAC address string. A MAC has 6 groups
    (5 separators), while host:port has exactly 1 colon. If the value before
    the last colon is a valid MAC, drop the port part.
    """
    if not value:
        return value
    head, sep, tail = value.rpartition(":")
    if sep and oracle_is_mac_address(head):
        return head
    return value


def oracle_is_ip_address(value: str) -> bool:
    """Oracle for _is_ip_address using stdlib only."""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def oracle_extract_oui(mac: str) -> str:
    """Oracle for _extract_oui using stdlib only.

    Returns the first 6 hex characters (24-bit OUI, first 3 octets).
    """
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    return cleaned[:6]


def oracle_normalize_mac_for_api(mac: str) -> str:
    """Oracle for _normalize_mac_for_api using stdlib only.

    Returns MAC with all separators stripped and lowercased.
    """
    return mac.replace(":", "").replace("-", "").replace(".", "").lower()


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

def generate_mac_inputs() -> list[str]:
    """Generate a comprehensive matrix of MAC-like and hostile inputs."""
    inputs = []

    # Valid MACs (various formats)
    valid_macs = [
        "00:1A:2B:3C:4D:5E",
        "00-1A-2B-3C-4D-5E",
        "00.1A.2B.3C.4D.5E",
        "001A2B3C4D5E",
        "aa:bb:cc:dd:ee:ff",
        "AA-BB-CC-DD-EE-FF",
        "00:00:00:00:00:00",
        "ff:ff:ff:ff:ff:ff",
        "01:23:45:67:89:ab",
        "01-23-45-67-89-ab",
        "01.23.45.67.89.ab",
        "0123456789ab",
    ]
    inputs.extend(valid_macs)

    # Mixed case
    for mac in ["00:1a:2B:3C:4d:5E", "AA:bb:CC:dd:EE:ff"]:
        inputs.append(mac)

    # Invalid: wrong length (after cleaning)
    invalid_length = [
        "",  # empty
        "00:1A:2B",  # too short
        "00:1A:2B:3C:4D",  # 5 octets
        "00:1A:2B:3C:4D:5E:6F",  # 7 octets
        "00:1A:2B:3C:4D:5E:6F:7G",  # 8 octets
        "001A2B3C4D5",  # 11 chars
        "001A2B3C4D5E6",  # 13 chars
    ]
    inputs.extend(invalid_length)

    # Invalid: non-hex characters
    invalid_hex = [
        "GG:1A:2B:3C:4D:5E",
        "00:1A:2B:3C:4D:5G",
        "ZZ:ZZ:ZZ:ZZ:ZZ:ZZ",
        "00:1A:2B:3C:4D:5Z",
        "00-1A-2B-3C-4D-5G",
        "00.1A.2B.3C.4D.5G",
        "0G1A2B3C4D5E",
        "00:1A:2B:3C:4D:5!",  # special char
        "00:1A:2B:3C:4D:5 ",  # space
        "00:1A:2B:3C:4D:5\t",  # tab
    ]
    inputs.extend(invalid_hex)

    # Invalid: inconsistent/mixed separators
    mixed_seps = [
        "00:1A-2B:3C:4D:5E",
        "00:1A:2B-3C:4D:5E",
        "00.1A:2B:3C:4D:5E",
        "00:1A:2B:3C.4D:5E",
        "00:1A:2B:3C:4D-5E",
    ]
    inputs.extend(mixed_seps)

    # Invalid: trailing/leading separators
    edge_seps = [
        ":00:1A:2B:3C:4D:5E",
        "00:1A:2B:3C:4D:5E:",
        "-00-1A-2B-3C-4D-5E",
        "00-1A-2B-3C-4D-5E-",
        ".00.1A.2B.3C.4D.5E",
        "00.1A.2B.3C.4D.5E.",
    ]
    inputs.extend(edge_seps)

    # Hostnames and IPs (should be False)
    non_macs = [
        "example.com",
        "localhost",
        "192.168.1.1",
        "8.8.8.8",
        "::1",
        "2001:db8::1",
        "[::1]",
        "fe80::1%eth0",
        "sub.example.com",
        "host-with-dash.com",
        "xn--bcher-kva.ch",
    ]
    inputs.extend(non_macs)

    # MAC-like with port (for _strip_mac_port testing)
    mac_with_port = [
        "00:1A:2B:3C:4D:5E:8080",
        "00:1a:2b:3c:4d:5e:1",
        "00-1A-2B-3C-4D-5E:8080",
        "00.1A.2B.3C.4D.5E:8080",
        "001A2B3C4D5E:8080",
        "00:1A:2B:3C:4D:5E:65535",
        "00:1A:2B:3C:4D:5E:0",
    ]
    inputs.extend(mac_with_port)

    # Non-MAC with port (should be unchanged)
    non_mac_with_port = [
        "example.com:8080",
        "8.8.8.8:53",
        "[fd00::1]:8443",
        "localhost:80",
        "sub.example.com:443",
        "192.168.1.1:8080",
        "[::1]:443",
    ]
    inputs.extend(non_mac_with_port)

    # Random generated cases
    rng = random.Random(20261126)
    hex_chars = "0123456789abcdefABCDEF"
    seps = [":", "-", ".", ""]

    for _ in range(2000):
        sep = rng.choice(seps)
        # Generate 12 hex chars
        mac_chars = "".join(rng.choice(hex_chars) for _ in range(12))
        if sep:
            # Insert separator every 2 chars
            parts = [mac_chars[i:i+2] for i in range(0, 12, 2)]
            mac = sep.join(parts)
        else:
            mac = mac_chars
        inputs.append(mac)

        # Sometimes add a port
        if rng.random() < 0.2:
            port = rng.randint(0, 65535)
            inputs.append(f"{mac}:{port}")

    # Random non-MAC strings
    for _ in range(500):
        length = rng.randint(1, 30)
        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.:-[]% "
        s = "".join(rng.choice(chars) for _ in range(length))
        inputs.append(s)

    return inputs


def generate_ip_inputs() -> list[str]:
    """Generate IP address inputs for _is_ip_address testing."""
    inputs = []

    # Valid IPv4
    valid_v4 = [
        "0.0.0.0",
        "127.0.0.1",
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "255.255.255.255",
        "8.8.8.8",
        "1.1.1.1",
    ]
    inputs.extend(valid_v4)

    # Valid IPv6
    valid_v6 = [
        "::1",
        "::",
        "2001:db8::1",
        "2001:db8:85a3::8a2e:370:7334",
        "fe80::1",
        "fd00::1",
        "::ffff:192.0.2.1",
        "2001:4860:4860::8888",
        "2606:4700:4700::1111",
    ]
    inputs.extend(valid_v6)

    # IPv6 with zone IDs
    zone_ids = [
        "fe80::1%eth0",
        "fe80::1%en0",
        "fe80::1%wlan0",
        "fe80::1%1",
        "fe80::1%2",
    ]
    inputs.extend(zone_ids)

    # Invalid IPs
    invalid = [
        "",  # empty
        "192.168.1",  # incomplete
        "192.168.1.256",  # octet > 255
        "256.168.1.1",  # octet > 255
        "192.168.1.1.1",  # 5 octets
        "::1::1",  # double ::
        "2001:db8:::1",  # triple :
        "gggg::1",  # non-hex
        "192.168.1.",  # trailing dot
        ".192.168.1.1",  # leading dot
        "192..168.1.1",  # double dot
        "2001:db8:gggg::1",  # non-hex in IPv6
        "not-an-ip",
        "localhost",
        "example.com",
        "00:1A:2B:3C:4D:5E",  # MAC
        "00-1A-2B-3C-4D-5E",
        "001A2B3C4D5E",
    ]
    inputs.extend(invalid)

    # Bracketed IPv6 (not valid for ip_address)
    bracketed = [
        "[::1]",
        "[2001:db8::1]",
        "[fe80::1]",
        "[::1]:443",
    ]
    inputs.extend(bracketed)

    # Random generated
    rng = random.Random(20261126 + 1)
    for _ in range(1000):
        # Random IPv4-like
        if rng.random() < 0.5:
            ip = ".".join(str(rng.randint(0, 300)) for _ in range(4))
            inputs.append(ip)
        else:
            # Random IPv6-like
            parts = []
            for _ in range(8):
                parts.append("".join(rng.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(1, 4))))
            ip = ":".join(parts)
            if rng.random() < 0.3:
                ip = "::" + ip
            inputs.append(ip)

    return inputs


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_is_mac_address() -> list[tuple[str, str, str]]:
    """Verify _is_mac_address against oracle."""
    mismatches = []
    inputs = generate_mac_inputs()

    for inp in inputs:
        try:
            our_result = _is_mac_address(inp)
        except Exception as e:
            mismatches.append((repr(inp), f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_is_mac_address(inp)

        if our_result != oracle_result:
            mismatches.append((repr(inp), str(our_result), str(oracle_result)))

    return mismatches


def verify_strip_mac_port() -> list[tuple[str, str, str]]:
    """Verify _strip_mac_port against oracle."""
    mismatches = []
    inputs = generate_mac_inputs()

    for inp in inputs:
        try:
            our_result = _strip_mac_port(inp)
        except Exception as e:
            mismatches.append((repr(inp), f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_strip_mac_port(inp)

        if our_result != oracle_result:
            mismatches.append((repr(inp), repr(our_result), repr(oracle_result)))

    return mismatches


def verify_is_ip_address() -> list[tuple[str, str, str]]:
    """Verify _is_ip_address against oracle."""
    mismatches = []
    inputs = generate_ip_inputs()

    for inp in inputs:
        try:
            our_result = _is_ip_address(inp)
        except Exception as e:
            mismatches.append((repr(inp), f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_is_ip_address(inp)

        if our_result != oracle_result:
            mismatches.append((repr(inp), str(our_result), str(oracle_result)))

    return mismatches


def verify_extract_oui() -> list[tuple[str, str, str]]:
    """Verify _extract_oui against oracle.

    Only test with valid MAC addresses since the function assumes valid input.
    """
    mismatches = []
    inputs = generate_mac_inputs()

    for inp in inputs:
        # Only test with inputs that are valid MACs per the oracle
        if not oracle_is_mac_address(inp):
            continue

        try:
            our_result = _extract_oui(inp)
        except Exception as e:
            mismatches.append((repr(inp), f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_extract_oui(inp)

        if our_result != oracle_result:
            mismatches.append((repr(inp), repr(our_result), repr(oracle_result)))

    return mismatches


def verify_normalize_mac_for_api() -> list[tuple[str, str, str]]:
    """Verify _normalize_mac_for_api against oracle.

    Only test with valid MAC addresses since the function assumes valid input.
    """
    mismatches = []
    inputs = generate_mac_inputs()

    for inp in inputs:
        # Only test with inputs that are valid MACs per the oracle
        if not oracle_is_mac_address(inp):
            continue

        try:
            our_result = _normalize_mac_for_api(inp)
        except Exception as e:
            mismatches.append((repr(inp), f"EXCEPTION: {type(e).__name__}: {e}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_normalize_mac_for_api(inp)

        if our_result != oracle_result:
            mismatches.append((repr(inp), repr(our_result), repr(oracle_result)))

    return mismatches


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches = []

    print("Verifying _is_mac_address...", file=sys.stderr)
    mismatches = verify_is_mac_address()
    if mismatches:
        all_mismatches.extend([("_is_mac_address",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _strip_mac_port...", file=sys.stderr)
    mismatches = verify_strip_mac_port()
    if mismatches:
        all_mismatches.extend([("_strip_mac_port",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _is_ip_address...", file=sys.stderr)
    mismatches = verify_is_ip_address()
    if mismatches:
        all_mismatches.extend([("_is_ip_address",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _extract_oui...", file=sys.stderr)
    mismatches = verify_extract_oui()
    if mismatches:
        all_mismatches.extend([("_extract_oui",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    print("Verifying _normalize_mac_for_api...", file=sys.stderr)
    mismatches = verify_normalize_mac_for_api()
    if mismatches:
        all_mismatches.extend([("_normalize_mac_for_api",) + m for m in mismatches])
        print(f"  FAIL: {len(mismatches)} mismatches", file=sys.stderr)
    else:
        print("  OK", file=sys.stderr)

    if all_mismatches:
        print(f"\n=== TOTAL MISMATCHES: {len(all_mismatches)} ===", file=sys.stderr)
        for func, inp, ours, oracle in all_mismatches[:20]:
            print(f"  {func}({inp}) => ours={ours}, oracle={oracle}", file=sys.stderr)
        if len(all_mismatches) > 20:
            print(f"  ... and {len(all_mismatches) - 20} more", file=sys.stderr)
        return 1

    print("\n=== ALL VERIFICATIONS PASSED ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())