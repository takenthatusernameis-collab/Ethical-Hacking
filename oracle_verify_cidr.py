#!/usr/bin/env python3
"""Independent oracle verification for ethscan.cidr pure helpers.

This script verifies the pure helper functions in ethscan.cidr against
stdlib oracles (ipaddress only) over a hostile input matrix.

Functions verified:
- normalize_cidr
- _contains_ip
- _subtract_networks
- run_cidr

The script runs silently on success, prints mismatches on failure, and
exits with non-zero code if any oracle mismatch is found.
"""

from __future__ import annotations

import ipaddress
import random
import sys
from typing import NamedTuple, cast

from ethscan.cidr import (
    CidrSpecError,
    _contains_ip,
    _subtract_networks,
    normalize_cidr,
    run_cidr,
)

# ──────────────────────────────────────────────────────────────────────────────
# Oracle implementations using stdlib only (ipaddress)
# ──────────────────────────────────────────────────────────────────────────────

# Sentinel used by oracles to signal an invalid input (mirrors CidrSpecError).
_ORACLE_ERROR = "__ORACLE_ERROR__"


def oracle_normalize_cidr(value: str) -> str | None:
    """Oracle for normalize_cidr using stdlib ipaddress only.

    Returns the canonical CIDR string, or None if the value is invalid.
    """
    value = value.strip()
    if not value:
        return None
    if "/" not in value:
        try:
            addr = ipaddress.ip_address(value)
            value = value + ("/32" if addr.version == 4 else "/128")
        except ValueError:
            value = value + "/128"
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None
    return str(network)


def oracle_contains_ip(network: ipaddress.IPv4Network | ipaddress.IPv6Network, ip: str) -> bool:
    """Oracle for _contains_ip using stdlib ipaddress only."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr in network


def oracle_parse_networks(cidrs: list[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None:
    """Parse a list of CIDR strings into network objects, or None on any error."""
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in cidrs:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            return None
    return networks


def oracle_subtract_networks(minuend_cidrs: list[str], subtrahend_cidrs: list[str]) -> list[str] | None:
    """Oracle for _subtract_networks using stdlib ipaddress only.

    Mirrors the set-difference spec: addresses in minuend but not in subtrahend.
    Returns the sorted list of resulting CIDR strings, or None on parse error.
    """
    minuend = oracle_parse_networks(minuend_cidrs)
    subtrahend = oracle_parse_networks(subtrahend_cidrs)
    if minuend is None or subtrahend is None:
        return None

    if not minuend:
        return []
    if not subtrahend:
        return sorted(str(n) for n in sorted(minuend, key=lambda n: n.network_address))

    result: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for m_net in sorted(minuend, key=lambda n: n.network_address):
        remaining = [m_net]
        for s_net in sorted(subtrahend, key=lambda n: n.network_address):
            if m_net.version != s_net.version:
                continue
            if not m_net.overlaps(s_net):
                continue
            new_remaining: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
            for r_net in remaining:
                if not r_net.overlaps(s_net):
                    new_remaining.append(r_net)
                    continue
                try:
                    diffs = list(r_net.address_exclude(s_net))  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    diffs = []
                if diffs:
                    new_remaining.extend(diffs)  # type: ignore[arg-type]
            remaining = new_remaining
            if not remaining:
                break
        result.extend(remaining)
    return sorted(str(n) for n in sorted(result, key=lambda n: n.network_address))


def oracle_format_network_info(network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> dict[str, object]:
    """Oracle for _format_network_info using stdlib ipaddress only."""
    is_v4 = network.version == 4
    netmask = str(network.netmask)
    broadcast = str(network.broadcast_address) if is_v4 and network.broadcast_address else None
    wildcard = str(network.hostmask)

    num = network.num_addresses
    if num == 1:
        usable_hosts = 1
    elif num == 2:
        if is_v4:
            usable_hosts = 2
        else:
            usable_hosts = 1
    elif is_v4:
        usable_hosts = num - 2
    else:
        usable_hosts = num - 1

    if num > 2:
        first_host = str(network[1])
        last_host = str(network[-2] if is_v4 else network[-1])
    elif num == 2:
        if is_v4:
            first_host = str(network[0])
            last_host = str(network[1])
        else:
            first_host = str(network[1])
            last_host = str(network[1])
    else:
        first_host = str(network.network_address)
        last_host = str(network.network_address)

    return {
        "network_address": str(network.network_address),
        "netmask": netmask,
        "broadcast_address": broadcast,
        "wildcard_mask": wildcard,
        "first_host": first_host,
        "last_host": last_host,
        "usable_host_count": usable_hosts,
        "total_addresses": num,
        "prefixlen": network.prefixlen,
        "is_private": network.is_private,
    }


def oracle_run_cidr(
    cidr: str, contains: str | None, diff: str | None
) -> dict[str, object] | None:
    """Oracle for run_cidr using stdlib ipaddress only.

    Returns the structured result dict, or None if any input is invalid
    (mirroring run_cidr raising CidrSpecError).
    """
    normalized = oracle_normalize_cidr(cidr)
    if normalized is None:
        return None
    network = ipaddress.ip_network(normalized, strict=False)
    info = oracle_format_network_info(network)

    result: dict[str, object] = {
        "cidr": normalized,
        "ip_version": "IPv4" if network.version == 4 else "IPv6",
        "network": info,
    }

    if contains is not None:
        contains_stripped = contains.strip()
        result["contains"] = {
            "ip": contains_stripped,
            "in_network": oracle_contains_ip(network, contains_stripped),
        }

    if diff is not None:
        diff_normalized = oracle_normalize_cidr(diff)
        if diff_normalized is None:
            return None
        diff_result = oracle_subtract_networks([normalized], [diff_normalized])
        if diff_result is None:
            return None
        total_diff_addresses = 0
        for part in diff_result:
            try:
                total_diff_addresses += ipaddress.ip_network(part, strict=False).num_addresses
            except ValueError:
                total_diff_addresses += 0
        result["diff"] = {
            "diff_cidr": diff_normalized,
            "difference": diff_result,
            "difference_network_count": len(diff_result),
            "total_diff_addresses": total_diff_addresses,
        }

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Hostile input generators
# ──────────────────────────────────────────────────────────────────────────────

class Case(NamedTuple):
    cidr: str
    contains: str | None
    diff: str | None


def generate_cidr_inputs() -> list[str]:
    """Generate a comprehensive matrix of CIDR-like and hostile inputs."""
    inputs: list[str] = []

    # Valid IPv4 CIDRs
    valid_v4 = [
        "0.0.0.0/0", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "192.168.1.0/24", "192.168.1.1/24",  # host bits set (strict=False ok)
        "127.0.0.1/32", "255.255.255.255/32", "8.8.8.8/32",
        "10.0.0.0/1", "10.0.0.0/31", "10.0.0.0/30",
    ]
    inputs.extend(valid_v4)

    # Valid IPv6 CIDRs
    valid_v6 = [
        "::/0", "::1/128", "2001:db8::/32", "2001:db8::1/128",
        "fe80::/10", "ff00::/8", "2001:db8:85a3::8a2e:370:7334/64",
    ]
    inputs.extend(valid_v6)

    # Bare IPs (treated as /32 or /128)
    bare_ips = [
        "192.168.1.1", "10.0.0.1", "0.0.0.0", "255.255.255.255",
        "::1", "2001:db8::1", "fe80::1", "::", "ff00::1",
    ]
    inputs.extend(bare_ips)

    # Empty / whitespace
    inputs.extend(["", "   ", "\t\n", " \t \n ", "\x00"])

    # Invalid: non-CIDR garbage
    garbage = [
        "notacidr", "192.168.1", "192.168.1.256/24", "256.168.1.1/24",
        "192.168.1.1.1/24", "192.168.1.1/", "/24", "192.168.1.1/33",
        "192.168.1.1/-1", "192.168.1.1/abc", "192.168.1.1/ 24",
        "192.168.1.1 /24", " 192.168.1.1/24 ", "192.168.1.1/24 ",
        "ipv6::gggg/64", "::1/129", "fe80::1%eth0/64",
        "[::1]/64", "[2001:db8::1]/64", "192.168.1.1/24/extra",
    ]
    inputs.extend(garbage)

    # Control characters
    controls = ["\x00", "\x01", "\x09", "\x0a", "\x0d", "\x1f", "\x7f"]
    for c in controls:
        inputs.extend([f"192.168.1.1{c}/24", f"{c}192.168.1.1/24", f"192.168.1.1/24{c}"])

    # Very long
    inputs.append("192.168.1." + "1" * 5000 + "/24")
    inputs.append("a" * 10000 + "/24")

    # Non-ASCII / Unicode
    inputs.extend([
        "exämple.com/24", "例子.测试/24", "192.168.1.１/24",
        "192.168.1.1/२४",  # Devanagari digits
    ])

    # Random generated
    rng = random.Random(20261126)
    for _ in range(2000):
        if rng.random() < 0.5:
            ip = ".".join(str(rng.randint(0, 300)) for _ in range(4))
            prefix = str(rng.randint(-5, 40))
        else:
            parts = [
                "".join(rng.choice("0123456789abcdef") for _ in range(rng.randint(1, 4)))
                for _ in range(8)
            ]
            ip = ":".join(parts)
            prefix = str(rng.randint(-5, 130))
        sep = rng.choice(["/", "", " // "])
        inputs.append(f"{ip}{sep}{prefix}")

    return inputs


def generate_contains_inputs() -> list[str | None]:
    """Generate IP inputs for membership testing."""
    inputs: list[str | None] = [
        None, "", "   ", "\t\n",
        "192.168.1.1", "192.168.1.100", "10.0.0.5", "255.255.255.255",
        "0.0.0.0", "8.8.8.8", "127.0.0.1",
        "::1", "2001:db8::1", "fe80::1", "ff00::1",
    ]
    garbage = ["notanip", "192.168.1.256", "256.168.1.1", "192.168.1", "",
               "::1/64", "192.168.1.1/24", "\x00", "exämple.com"]
    inputs.extend(garbage)
    controls = ["\x00", "\x09", "\x0a", "\x1f", "\x7f"]
    for c in controls:
        inputs.append(f"192.168.1.1{c}")
    rng = random.Random(20261126 + 1)
    for _ in range(1000):
        if rng.random() < 0.5:
            ip = ".".join(str(rng.randint(0, 300)) for _ in range(4))
        else:
            ip = ":".join(
                "".join(rng.choice("0123456789abcdefghijklmnopqrstuvwxyz")
                        for _ in range(rng.randint(1, 4))) for _ in range(8)
            )
        inputs.append(ip)
    return inputs


def generate_diff_inputs() -> list[str | None]:
    """Generate CIDR inputs for set-difference testing."""
    inputs: list[str | None] = [
        None, "", "   ",
        "10.0.0.0/8", "10.0.0.0/16", "10.1.0.0/16", "10.0.1.0/24",
        "192.168.1.0/24", "192.168.1.0/25", "192.168.1.128/25",
        "::/0", "::1/128", "2001:db8::/32", "2001:db8::1/128",
        "10.0.0.0/33", "notacidr", "256.168.1.1/24", "::1/129",
    ]
    rng = random.Random(20261126 + 2)
    for _ in range(800):
        if rng.random() < 0.5:
            ip = ".".join(str(rng.randint(0, 300)) for _ in range(4))
            prefix = str(rng.randint(-5, 40))
        else:
            parts = [
                "".join(rng.choice("0123456789abcdef") for _ in range(rng.randint(1, 4)))
                for _ in range(8)
            ]
            ip = ":".join(parts)
            prefix = str(rng.randint(-5, 130))
        inputs.append(f"{ip}/{prefix}")
    return inputs


def generate_run_cidr_cases() -> list[Case]:
    """Generate full run_cidr (cidr, contains, diff) cases."""
    cidrs = generate_cidr_inputs()
    contains_list = generate_contains_inputs()
    diffs = generate_diff_inputs()
    rng = random.Random(20261126 + 3)
    cases: list[Case] = []
    # Deterministic cross product of a curated subset.
    curated_cidrs = [
        "192.168.1.0/24", "10.0.0.0/8", "::/0", "::1/128",
        "192.168.1.1", "2001:db8::/32", "", "notacidr",
        "10.0.0.0/31", "10.0.0.0/32", "192.168.1.0/25",
    ]
    curated_contains: list[str | None] = [
        None, "192.168.1.1", "10.0.0.5", "::1", "2001:db8::1",
        "192.168.2.1", "notanip", "", "\x00",
    ]
    curated_diffs: list[str | None] = [
        None, "10.0.0.0/8", "10.0.0.0/16", "192.168.1.0/25",
        "192.168.1.0/24", "::/0", "2001:db8::/33", "notacidr", "",
    ]
    for c in curated_cidrs:
        for co in curated_contains:
            for d in curated_diffs:
                cases.append(Case(c, co, d))
    # Randomized cases for broader coverage.
    for _ in range(1500):
        c = rng.choice(cidrs)
        co = rng.choice(contains_list)
        d = rng.choice(diffs)
        cases.append(Case(c, co, d))
    return cases


# ──────────────────────────────────────────────────────────────────────────────
# Verification functions
# ──────────────────────────────────────────────────────────────────────────────

def verify_normalize_cidr() -> list[tuple[str, str, str]]:
    """Verify normalize_cidr against oracle."""
    mismatches: list[tuple[str, str, str]] = []
    for value in generate_cidr_inputs():
        try:
            our_result = normalize_cidr(value)
            our_str = str(our_result)
        except CidrSpecError:
            our_str = _ORACLE_ERROR
        except (ValueError, TypeError) as e:
            mismatches.append((repr(value), f"EXCEPTION: {type(e).__name__}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_normalize_cidr(value)
        oracle_str = _ORACLE_ERROR if oracle_result is None else str(oracle_result)

        if our_str != oracle_str:
            mismatches.append((repr(value), our_str, oracle_str))
    return mismatches


def verify_contains_ip() -> list[tuple[str, str, str]]:
    """Verify _contains_ip against oracle."""
    mismatches: list[tuple[str, str, str]] = []
    for cidr in generate_cidr_inputs():
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        for ip in generate_contains_inputs():
            ip_str = repr(ip) if ip is not None else "None"
            try:
                our_result = _contains_ip(network, ip if ip is not None else "")
                our_str = str(our_result)
            except (ValueError, TypeError) as e:
                mismatches.append((f"{cidr!r} contains={ip_str}", f"EXCEPTION: {type(e).__name__}", "ORACLE_N/A"))
                continue

            oracle_str = str(oracle_contains_ip(network, ip if ip is not None else ""))
            if our_str != oracle_str:
                mismatches.append((f"{cidr!r} contains={ip_str}", our_str, oracle_str))
    return mismatches


def verify_subtract_networks() -> list[tuple[str, str, str]]:
    """Verify _subtract_networks against oracle."""
    mismatches: list[tuple[str, str, str]] = []
    for minuend_raw in generate_cidr_inputs():
        minuend_nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        if minuend_raw:
            try:
                minuend_nets = [ipaddress.ip_network(minuend_raw, strict=False)]
            except ValueError:
                continue
        for subtrahend_raw in generate_cidr_inputs():
            subtrahend_nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
            if subtrahend_raw:
                try:
                    subtrahend_nets = [ipaddress.ip_network(subtrahend_raw, strict=False)]
                except ValueError:
                    continue
            desc = f"{minuend_raw!r}-{subtrahend_raw!r}"
            try:
                our_nets = _subtract_networks(minuend_nets, subtrahend_nets)
                our_str = sorted(str(n) for n in our_nets)
            except (ValueError, TypeError, AttributeError) as e:
                mismatches.append((desc, f"EXCEPTION: {type(e).__name__}", "ORACLE_N/A"))
                continue

            oracle_str = oracle_subtract_networks(
                [minuend_raw] if minuend_raw else [],
                [subtrahend_raw] if subtrahend_raw else [],
            )
            oracle_list: list[str] = [] if oracle_str is None else oracle_str
            if our_str != oracle_list:
                mismatches.append((desc, str(our_str), str(oracle_list)))
    return mismatches


def verify_run_cidr() -> list[tuple[str, str, str]]:
    """Verify run_cidr against oracle."""
    mismatches: list[tuple[str, str, str]] = []
    for case in generate_run_cidr_cases():
        desc = f"run_cidr({case.cidr!r}, {case.contains!r}, {case.diff!r})"
        try:
            our_result = run_cidr(case.cidr, case.contains, case.diff)
            our_str = str(_canonicalize_result(cast(dict[str, object], our_result)))
        except CidrSpecError:
            our_str = _ORACLE_ERROR
        except (ValueError, TypeError) as e:
            mismatches.append((desc, f"EXCEPTION: {type(e).__name__}", "ORACLE_N/A"))
            continue

        oracle_result = oracle_run_cidr(case.cidr, case.contains, case.diff)
        oracle_str = _ORACLE_ERROR if oracle_result is None else str(_canonicalize_result(oracle_result))

        if our_str != oracle_str:
            mismatches.append((desc, our_str, oracle_str))
    return mismatches


def _canonicalize_result(result: dict[str, object]) -> dict[str, object]:
    """Sort the difference list for order-independent comparison."""
    out: dict[str, object] = dict(result)
    diff = out.get("diff")
    if isinstance(diff, dict):
        difference = diff.get("difference")
        if isinstance(difference, list):
            diff = dict(diff)
            diff["difference"] = sorted(difference)
            out["diff"] = diff
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    """Run all verifications. Returns 0 on success, 1 on mismatch."""
    all_mismatches: list[tuple[str, str, str, str]] = []

    checks = [
        ("normalize_cidr", verify_normalize_cidr()),
        ("_contains_ip", verify_contains_ip()),
        ("_subtract_networks", verify_subtract_networks()),
        ("run_cidr", verify_run_cidr()),
    ]

    for func_name, mismatches in checks:
        if mismatches:
            all_mismatches.extend([(func_name,) + m for m in mismatches])
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
