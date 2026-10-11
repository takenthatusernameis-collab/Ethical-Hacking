"""CIDR network calculation module for ethscan.

Provides offline network calculations using the stdlib ``ipaddress`` module:
network address, netmask, broadcast, wildcard, host range, usable host count,
IP version, and membership testing for a ``--contains`` IP.

Fully stdlib-only and offline.
"""

import ipaddress
from typing import Dict, List, Optional, Tuple, Union


def _normalize_cidr(value: str) -> str:
    """Normalize a CIDR string, ensuring a network address.

    Args:
        value: CIDR notation (e.g. ``192.168.1.0/24``) or bare IP (treated as /32 or /128).

    Returns:
        Canonical CIDR string with network address and prefix length.
    """
    value = value.strip()
    if not value:
        raise ValueError("Empty CIDR value")

    if "/" not in value:
        # Bare IP: treat as a single-host network
        value = value + ("/32" if "." in value else "/128")

    network = ipaddress.ip_network(value, strict=False)
    return str(network)


def _is_ipv4(network: ipaddress._BaseNetwork) -> bool:
    """Return True if the network is IPv4."""
    return network.version == 4


def _format_network_info(network: ipaddress._BaseNetwork) -> Dict[str, object]:
    """Build the structured network-info dictionary for a network object."""
    is_v4 = _is_ipv4(network)

    if is_v4:
        netmask = str(network.netmask)
        broadcast = str(network.broadcast_address) if network.broadcast_address else None
        wildcard = str(network.hostmask)
        first_host = str(network[1]) if network.num_addresses > 1 else (
            str(network.network_address) if network.num_addresses == 1 else None
        )
        last_host = str(network[-1]) if network.num_addresses > 1 else (
            str(network.network_address) if network.num_addresses == 1 else None
        )
        usable_hosts = max(0, network.num_addresses - 2)
    else:
        netmask = str(network.netmask)
        broadcast = None
        wildcard = str(network.hostmask)
        first_host = str(network[1]) if network.num_addresses > 1 else (
            str(network.network_address) if network.num_addresses == 1 else None
        )
        last_host = str(network[-1]) if network.num_addresses > 1 else (
            str(network.network_address) if network.num_addresses == 1 else None
        )
        usable_hosts = max(0, network.num_addresses - 2)

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
    }


def _contains_ip(network: ipaddress._BaseNetwork, ip: str) -> bool:
    """Check whether an IP address belongs to the network."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr in network


def run_cidr(
    cidr: str,
    contains: Optional[str] = None,
) -> Dict[str, object]:
    """Compute network calculations for a CIDR.

    Args:
        cidr: CIDR notation (e.g. ``192.168.1.0/24``) or bare IP.
        contains: Optional IP address to test for membership.

    Returns:
        Structured results with network info and optional membership test.
    """
    normalized = _normalize_cidr(cidr)
    network = ipaddress.ip_network(normalized, strict=False)
    info = _format_network_info(network)

    result: Dict[str, object] = {
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

    return result


def format_cidr_report_json(data: Dict[str, object]) -> str:
    """Format CIDR results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def format_cidr_report_markdown(data: Dict[str, object]) -> str:
    """Format CIDR results as Markdown."""
    lines = ["# ethscan CIDR Network Calculator Report", ""]
    lines.append(f"- **CIDR:** {data['cidr']}")
    lines.append(f"- **IP Version:** {data['ip_version']}")
    lines.append("")

    network = data["network"]
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
    if contains is not None:
        lines.append("## Membership Test")
        lines.append(f"- **IP Tested:** {contains['ip']}")
        lines.append(f"- **In Network:** {'Yes' if contains['in_network'] else 'No'}")
        lines.append("")

    return "\n".join(lines)