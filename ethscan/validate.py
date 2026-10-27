"""Validation module for ethscan.

Validates and expands port specifications (comma-separated lists and ranges)
and CIDR network inputs offline, using the stdlib ``ipaddress`` module.

Port specifications are parsed inline rather than by reusing
``parse_port_range`` from :mod:`ethscan.scanner`: the ``validate`` command
reports each specification's error inside its own output instead of failing
the whole run, and it needs the per-token error messages that the inline
parser produces.

Fully stdlib-only and offline.
"""
from __future__ import annotations

import csv
import io
import ipaddress
import json
from typing import Any

MAX_PORT = 65535
MAX_EXPANDED_IPS = 256


def _validate_port_spec(spec: str) -> dict[str, Any]:
    """Validate and expand a single port specification string.

    Accepts comma-separated ports and ranges, e.g. ``"80,443,8000-9000"``.

    Returns a dict with keys ``spec``, ``valid``, ``ports``, ``count``, and
    ``error``.
    """
    spec = spec.strip()
    if not spec:
        return {
            "spec": spec,
            "valid": False,
            "ports": [],
            "count": 0,
            "error": "Empty port specification",
        }

    parts = [p.strip() for p in spec.split(",") if p.strip()]
    parsed_ports: list[int] = []
    for part in parts:
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start_str = start_str.strip()
            end_str = end_str.strip()
            if not start_str or not end_str:
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Invalid range '{part}': missing start or end",
                }
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Invalid port number in range '{part}'",
                }
            if start > end:
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Invalid range '{part}': start ({start}) > end ({end})",
                }
            if not (0 <= start <= MAX_PORT and 0 <= end <= MAX_PORT):
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Port out of range (0-{MAX_PORT}) in range '{part}'",
                }
            parsed_ports.extend(range(start, end + 1))
        else:
            try:
                port = int(part)
            except ValueError:
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Invalid port number '{part}'",
                }
            if not (0 <= port <= MAX_PORT):
                return {
                    "spec": spec,
                    "valid": False,
                    "ports": [],
                    "count": 0,
                    "error": f"Port {port} out of range (0-{MAX_PORT})",
                }
            parsed_ports.append(port)

    unique_ports = sorted(set(parsed_ports))
    return {
        "spec": spec,
        "valid": True,
        "ports": unique_ports,
        "count": len(unique_ports),
        "error": None,
    }


def _format_network_info(network: ipaddress._BaseNetwork) -> dict[str, Any]:
    """Build a structured network-info dictionary for a network object.

    Includes address range, netmask, broadcast, host range, and counts.
    For networks with at most ``MAX_EXPANDED_IPS`` total addresses, also
    includes the full list of individual IP addresses.
    """
    is_v4 = network.version == 4
    total = network.num_addresses

    info: dict[str, object] = {
        "network_address": str(network.network_address),
        "netmask": str(network.netmask),
        "broadcast_address": str(network.broadcast_address) if is_v4 else None,
        "wildcard_mask": str(network.hostmask),
        "first_host": str(network[1]) if total > 2 else str(network[0]),
        "last_host": (
            str(network[-1] if network.version == 6 else network[-2])
            if total > 2
            else str(network[0])
        ),
        "total_addresses": total,
        "prefixlen": network.prefixlen,
    }

    if total <= MAX_EXPANDED_IPS:
        info["addresses"] = [str(addr) for addr in network]
    else:
        info["addresses"] = None

    return info


def _validate_cidr(spec: str) -> dict[str, Any]:
    """Validate a single CIDR/network specification string.

    Accepts CIDR notation (``192.168.1.0/24``) or bare IPs (``192.168.1.1``,
    ``2001:db8::1``).

    Returns a dict with keys ``spec``, ``valid``, ``canonical``, ``network``,
    and ``error``.
    """
    spec = spec.strip()
    if not spec:
        return {
            "spec": spec,
            "valid": False,
            "canonical": None,
            "network": None,
            "error": "Empty CIDR specification",
        }

    try:
        if "/" not in spec:
            net_str = spec + ("/32" if "." in spec else "/128")
        else:
            net_str = spec
        network = ipaddress.ip_network(net_str, strict=False)
    except ValueError as exc:
        return {
            "spec": spec,
            "valid": False,
            "canonical": None,
            "network": None,
            "error": str(exc),
        }

    canonical = str(network)
    return {
        "spec": spec,
        "valid": True,
        "canonical": canonical,
        "network": _format_network_info(network),
        "error": None,
    }


def run_validate(
    ports: str | None = None,
    cidrs: str | None = None,
) -> dict[str, Any]:
    """Validate and expand port specifications and CIDR inputs.

    Args:
        ports: A port specification string with comma-separated ports and
            ranges (e.g. ``"80,443,8000-9000"``). The entire string is treated
            as a single specification.
        cidrs: Comma-separated CIDR/network specifications
            (e.g. ``"192.168.1.0/24,10.0.0.0/8"``).

    Returns:
        Structured results with per-spec validation, expanded values, a
        summary, and notes.
    """
    port_results: list[dict[str, object]] = []
    if ports:
        port_results.append(_validate_port_spec(ports))

    cidr_results: list[dict[str, object]] = []
    cidr_specs: list[str] = []
    if cidrs:
        cidr_specs = [s.strip() for s in cidrs.split(",") if s.strip()]
        for spec in cidr_specs:
            cidr_results.append(_validate_cidr(spec))

    total_valid = all(bool(r.get("valid", False)) for r in port_results + cidr_results) if (port_results or cidr_results) else False
    notes: list[str] = []
    if not port_results and not cidr_results:
        notes.append("No port or CIDR specifications provided; nothing to validate.")
    if port_results:
        notes.append(f"Validated {len(port_results)} port specification(s).")
    if cidr_results:
        notes.append(f"Validated {len(cidr_results)} CIDR specification(s).")
    if total_valid:
        notes.append("All specifications valid.")
    else:
        notes.append("One or more specifications were invalid; see error fields.")

    all_ports: set[int] = set()
    for r in port_results:
        ports_val = r.get("ports", [])
        if isinstance(ports_val, list):
            try:
                all_ports.update(int(p) for p in ports_val)
            except Exception:
                pass

    summary: dict[str, Any] = {
        "ports_specified": len(port_results),
        "ports_valid": sum(1 for r in port_results if r.get("valid")),
        "ports_total": len(sorted(all_ports)),
        "cidrs_specified": len(cidr_results),
        "cidrs_valid": sum(1 for r in cidr_results if r.get("valid")),
        "all_valid": total_valid,
    }

    return {
        "ports": port_results,
        "cidrs": cidr_results,
        "summary": summary,
        "notes": notes,
    }


def format_validate_report_json(data: dict[str, Any]) -> str:
    """Format validation results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def _ports_to_ranges(ports: list[int] | list[Any]) -> str:
    """Render a list of ports as compact range strings (e.g. ``80,443,8000-8002``)."""
    if not ports:
        return ""
    try:
        sorted_ports = sorted(int(p) for p in ports)
    except (TypeError, ValueError):
        return ""
    ranges: list[str] = []
    start = prev = sorted_ports[0]
    for port in sorted_ports[1:]:
        if port == prev + 1:
            prev = port
        else:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            start = prev = port
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{prev}")
    return ", ".join(ranges)




def format_validate_report_csv(data: dict[str, Any]) -> str:
    """Format validation results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "spec", "valid", "detail"])
    port_results = data.get("ports", []) or []
    if isinstance(port_results, list):
        for r in port_results:
            if not isinstance(r, dict):
                continue
            spec = str(r.get("spec", ""))
            valid_flag = bool(r.get("valid"))
            valid = "true" if valid_flag else "false"
            if valid_flag:
                ports_val = r.get("ports", [])
                if ports_val:
                    detail = _ports_to_ranges(ports_val)  # type: ignore
                else:
                    detail = str(r.get("count", 0))
            else:
                detail = str(r.get("error") or "")
            writer.writerow(["port", spec, valid, detail])
    cidr_results = data.get("cidrs", []) or []
    if isinstance(cidr_results, list):
        for r in cidr_results:
            if not isinstance(r, dict):
                continue
            spec = str(r.get("spec", ""))
            valid_flag = bool(r.get("valid"))
            valid = "true" if valid_flag else "false"
            if valid_flag:
                network = r.get("network") or {}
                if isinstance(network, dict):
                    canonical = network.get("canonical") or r.get("canonical") or spec
                else:
                    canonical = r.get("canonical") or spec
                detail = str(canonical)
            else:
                detail = str(r.get("error") or "")
            writer.writerow(["cidr", spec, valid, detail])
    return output.getvalue().rstrip("\r\n")

def format_validate_report_markdown(data: dict[str, Any]) -> str:
    """Format validation results as Markdown."""
    lines: list[str] = ["# ethscan Validate Report", ""]

    summary = data.get("summary", {}) or {}
    if isinstance(summary, dict):
        lines.append("## Summary")
        lines.append(f"- **Port Specs Provided:** {summary.get('ports_specified', 0)}")
        lines.append(f"- **Port Specs Valid:** {summary.get('ports_valid', 0)}")
        lines.append(f"- **Total Ports Expanded:** {summary.get('ports_total', 0)}")
        lines.append(f"- **CIDR Specs Provided:** {summary.get('cidrs_specified', 0)}")
        lines.append(f"- **CIDR Specs Valid:** {summary.get('cidrs_valid', 0)}")
        all_valid = summary.get("all_valid", False)
        lines.append(f"- **All Valid:** {'Yes' if all_valid else 'No'}")
        lines.append("")
    else:
        lines.append("## Summary")
        lines.append("")

    port_results = data.get("ports", []) or []
    if isinstance(port_results, list) and port_results:
        lines.append("## Port Specifications")
        lines.append("| Specification | Valid | Expanded Ports | Count | Error |")
        lines.append("|---------------|-------|-----------------|-------|-------|")
        for r in port_results:
            if not isinstance(r, dict):
                continue
            valid_flag = bool(r.get("valid"))
            ports_val = r.get("ports", [])
            if valid_flag and ports_val:
                expanded = _ports_to_ranges(ports_val)  # type: ignore
                if len(expanded) > 80:
                    expanded = expanded[:77] + "..."
            else:
                expanded = ""
            count = r.get("count", 0)
            error = _escape(str(r.get("error") or ""))
            valid_str = "Yes" if valid_flag else "No"
            lines.append(
                f"| {_escape(str(r.get('spec', '')))} | {valid_str} | {expanded} | {count} | {error} |"
            )
        lines.append("")
    else:
        lines.append("## Port Specifications")
        lines.append("*No port specifications provided.*")
        lines.append("")

    cidr_results = data.get("cidrs", []) or []
    if isinstance(cidr_results, list) and cidr_results:
        lines.append("## CIDR / Network Specifications")
        lines.append("| Specification | Valid | Canonical | Network | Broadcast | Range | Addresses | Error |")
        lines.append("|---------------|-------|-----------|---------|-----------|-------|-----------|-------|")
        for r in cidr_results:
            if not isinstance(r, dict):
                continue
            if r.get("valid"):
                net = r.get("network") or {}
                if isinstance(net, dict):
                    canonical = _escape(str(r.get("canonical") or net.get("canonical") or ""))
                    network_addr = _escape(str(net.get("network_address") or ""))
                    broadcast_addr = net.get("broadcast_address")
                    broadcast = _escape(str(broadcast_addr)) if broadcast_addr else "N/A"
                    range_str = (
                        f"{_escape(str(net.get('first_host', '')))} - "
                        f"{_escape(str(net.get('last_host', '')))}"
                    )
                    total = net.get("total_addresses", "?")
                else:
                    canonical = _escape(str(r.get("canonical") or ""))
                    network_addr = ""
                    broadcast = "N/A"
                    range_str = ""
                    total = ""
                error = ""
                valid_str = "Yes"
            else:
                canonical = ""
                network_addr = ""
                broadcast = ""
                range_str = ""
                total = ""
                error = _escape(str(r.get("error") or ""))
                valid_str = "No"
            lines.append(
                f"| {_escape(str(r.get('spec', '')))} | {valid_str} | {canonical} | "
                f"{network_addr} | {broadcast} | {range_str} | {total} | {error} |"
            )
        lines.append("")
    else:
        lines.append("## CIDR / Network Specifications")
        lines.append("*No CIDR specifications provided.*")
        lines.append("")

    notes = data.get("notes", []) or []
    if isinstance(notes, list) and notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {_escape(str(note))}")
        lines.append("")

    return "\n".join(lines)
