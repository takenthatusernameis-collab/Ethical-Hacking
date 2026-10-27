"""CIDR network calculation module for ethscan.

Provides offline network calculations using the stdlib ``ipaddress`` module:
network address, netmask, broadcast, wildcard, host range, usable host count,
IP version, and membership testing for a ``--contains`` IP.

Fully stdlib-only and offline.
"""
from __future__ import annotations

import csv
import io
import ipaddress


class CidrSpecError(ValueError):
    """Raised when a CIDR specification cannot be parsed.

    Subclasses :class:`ValueError` so that existing ``except ValueError``
    handlers keep working, while letting the CLI layer distinguish an invalid
    CIDR specification from unrelated value errors and turn it into a usage
    error.
    """


def normalize_cidr(value: str) -> str:
    """Normalize a CIDR string, ensuring a network address.

    Args:
        value: CIDR notation (e.g. ``192.168.1.0/24``) or bare IP (treated as /32 or /128).

    Returns:
        Canonical CIDR string with network address and prefix length.

    Raises:
        CidrSpecError: If the value is empty or is not a valid IPv4/IPv6 network.
    """
    value = value.strip()
    if not value:
        raise CidrSpecError("Empty CIDR value")

    if "/" not in value:
        # Bare IP: treat as a single-host network
        value = value + ("/32" if "." in value else "/128")

    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise CidrSpecError(str(exc)) from exc
    return str(network)


# Backwards-compatible alias for the previous private name.
_normalize_cidr = normalize_cidr


def _is_ipv4(network: ipaddress._BaseNetwork) -> bool:
    """Return True if the network is IPv4."""
    return network.version == 4


def _format_network_info(network: ipaddress._BaseNetwork) -> dict[str, object]:
    """Build the structured network-info dictionary for a network object."""
    is_v4 = _is_ipv4(network)

    if is_v4:
        netmask = str(network.netmask)
        broadcast = str(network.broadcast_address) if network.broadcast_address else None
        wildcard = str(network.hostmask)
        usable_hosts = max(0, network.num_addresses - 2)
    else:
        netmask = str(network.netmask)
        broadcast = None
        wildcard = str(network.hostmask)
        usable_hosts = max(0, network.num_addresses - 1)

    if network.num_addresses > 2:
        first_host = str(network[1])
        last_host = str(network[-2] if is_v4 else network[-1])
    elif network.num_addresses == 2:
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
        "total_addresses": network.num_addresses,
        "prefixlen": network.prefixlen,
        "is_private": network.is_private,
    }


def _contains_ip(network: ipaddress._BaseNetwork, ip: str) -> bool:
    """Check whether an IP address belongs to the network."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr in network


def _subtract_networks(
    minuend: list[ipaddress._BaseNetwork],
    subtrahend: list[ipaddress._BaseNetwork],
) -> list[ipaddress._BaseNetwork]:
    """Subtract subtrahend networks from minuend networks.

    Returns a list of networks representing the address ranges in minuend
    but not in subtrahend. Uses ipaddress collapse and subtraction logic.
    """
    if not minuend:
        return []
    if not subtrahend:
        return sorted(minuend, key=lambda n: n.network_address)

    result: list[ipaddress._BaseNetwork] = []
    for m_net in sorted(minuend, key=lambda n: n.network_address):
        remaining = [m_net]
        for s_net in sorted(subtrahend, key=lambda n: n.network_address):
            if m_net.version != s_net.version:
                continue
            if not m_net.overlaps(s_net):
                continue
            new_remaining = []
            for r_net in remaining:
                if not r_net.overlaps(s_net):
                    new_remaining.append(r_net)
                    continue
                try:
                    diffs = list(r_net.address_exclude(s_net))
                except (ValueError, TypeError):
                    diffs = []
                if diffs:
                    new_remaining.extend(diffs)
            remaining = new_remaining
            if not remaining:
                break
        result.extend(remaining)
    return sorted(result, key=lambda n: n.network_address)


def run_cidr(
    cidr: str,
    contains: str | None = None,
    diff: str | None = None,
) -> dict[str, object]:
    """Compute network calculations for a CIDR.

    Args:
        cidr: CIDR notation (e.g. ``192.168.1.0/24``) or bare IP.
        contains: Optional IP address to test for membership.
        diff: Optional second CIDR to compute set difference against
            (addresses in ``cidr`` but not in ``diff``).

    Returns:
        Structured results with network info, optional membership test,
        and optional set difference.
    """
    normalized = _normalize_cidr(cidr)
    network = ipaddress.ip_network(normalized, strict=False)
    info = _format_network_info(network)

    result: dict[str, object] = {
        "cidr": normalized,
        "ip_version": "IPv4" if _is_ipv4(network) else "IPv6",
        "network": info,
    }

    if contains is not None:
        contains_stripped = contains.strip()
        result["contains"] = {
            "ip": contains_stripped,
            "in_network": _contains_ip(network, contains_stripped),
        }

    if diff is not None:
        diff_normalized = _normalize_cidr(diff)
        diff_network = ipaddress.ip_network(diff_normalized, strict=False)
        diff_result = _subtract_networks([network], [diff_network])
        total_diff_addresses = sum(n.num_addresses for n in diff_result)
        result["diff"] = {
            "diff_cidr": diff_normalized,
            "difference": [str(n) for n in diff_result],
            "difference_network_count": len(diff_result),
            "total_diff_addresses": total_diff_addresses,
        }

    return result


def format_cidr_report_json(data: dict[str, object]) -> str:
    """Format CIDR results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_cidr_report_markdown(data: dict[str, object]) -> str:
    """Format CIDR results as Markdown."""
    lines = ["# ethscan CIDR Network Calculator Report", ""]
    lines.append(f"- **CIDR:** {data['cidr']}")
    lines.append(f"- **IP Version:** {data['ip_version']}")
    lines.append("")

    network = data["network"]
    if not isinstance(network, dict):
        network = {}
    lines.append("## Network Information")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    for key, label in (
        ("network_address", "Network Address"),
        ("netmask", "Netmask"),
        ("broadcast_address", "Broadcast Address"),
        ("wildcard_mask", "Wildcard Mask"),
        ("first_host", "First Host"),
        ("last_host", "Last Host"),
        ("usable_host_count", "Usable Host Count"),
        ("total_addresses", "Total Addresses"),
        ("prefixlen", "Prefix Length"),
    ):
        value = network.get(key)
        value_str = "" if value is None else str(value)
        lines.append(f"| {label} | {_escape(value_str)} |")
    lines.append("")

    contains = data.get("contains")
    if isinstance(contains, dict):
        lines.append("## Membership Test")
        lines.append(f"- **IP Tested:** {contains.get('ip')}")
        lines.append(f"- **In Network:** {'Yes' if contains.get('in_network') else 'No'}")
        lines.append("")

    diff = data.get("diff")
    if isinstance(diff, dict):
        lines.append("## Set Difference (In First, Not In Second)")
        lines.append(f"- **Diff CIDR:** {diff.get('diff_cidr')}")
        lines.append(f"- **Difference Networks:** {diff.get('difference_network_count')}")
        lines.append(f"- **Total Difference Addresses:** {diff.get('total_diff_addresses')}")
        lines.append("")
        lines.append("### Difference Networks")
        lines.append("| Network | Address Range | Total Addresses |")
        lines.append("|---------|---------------|-----------------|")
        for net_str in diff.get("difference", []) or []:
            try:
                network = ipaddress.ip_network(net_str, strict=False)
                start = str(network.network_address)
                end = str(network.broadcast_address) if network.version == 4 else str(network[-1])
                total: object = network.num_addresses
            except ValueError:
                start = end = ""
                total = "?"
            lines.append(f"| {_escape(net_str)} | {_escape(start)} - {_escape(end)} | {total} |")
        lines.append("")

    return "\n".join(lines)
def format_cidr_report_csv(data: dict[str, object]) -> str:
    """Format CIDR calculation results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "cidr",
        "network_address",
        "broadcast_address",
        "netmask",
        "wildcard_mask",
        "prefix_length",
        "num_addresses",
        "first_address",
        "last_address",
        "is_private",
        "contains_ip",
        "contains_in_network",
        "diff_count",
        "diff_first",
        "diff_last",
    ])
    network = data.get("network")
    if not isinstance(network, dict):
        network = {}
    contains = data.get("contains")
    if not isinstance(contains, dict):
        contains = {}
    diff = data.get("diff")
    if not isinstance(diff, dict):
        diff = {}
    writer.writerow([
        data.get("cidr", ""),
        network.get("network_address", ""),
        network.get("broadcast_address", ""),
        network.get("netmask", ""),
        network.get("wildcard_mask", ""),
        network.get("prefixlen", ""),
        network.get("total_addresses", ""),
        network.get("first_host", ""),
        network.get("last_host", ""),
        "true" if network.get("is_private") else "false",
        contains.get("ip", "") if isinstance(contains, dict) else (contains or ""),
        "true" if (isinstance(contains, dict) and contains.get("in_network")) else "false",
        diff.get("difference_network_count", "") if diff else "",
        diff.get("difference", [""])[0] if diff and diff.get("difference") else "",
        diff.get("difference", [""])[-1] if diff and diff.get("difference") else "",
    ])
    return output.getvalue().rstrip("\r\n")
