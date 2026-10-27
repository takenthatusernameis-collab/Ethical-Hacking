"""Subdomain enumeration module for ethscan."""
from __future__ import annotations

import csv
import io
import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ethscan.fileio import read_lines
from ethscan.target import parse_url

try:
    try:
        import dns.enum
        import dns.message
    except Exception:  # noqa: BLE001, S110
        pass
    import dns.exception
    import dns.resolver
    DNS_AVAILABLE = True
except Exception:  # noqa: BLE001
    DNS_AVAILABLE = False


DEFAULT_SUBDOMAINS = [
    "www",
    "mail",
    "api",
    "admin",
    "dev",
    "staging",
    "test",
    "blog",
    "shop",
    "cdn",
    "ftp",
    "smtp",
    "imap",
    "webmail",
    "vpn",
    "remote",
    "portal",
    "app",
    "m",
    "mobile",
    "secure",
    "support",
    "ns1",
    "ns2",
    "dns",
    "dns2",
]


DEFAULT_RECURSIVE_DEPTH = 2


def load_subdomain_wordlist(path: str) -> list[str]:
    """Load a subdomain wordlist from file, one subdomain per line.

    Args:
        path: Path to wordlist file.

    Returns:
        List of subdomain names (lines stripped, empty lines skipped).
    """
    return read_lines(path)


def _normalize_domain(target: str) -> str:
    """Extract a bare domain from a target that may be a URL or host.

    Args:
        target: Bare domain (e.g. example.com) or URL (e.g. https://example.com/path).

    Returns:
        Lowercased netloc/domain without scheme or path.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = parse_url(normalized)
    return parsed.netloc.lower()


def resolve_subdomain(
    subdomain: str, domain: str, timeout: float = 2.0, resolver: str | None = None
) -> tuple[str, str | None]:
    """Resolve a single subdomain to an IP address.

    Args:
        subdomain: Subdomain label (e.g. www).
        domain: Base domain (e.g. example.com).
        timeout: DNS resolution timeout in seconds.
        resolver: Custom DNS resolver IP address (requires dnspython).

    Returns:
        Tuple of (subdomain, ip_or_None).
    """
    hostname = f"{subdomain}.{domain}"
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "A")
            if not answers:
                return subdomain, None
            return subdomain, str(answers[0])
        except Exception:  # noqa: BLE001 - resolver can raise any type
            return subdomain, None
    try:
        previous = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            ip = socket.gethostbyname(hostname)
            return subdomain, ip
        finally:
            socket.setdefaulttimeout(previous)
    except Exception:  # noqa: BLE001 - resolver can raise any type
        # A label that holds a null byte (a wordlist that is not text) makes
        # ``gethostbyname`` raise a ``TypeError``: the label cannot be
        # resolved, it is not a crash.
        return subdomain, None


def run_subdomains(
    target: str,
    subdomains: list[str] | None = None,
    timeout: float = 2.0,
    max_workers: int = 50,
    resolver: str | None = None,
    recursive: bool = False,
    max_depth: int = DEFAULT_RECURSIVE_DEPTH,
) -> dict[str, Any]:
    """Enumerate subdomains for a target domain.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        subdomains: List of subdomain labels to test. If None, uses DEFAULT_SUBDOMAINS.
        timeout: DNS resolution timeout in seconds.
        max_workers: Maximum number of concurrent resolution workers.
        resolver: Custom DNS resolver IP address (requires dnspython).
        recursive: Enable recursive subdomain enumeration (discover subdomains of resolved subdomains).
        max_depth: Maximum recursion depth for recursive enumeration (default: 2).

    Returns:
        Structured results with target, domain, resolved subdomains, and all results.
    """
    domain = _normalize_domain(target)
    labels = subdomains if subdomains is not None else DEFAULT_SUBDOMAINS

    all_results: list[dict[str, Any]] = []
    seen_hostnames: set[str] = set()
    per_depth_results: list[dict[str, Any]] = []

    def _enumerate_depth(
        current_labels: list[str], base_domain: str, depth: int
    ) -> list[dict[str, Any]]:
        """Enumerate subdomains at a specific depth."""
        depth_results: list[dict[str, Any]] = []
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_label = {
                    executor.submit(
                        resolve_subdomain, label, base_domain, timeout, resolver
                    ): label
                    for label in current_labels
                }
                for future in as_completed(future_to_label):
                    try:
                        subdomain, ip = future.result()
                        hostname = f"{subdomain}.{base_domain}"
                        depth_results.append(
                            {"subdomain": subdomain, "hostname": hostname, "ip": ip, "depth": depth}
                        )
                    except Exception:  # noqa: BLE001 - resolver can raise any type
                        label = future_to_label.get(future)
                        if label is not None:
                            hostname = f"{label}.{base_domain}"
                            depth_results.append(
                                {"subdomain": label, "hostname": hostname, "ip": None, "depth": depth}
                            )
        except Exception:  # noqa: BLE001 - resolver can raise any type
            for label in current_labels:
                hostname = f"{label}.{base_domain}"
                depth_results.append(
                    {"subdomain": label, "hostname": hostname, "ip": None, "depth": depth}
                )
        return depth_results

    # Depth 0: enumerate against the base domain
    depth_0_results = _enumerate_depth(labels, domain, 0)
    all_results.extend(depth_0_results)
    for entry in depth_0_results:
        seen_hostnames.add(entry["hostname"])
    per_depth_results.append(
        {
            "depth": 0,
            "subdomains_tested": len(labels),
            "resolved_count": sum(1 for r in depth_0_results if r.get("ip") is not None),
            "results": depth_0_results,
        }
    )

    # Recursive enumeration for subsequent depths
    if recursive:
        for depth in range(1, max_depth + 1):
            # Find resolved subdomains from previous depth to use as base for next depth
            prev_depth = per_depth_results[depth - 1]
            prev_results = prev_depth.get("results") or []
            base_domains = [
                r["hostname"]
                for r in prev_results
                if isinstance(r, dict) and r.get("ip") is not None
            ]

            if not base_domains:
                # No resolved subdomains at previous depth, stop early
                per_depth_results.append(
                    {
                        "depth": depth,
                        "subdomains_tested": 0,
                        "resolved_count": 0,
                        "results": [],
                    }
                )
                continue

            # Use the same labels for each base domain
            depth_labels = labels
            depth_results: list[dict[str, Any]] = []

            for base_domain in base_domains:
                base_results = _enumerate_depth(depth_labels, base_domain, depth)
                for entry in base_results:
                    if entry["hostname"] not in seen_hostnames:
                        seen_hostnames.add(entry["hostname"])
                        depth_results.append(entry)

            all_results.extend(depth_results)
            per_depth_results.append(
                {
                    "depth": depth,
                    "subdomains_tested": len(base_domains) * len(depth_labels),
                    "resolved_count": sum(1 for r in depth_results if r.get("ip") is not None),
                    "results": depth_results,
                }
            )

    # Build resolved list (all results with IP, across all depths)
    resolved = [r for r in all_results if r.get("ip") is not None]

    # Build all_results without depth field for backward compatibility
    all_results_no_depth = [
        {"subdomain": r["subdomain"], "hostname": r["hostname"], "ip": r["ip"]}
        for r in sorted(all_results, key=lambda r: str(r.get("hostname")))
    ]

    return {
        "target": target,
        "domain": domain,
        "subdomains_tested": sum(int(d.get("subdomains_tested", 0)) for d in per_depth_results),
        "resolved_count": len(resolved),
        "resolved": resolved,
        "all_results": all_results_no_depth,
        "per_depth": per_depth_results,
        "resolver": resolver,
        "dnspython_available": DNS_AVAILABLE,
        "recursive": recursive,
        "max_depth": max_depth,
    }


def format_subdomains_report_json(data: dict[str, Any]) -> str:
    """Format subdomain results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_subdomains_report_markdown(data: dict[str, Any]) -> str:
    """Format subdomain results as Markdown."""
    lines = ["# ethscan Subdomain Enumeration Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Domain:** {data.get('domain', '')}")
    resolver = data.get("resolver")
    if resolver:
        lines.append(f"- **Resolver:** {resolver} (dnspython: {'Yes' if data.get('dnspython_available') else 'No'})")
    recursive = data.get("recursive", False)
    max_depth = data.get("max_depth", 0)
    lines.append(f"- **Recursive:** {'Yes' if recursive else 'No'}")
    if recursive:
        lines.append(f"- **Max Depth:** {max_depth}")
    lines.append(f"- **Subdomains Tested:** {data.get('subdomains_tested', 0)}")
    lines.append(f"- **Resolved:** {data.get('resolved_count', 0)}")
    lines.append("")

    lines.append("## Resolved Subdomains")
    lines.append("| Subdomain | Hostname | IP |")
    lines.append("|-----------|----------|----|")
    resolved_list = data.get("resolved") or []
    if isinstance(resolved_list, list):
        for entry in resolved_list:
            if not isinstance(entry, dict):
                continue
            lines.append(f"| {entry.get('subdomain', '')} | {entry.get('hostname', '')} | {entry.get('ip', '')} |")
    lines.append("")

    lines.append("## All Results")
    lines.append("| Subdomain | Hostname | IP |")
    lines.append("|-----------|----------|----|")
    all_results = data.get("all_results") or []
    if isinstance(all_results, list):
        for entry in all_results:
            if not isinstance(entry, dict):
                continue
            ip = entry.get("ip") if entry.get("ip") is not None else "N/A"
            lines.append(f"| {entry.get('subdomain', '')} | {entry.get('hostname', '')} | {ip} |")
    lines.append("")

    if recursive:
        lines.append("## Recursive Enumeration (Per Depth)")
        per_depth = data.get("per_depth") or []
        if isinstance(per_depth, list):
            for depth_data in per_depth:
                if not isinstance(depth_data, dict):
                    continue
                depth = depth_data.get("depth", 0)
                if depth == 0:
                    continue
                lines.append(f"### Depth {depth}")
                lines.append(f"- **Base Domains:** {depth_data.get('subdomains_tested', 0)} subdomains tested")
                lines.append(f"- **Resolved:** {depth_data.get('resolved_count', 0)}")
                results = depth_data.get("results") or []
                if isinstance(results, list) and results:
                    lines.append("| Subdomain | Hostname | IP |")
                    lines.append("|-----------|----------|----|")
                    for entry in results:
                        if not isinstance(entry, dict):
                            continue
                        lines.append(f"| {entry.get('subdomain', '')} | {entry.get('hostname', '')} | {entry.get('ip', '')} |")
                else:
                    lines.append("*No subdomains resolved at this depth.*")
                lines.append("")

    return "\n".join(lines)


def format_subdomains_report_csv(data: dict[str, Any]) -> str:
    """Format subdomain results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["subdomain", "hostname", "ip", "resolved"])
    all_results = data.get("all_results") or []
    if isinstance(all_results, list):
        for entry in all_results:
            if not isinstance(entry, dict):
                continue
            writer.writerow([
                entry.get("subdomain", ""),
                entry.get("hostname", ""),
                entry.get("ip") or "",
                "true" if entry.get("ip") else "false",
            ])
    return output.getvalue().rstrip("\r\n")