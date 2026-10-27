"""Radix tree visualization module for ethscan.

Builds a binary radix tree (Patricia trie) over a set of CIDR networks,
merging overlapping and adjacent (supernettable) networks into compact
aggregate ranges. Fully offline; depends only on the stdlib ``ipaddress``
module and the shared CIDR helpers in :mod:`ethscan.cidr`.
"""
from __future__ import annotations

import csv
import io
import ipaddress
from typing import cast

from ethscan.cidr import normalize_cidr

# Backwards-compatible alias for the previous private name.
_normalize_cidr = normalize_cidr


class RadixSpecError(ValueError):
    """Raised when a radix tree specification mixes IP address families.

    Subclasses :class:`ValueError` so that existing ``except ValueError``
    handlers keep working, while letting the CLI layer distinguish an invalid
    radix specification from unrelated value errors and turn it into a usage
    error.
    """


def _is_ipv4(network: ipaddress._BaseNetwork) -> bool:
    """Return True if the network is IPv4."""
    return network.version == 4


def parse_cidrs(values: list[str]) -> list[ipaddress._BaseNetwork]:
    """Parse and normalize a list of CIDR strings into network objects.

    A radix tree is built over a single address family, so a list that mixes
    IPv4 and IPv6 networks is rejected instead of failing later on.

    Raises:
        CidrSpecError: If a value is not a valid CIDR/network specification.
        RadixSpecError: If the values mix IPv4 and IPv6 networks.
    """
    networks: list[ipaddress._BaseNetwork] = []
    for raw in values:
        normalized = normalize_cidr(raw)
        networks.append(ipaddress.ip_network(normalized, strict=False))
    if len({net.version for net in networks}) > 1:
        raise RadixSpecError(
            "Cannot mix IPv4 and IPv6 networks in a single radix tree"
        )
    return networks


# Backwards-compatible alias for the previous private name.
_parse_networks = parse_cidrs


def _nth_bit(addr, bit_index: int, is_v4: bool) -> int:
    """Return the value (0/1) of the bit at the given index (MSB = 0)."""
    max_bits = 32 if is_v4 else 128
    if bit_index >= max_bits:
        return 0
    return (int(addr) >> (max_bits - 1 - bit_index)) & 1


def _common_prefix_length(networks: list[ipaddress._BaseNetwork]) -> int:
    """Return the longest common prefix length shared by all networks."""
    if not networks:
        return 0
    if len(networks) == 1:
        return networks[0].prefixlen
    ref = networks[0]
    is_v4 = ref.version == 4
    max_bits = 32 if is_v4 else 128
    for bit in range(max_bits):
        ref_bit = _nth_bit(ref.network_address, bit, is_v4)
        for net in networks[1:]:
            if _nth_bit(net.network_address, bit, is_v4) != ref_bit:
                return bit
    return min(n.prefixlen for n in networks)


def _contains_ip(network: ipaddress._BaseNetwork, ip: str) -> bool:
    """Check whether an IP address belongs to the network."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr in network


def _contains_in_merged(merged: list[ipaddress._BaseNetwork], ip: str) -> tuple[bool, str | None]:
    """Check whether an IP address belongs to any of the merged networks.

    Returns a tuple of (in_network, matched_network_str_or_None).
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False, None
    for net in sorted(merged, key=lambda n: n.network_address):
        if addr in net:
            return True, str(net)
    return False, None


def _collapse_v4_networks(
    first: ipaddress.IPv4Network, second: ipaddress.IPv4Network
) -> list[ipaddress.IPv4Network]:
    """Collapse two IPv4 networks into a single supernet when possible."""
    return list(ipaddress.collapse_addresses([first, second]))


def _collapse_v6_networks(
    first: ipaddress.IPv6Network, second: ipaddress.IPv6Network
) -> list[ipaddress.IPv6Network]:
    """Collapse two IPv6 networks into a single supernet when possible."""
    return list(ipaddress.collapse_addresses([first, second]))


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
                except ValueError:
                    diffs = []
                if diffs:
                    new_remaining.extend(diffs)
            remaining = new_remaining
            if not remaining:
                break
        result.extend(remaining)
    return sorted(result, key=lambda n: n.network_address)


def _merge_networks(networks: list[ipaddress._BaseNetwork]) -> list[ipaddress._BaseNetwork]:
    """Merge overlapping and adjacent (supernettable) networks.

    Networks that overlap or can be combined into a single supernet are
    collapsed. The result is a minimal, non-overlapping set of aggregate
    networks sorted by address range.
    """
    if not networks:
        return []
    sorted_nets = sorted(networks, key=lambda n: (n.network_address, -n.prefixlen))
    merged: list[ipaddress._BaseNetwork] = []
    for net in sorted_nets:
        if not merged:
            merged.append(net)
            continue
        last = merged[-1]
        if net.version != last.version:
            merged.append(net)
            continue
        collapsed: list[ipaddress.IPv4Network] | list[ipaddress.IPv6Network] | None = None
        try:
            if isinstance(last, ipaddress.IPv4Network) and isinstance(
                net, ipaddress.IPv4Network
            ):
                collapsed = _collapse_v4_networks(
                    cast(ipaddress.IPv4Network, last),
                    cast(ipaddress.IPv4Network, net),
                )
            elif isinstance(last, ipaddress.IPv6Network) and isinstance(
                net, ipaddress.IPv6Network
            ):
                collapsed = _collapse_v6_networks(
                    cast(ipaddress.IPv6Network, last),
                    cast(ipaddress.IPv6Network, net),
                )
            else:
                collapsed = None
        except ValueError:
            collapsed = None
        if collapsed and len(collapsed) == 1:
            merged[-1] = collapsed[0]
        elif last.overlaps(net):
            if last.num_addresses >= net.num_addresses:
                merged[-1] = last
            else:
                merged[-1] = net
        else:
            merged.append(net)
    merged = sorted(merged, key=lambda n: n.network_address)
    return merged


def _common_prefix_of_pair(start, end, is_v4: bool) -> int:
    """Return the prefix length covering the range from start to end."""
    max_bits = 32 if is_v4 else 128
    span = int(end) - int(start) + 1
    # Find smallest prefix length that covers the span.
    needed_bits = 0
    while (1 << needed_bits) < span:
        needed_bits += 1
    return max(0, max_bits - needed_bits)


def _build_radix_node(
    networks: list[ipaddress._BaseNetwork],
    depth: int = 0,
    max_depth: int = 64,
) -> dict[str, object] | None:
    """Recursively build a radix tree node for a list of networks.

    Returns a dict with keys:
        prefix, start_address, end_address, total_addresses, networks,
        children, depth
    or None when the input list is empty.
    """
    if not networks or depth > max_depth:
        return None

    is_v4 = networks[0].version == 4
    max_bits = 32 if is_v4 else 128

    prefix_len = _common_prefix_length(networks)

    # Keep each network as-is; the common prefix is used only to compute the
    # node's aggregate range and to partition children by the next bit.
    deduped: list[ipaddress._BaseNetwork] = []
    seen = set()
    for net in networks:
        key = (str(net.network_address), net.prefixlen)
        if key not in seen:
            seen.add(key)
            deduped.append(net)

    start = min(n.network_address for n in deduped)
    end = max(n.broadcast_address for n in deduped)
    total = int(end) - int(start) + 1

    # Compute the proper supernet prefix for the aggregate range by finding
    # the common prefix between start and end.
    range_prefix = _common_prefix_of_pair(start, end, is_v4)
    try:
        supernet = ipaddress.ip_network(f"{start}/{range_prefix}", strict=False)
        prefix_str = str(supernet)
    except ValueError:
        prefix_str = f"{start}/{range_prefix}"

    node: dict[str, object] = {
        "prefix": prefix_str,
        "start_address": str(start),
        "end_address": str(end),
        "total_addresses": total,
        "networks": [str(n) for n in sorted(deduped, key=lambda n: n.network_address)],
        "children": [],
        "depth": depth,
    }

    # Recurse into children when there are multiple distinct networks and we
    # have not reached the host prefix. Partition by the next bit after the
    # common prefix.
    if len(deduped) > 1 and prefix_len < max_bits:
        left_nets: list[ipaddress._BaseNetwork] = []
        right_nets: list[ipaddress._BaseNetwork] = []
        for net in networks:
            bit = _nth_bit(net.network_address, prefix_len, is_v4)
            if bit == 0:
                left_nets.append(net)
            else:
                right_nets.append(net)
        left_node = _build_radix_node(left_nets, depth + 1, max_depth)
        right_node = _build_radix_node(right_nets, depth + 1, max_depth)
        children = node.get("children", [])
        if not isinstance(children, list):
            children = []
        if left_node is not None:
            children.append({"side": "left (0)", "node": left_node})
        if right_node is not None:
            children.append({"side": "right (1)", "node": right_node})
        node["children"] = children

    return node


def _format_network_info(network: ipaddress._BaseNetwork) -> dict[str, object]:
    """Build structured network info dict for a single network."""
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
    }


def run_radix(
    cidrs: list[str],
    merge: bool = True,
    max_depth: int = 64,
    contains: str | None = None,
    diff: list[str] | None = None,
) -> dict[str, object]:
    """Build a radix tree visualization over a set of CIDR networks.

    Args:
        cidrs: List of CIDR strings (e.g. ``["192.168.1.0/24", "10.0.0.0/8"]``).
        merge: When True, merge overlapping and supernettable networks first.
        max_depth: Maximum recursion depth for the radix tree (default 64).
        contains: Optional IP address to test for membership in the merged networks.
        diff: Optional second list of CIDR strings to compute set difference
            (addresses in cidrs but not in diff).

    Returns:
        Structured results with parsed networks, merged networks, radix tree
        node, summary counts, optional membership test, and optional diff.
    """
    parsed = parse_cidrs(cidrs)

    if merge:
        merged = _merge_networks(parsed)
    else:
        merged = sorted(parsed, key=lambda n: n.network_address)

    root = _build_radix_node(merged, depth=0, max_depth=max_depth)

    total_input_addresses = sum(n.num_addresses for n in parsed)
    total_merged_addresses = sum(n.num_addresses for n in merged)
    compression_ratio = (
        round(total_input_addresses / total_merged_addresses, 4)
        if total_merged_addresses > 0
        else 0.0
    )

    result: dict[str, object] = {
        "cidrs": cidrs,
        "network_count": len(parsed),
        "merged_network_count": len(merged),
        "merged": [str(n) for n in merged],
        "total_input_addresses": total_input_addresses,
        "total_merged_addresses": total_merged_addresses,
        "compression_ratio": compression_ratio,
        "merge_enabled": merge,
        "max_depth": max_depth,
        "radix_tree": root,
    }

    if contains is not None:
        contains_stripped = contains.strip()
        in_network, matched = _contains_in_merged(merged, contains_stripped)
        result["contains"] = {
            "ip": contains_stripped,
            "in_network": in_network,
            "matched_network": matched,
        }

    if diff is not None:
        diff_parsed = parse_cidrs(diff)
        if merge:
            diff_merged = _merge_networks(diff_parsed)
        else:
            diff_merged = sorted(diff_parsed, key=lambda n: n.network_address)
        diff_result = _subtract_networks(merged, diff_merged)
        total_diff_addresses = sum(n.num_addresses for n in diff_result)
        result["diff"] = {
            "diff_cidrs": diff,
            "diff_network_count": len(diff_parsed),
            "diff_merged_network_count": len(diff_merged),
            "diff_merged": [str(n) for n in diff_merged],
            "difference": [str(n) for n in diff_result],
            "difference_network_count": len(diff_result),
            "total_diff_addresses": total_diff_addresses,
        }

    return result


def format_radix_report_json(data: dict[str, object]) -> str:
    """Format radix results as JSON."""
    import json
    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def _render_node_md(node: dict[str, object], lines: list[str], depth: int = 0) -> None:
    """Recursively render a radix node as Markdown lines."""
    indent = "  " * depth
    prefix = node.get("prefix", "")
    start = node.get("start_address", "")
    end = node.get("end_address", "")
    total = node.get("total_addresses", 0)
    networks = node.get("networks", [])
    if not isinstance(networks, list):
        networks = []
    lines.append(f"{indent}- **{prefix}** | {start} - {end} | {total} addresses | {len(networks)} net(s)")
    children = node.get("children", [])
    if not isinstance(children, list):
        children = []
    for child in children:
        side = child.get("side", "")
        child_node = child.get("node")
        if child_node is not None:
            lines.append(f"{indent}  - {side}:")
            _render_node_md(child_node, lines, depth + 2)


def format_radix_report_markdown(data: dict[str, object]) -> str:
    """Format radix results as Markdown."""
    lines = ["# ethscan Radix Tree Report", ""]
    lines.append(f"- **Networks Provided:** {data['network_count']}")
    lines.append(f"- **Merged Networks:** {data['merged_network_count']}")
    lines.append(f"- **Total Input Addresses:** {data['total_input_addresses']}")
    lines.append(f"- **Total Merged Addresses:** {data['total_merged_addresses']}")
    lines.append(f"- **Compression Ratio:** {data['compression_ratio']}")
    lines.append(f"- **Merge Enabled:** {data['merge_enabled']}")
    lines.append("")

    lines.append("## Merged Networks")
    lines.append("| Network | Address Range | Total Addresses |")
    lines.append("|---------|---------------|-----------------|")
    merged = data.get("merged", [])
    if not isinstance(merged, list):
        merged = []
    for net_str in merged:
        try:
            network = ipaddress.ip_network(net_str, strict=False)
            start = str(network.network_address)
            end = str(network.broadcast_address) if network.version == 4 else str(network[-1])
            total = str(network.num_addresses)
        except ValueError:
            start = end = ""
            total = "?"
        lines.append(f"| {_escape(net_str)} | {_escape(start)} - {_escape(end)} | {total} |")
    lines.append("")

    root = data.get("radix_tree")
    if not isinstance(root, dict):
        root = None
    if root is not None:
        lines.append("## Radix Tree")
        lines.append("")
        _render_node_md(root, lines)
        lines.append("")

    contains = data.get("contains")
    if not isinstance(contains, dict):
        contains = None
    if contains is not None:
        lines.append("## Membership Test")
        lines.append(f"- **IP Tested:** {contains['ip']}")
        lines.append(f"- **In Network:** {'Yes' if contains['in_network'] else 'No'}")
        if contains.get("matched_network"):
            lines.append(f"- **Matched Network:** {contains['matched_network']}")
        lines.append("")

    diff = data.get("diff")
    if not isinstance(diff, dict):
        diff = None
    if diff is not None:
        lines.append("## Set Difference (In First, Not In Second)")
        lines.append(f"- **Diff CIDRs Provided:** {diff['diff_network_count']}")
        lines.append(f"- **Diff Merged Networks:** {diff['diff_merged_network_count']}")
        lines.append(f"- **Difference Networks:** {diff['difference_network_count']}")
        lines.append(f"- **Total Difference Addresses:** {diff['total_diff_addresses']}")
        lines.append("")
        lines.append("### Difference Networks")
        lines.append("| Network | Address Range | Total Addresses |")
        lines.append("|---------|---------------|-----------------|")
        difference = diff.get("difference", [])
        if not isinstance(difference, list):
            difference = []
        for net_str in difference:
            try:
                network = ipaddress.ip_network(net_str, strict=False)
                start = str(network.network_address)
                end = str(network.broadcast_address) if network.version == 4 else str(network[-1])
                total = str(network.num_addresses)
            except ValueError:
                start = end = ""
                total = "?"
            lines.append(f"| {_escape(net_str)} | {_escape(start)} - {_escape(end)} | {total} |")
        lines.append("")

    return "\n".join(lines)

def format_radix_report_csv(data: dict[str, object]) -> str:
    """Format radix tree results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    has_diff = "diff" in data
    if has_diff:
        writer.writerow([
            "original_cidr",
            "merged_cidr",
            "compression_ratio",
            "diff_cidr",
        ])
    else:
        writer.writerow([
            "original_cidr",
            "merged_cidr",
            "compression_ratio",
        ])

    cidrs = data.get("cidrs", [])
    if not isinstance(cidrs, list):
        cidrs = []
    merged = data.get("merged", [])
    if not isinstance(merged, list):
        merged = []
    compression_ratio = data.get("compression_ratio", 0.0)

    # Build a mapping from original CIDR to merged CIDR
    # For simplicity, if networks didn't merge, each maps to itself
    # If they did merge, we need to find which merged network contains the original
    import ipaddress
    merged_networks = [ipaddress.ip_network(m) for m in merged]

    # For diff, just use the first diff CIDR if available
    diff_cidr = ""
    if has_diff:
        diff = data.get("diff", {})
        if not isinstance(diff, dict):
            diff = {}
        diff_cidrs = diff.get("diff_cidrs", [])
        if diff_cidrs:
            diff_cidr = diff_cidrs[0]

    for original in cidrs:
        orig_net = ipaddress.ip_network(original, strict=False)
        matched_merged = original
        for m_net in merged_networks:
            if (
                isinstance(orig_net, ipaddress.IPv4Network)
                and isinstance(m_net, ipaddress.IPv4Network)
                and orig_net.subnet_of(m_net)
            ) or (
                isinstance(orig_net, ipaddress.IPv6Network)
                and isinstance(m_net, ipaddress.IPv6Network)
                and orig_net.subnet_of(m_net)
            ):
                matched_merged = str(m_net)
                break

        if has_diff:
            writer.writerow([
                original,
                matched_merged,
                compression_ratio,
                diff_cidr,
            ])
        else:
            writer.writerow([
                original,
                matched_merged,
                compression_ratio,
            ])

    return output.getvalue().rstrip("\r\n")
