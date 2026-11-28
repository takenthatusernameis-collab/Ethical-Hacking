#!/usr/bin/env python3
"""Independent oracle verification for ethscan.validate pure helpers."""

from __future__ import annotations

import ipaddress
import random
import sys
from typing import Any

from ethscan.validate import (
    _validate_cidr,
    _validate_port_spec,
    run_validate,
)

MAX_PORT = 65535
MAX_EXPANDED_IPS = 256


def oracle_validate_port_spec(spec: str) -> dict[str, Any]:
    spec = spec.strip()
    if not spec:
        return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": "Empty port specification"}
    parts = [p.strip() for p in spec.split(",")]
    if not any(parts):
        return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": "No ports in specification"}
    if any(not part for part in parts):
        return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Empty port token in specification: {spec!r}"}
    parsed: list[int] = []
    for part in parts:
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = a.strip(), b.strip()
            if not a or not b:
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Invalid range '{part}': missing start or end"}
            try:
                s, e = int(a), int(b)
            except ValueError:
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Invalid port number in range '{part}'"}
            if s > e:
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Invalid range '{part}': start ({s}) > end ({e})"}
            if not (0 <= s <= MAX_PORT and 0 <= e <= MAX_PORT):
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Port out of range (0-{MAX_PORT}) in range '{part}'"}
            parsed.extend(range(s, e + 1))
        else:
            try:
                p = int(part)
            except ValueError:
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Invalid port number '{part}'"}
            if not (0 <= p <= MAX_PORT):
                return {"spec": spec, "valid": False, "ports": [], "count": 0, "error": f"Port {p} out of range (0-{MAX_PORT})"}
            parsed.append(p)
    uniq = sorted(set(parsed))
    return {"spec": spec, "valid": True, "ports": uniq, "count": len(uniq), "error": None}


def oracle_validate_cidr(spec: str) -> dict[str, Any]:
    spec = spec.strip()
    if not spec:
        return {"spec": spec, "valid": False, "canonical": None, "network": None, "error": "Empty CIDR specification"}
    if "/" not in spec:
        try:
            addr = ipaddress.ip_address(spec)
            net_str = spec + ("/32" if addr.version == 4 else "/128")
        except ValueError:
            net_str = spec
    else:
        net_str = spec
    try:
        network = ipaddress.ip_network(net_str, strict=False)
    except ValueError as exc:
        return {"spec": spec, "valid": False, "canonical": None, "network": None, "error": str(exc)}
    is_v4 = network.version == 4
    total = network.num_addresses
    if total <= 2:
        usable = total
    elif is_v4:
        usable = total - 2
    else:
        usable = total - 1
    info: dict[str, Any] = {
        "network_address": str(network.network_address),
        "netmask": str(network.netmask),
        "broadcast_address": str(network.broadcast_address) if is_v4 else None,
        "wildcard_mask": str(network.hostmask),
        "first_host": (str(network[1]) if total > 2 else str(network[0]) if total == 2 else str(network.network_address)),
        "last_host": (str(network[-2] if is_v4 else network[-1]) if total > 2 else str(network[1]) if total == 2 else str(network.network_address)),
        "usable_host_count": usable,
        "total_addresses": total,
        "prefixlen": network.prefixlen,
        "is_private": network.is_private,
    }
    if total <= MAX_EXPANDED_IPS:
        info["addresses"] = [str(a) for a in network]
    else:
        info["addresses"] = None
    return {"spec": spec, "valid": True, "canonical": str(network), "network": info, "error": None}


def _cmp(a: Any, b: Any) -> bool:
    return a == b


def verify_validate_port_spec() -> list[tuple[str, str, str]]:
    cases = ["", "   ", "80", "80,443", "8000-9000", "80,443,8000-8002", "abc", "80-", "-80", "99999", "80,,443", "70000-100", "0", "65535", "1-2-3"]
    # add random
    for _ in range(200):
        n = random.randint(1, 4)
        toks = []
        for _ in range(n):
            if random.random() < 0.5:
                toks.append(str(random.randint(0, 70000)))
            else:
                a = random.randint(0, 70000)
                b = random.randint(0, 70000)
                toks.append(f"{a}-{b}")
        cases.append(",".join(toks))
        cases.append(random.choice(["", " ", "\t", "80", "abc", "1-2"]))
    mismatches = []
    for c in cases:
        ours = _validate_port_spec(c)
        oracle = oracle_validate_port_spec(c)
        if ours != oracle:
            mismatches.append((repr(c), repr(ours), repr(oracle)))
    return mismatches


def verify_validate_cidr() -> list[tuple[str, str, str]]:
    cases = ["", "   ", "192.168.1.0/24", "10.0.0.1", "2001:db8::/32", "::1", "999.999.999.999", "192.168.1.0/99", "foo", "192.168.1.0/24,10.0.0.0/8"]
    for v in ["192.168.1.0", "10.0.0.0", "::ffff:192.168.1.1", "2001:db8::1"]:
        cases.append(v)
    for _ in range(300):
        # random ipv4
        ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
        cases.append(ip)
        cases.append(ip + "/" + str(random.randint(0, 33)))
        # random ipv6
        cases.append("::1")
    mismatches = []
    for c in cases:
        ours = _validate_cidr(c)
        oracle = oracle_validate_cidr(c)
        if ours != oracle:
            mismatches.append((repr(c), repr(ours), repr(oracle)))
    return mismatches


def verify_run_validate() -> list[tuple[str, str, str]]:
    # smoke: compare run_validate for a few inputs
    cases = [
        (None, None, None),
        ("80,443", None, None),
        (None, "192.168.1.0/24", None),
        (None, None, "fast"),
        ("80", "10.0.0.0/24", None),
    ]
    mismatches = []
    for ports, cidrs, profile in cases:
        ours = run_validate(ports=ports, cidrs=cidrs, profile=profile)
        # oracle: rebuild using helpers
        port_results = []
        profile_result = None
        if profile:
            pk = profile.lower()
            if pk == "fast":
                from ethscan.scanner import FAST_PORTS
                port_results.append({"spec": "fast", "valid": True, "ports": list(FAST_PORTS), "count": len(FAST_PORTS), "error": None})
            elif pk == "normal":
                from ethscan.scanner import COMMON_PORTS
                port_results.append({"spec": "normal", "valid": True, "ports": list(COMMON_PORTS), "count": len(COMMON_PORTS), "error": None})
            elif pk == "full":
                from ethscan.scanner import FULL_PORTS
                port_results.append({"spec": "full", "valid": True, "ports": list(FULL_PORTS), "count": len(FULL_PORTS), "error": None})
            else:
                port_results.append({"spec": profile, "valid": False, "ports": [], "count": 0, "error": f"Unknown profile: {profile}. Valid profiles: fast, normal, full"})
        if ports:
            port_results.append(oracle_validate_port_spec(ports))
        elif profile_result is not None:
            port_results.append(profile_result)
        cidr_results = []
        if cidrs:
            for s in [x.strip() for x in cidrs.split(",") if x.strip()]:
                cidr_results.append(oracle_validate_cidr(s))
        # compare ports/cidrs only (summary/notes derived)
        if ours.get("ports") != port_results or ours.get("cidrs") != cidr_results:
            mismatches.append(((ports, cidrs, profile), repr(ours.get("ports")), repr(port_results)))
    return mismatches  # type: ignore[return-value]


def main() -> int:
    allm = []
    allm += [("port_spec",) + m for m in verify_validate_port_spec()]
    allm += [("cidr",) + m for m in verify_validate_cidr()]
    allm += [("run_validate",) + m for m in verify_run_validate()]
    if allm:
        for m in allm[:20]:
            print(m)
        print(f"TOTAL MISMATCHES: {len(allm)}")
        return 1
    print("ALL VERIFICATIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
