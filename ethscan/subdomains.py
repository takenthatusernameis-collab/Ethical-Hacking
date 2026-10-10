"""Subdomain enumeration module for ethscan."""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse

try:
    import dns.resolver
    import dns.exception
    DNS_AVAILABLE = True
except ImportError:
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


def load_subdomain_wordlist(path: str) -> List[str]:
    """Load a subdomain wordlist from file, one subdomain per line.

    Args:
        path: Path to wordlist file.

    Returns:
        List of subdomain names (lines stripped, empty lines skipped).
    """
    with open(path, "r", encoding="utf-8") as handle:
        return [
            line.strip()
            for line in handle
            if line.strip() and not line.startswith("#")
        ]


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
    parsed = urlparse(normalized)
    return parsed.netloc.lower()


def resolve_subdomain(
    subdomain: str, domain: str, timeout: float = 2.0, resolver: Optional[str] = None
) -> Tuple[str, Optional[str]]:
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
            return subdomain, str(answers[0])
        except (dns.exception.DNSException, OSError, ValueError):
            return subdomain, None
    try:
        socket.setdefaulttimeout(timeout)
        ip = socket.gethostbyname(hostname)
        return subdomain, ip
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        return subdomain, None


def run_subdomains(
    target: str,
    subdomains: Optional[List[str]] = None,
    timeout: float = 2.0,
    max_workers: int = 50,
    resolver: Optional[str] = None,
    recursive: bool = False,
    max_depth: int = DEFAULT_RECURSIVE_DEPTH,
) -> Dict[str, object]:
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

    all_results: List[Dict[str, object]] = []
    seen_hostnames: Set[str] = set()
    per_depth_results: List[Dict[str, object]] = []

    def _enumerate_depth(
        current_labels: List[str], base_domain: str, depth: int
    ) -> List[Dict[str, object]]:
        """Enumerate subdomains at a specific depth."""
        depth_results: List[Dict[str, object]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_label = {
                executor.submit(
                    resolve_subdomain, label, base_domain, timeout, resolver
                ): label
                for label in current_labels
            }
            for future in as_completed(future_to_label):
                subdomain, ip = future.result()
                hostname = f"{subdomain}.{base_domain}"
                depth_results.append(
                    {"subdomain": subdomain, "hostname": hostname, "ip": ip, "depth": depth}
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
            "resolved_count": sum(1 for r in depth_0_results if r["ip"] is not None),
            "results": depth_0_results,
        }
    )

    # Recursive enumeration for subsequent depths
    if recursive:
        for depth in range(1, max_depth + 1):
            # Find resolved subdomains from previous depth to use as base for next depth
            previous_depth_results = per_depth_results[depth - 1]["results"]
            base_domains = [
                r["hostname"]
                for r in previous_depth_results
                if r["ip"] is not None
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
            depth_results: List[Dict[str, object]] = []

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
                    "resolved_count": sum(1 for r in depth_results if r["ip"] is not None),
                    "results": depth_results,
                }
            )

    # Build resolved list (all results with IP, across all depths)
    resolved = [r for r in all_results if r["ip"] is not None]

    # Build all_results without depth field for backward compatibility
    all_results_no_depth = [
        {"subdomain": r["subdomain"], "hostname": r["hostname"], "ip": r["ip"]}
        for r in sorted(all_results, key=lambda r: r["hostname"])
    ]

    return {
        "target": target,
        "domain": domain,
        "subdomains_tested": sum(d["subdomains_tested"] for d in per_depth_results),
        "resolved_count": len(resolved),
        "resolved": resolved,
        "all_results": all_results_no_depth,
        "per_depth": per_depth_results,
        "resolver": resolver,
        "dnspython_available": DNS_AVAILABLE,
        "recursive": recursive,
        "max_depth": max_depth,
    }


def format_subdomains_report_json(data: Dict[str, object]) -> str:
    """Format subdomain results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_subdomains_report_markdown(data: Dict[str, object]) -> str:
    """Format subdomain results as Markdown."""
    lines = ["# ethscan Subdomain Enumeration Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    resolver = data.get("resolver")
    if resolver:
        lines.append(f"- **Resolver:** {resolver} (dnspython: {'Yes' if data.get('dnspython_available') else 'No'})")
    recursive = data.get("recursive", False)
    max_depth = data.get("max_depth", 0)
    lines.append(f"- **Recursive:** {'Yes' if recursive else 'No'}")
    if recursive:
        lines.append(f"- **Max Depth:** {max_depth}")
    lines.append(f"- **Subdomains Tested:** {data['subdomains_tested']}")
    lines.append(f"- **Resolved:** {data['resolved_count']}")
    lines.append("")

    lines.append("## Resolved Subdomains")
    lines.append("| Subdomain | Hostname | IP |")
    lines.append("|-----------|----------|----|")
    for entry in data["resolved"]:
        lines.append(f"| {entry['subdomain']} | {entry['hostname']} | {entry['ip']} |")
    lines.append("")

    lines.append("## All Results")
    lines.append("| Subdomain | Hostname | IP |")
    lines.append("|-----------|----------|----|")
    for entry in data["all_results"]:
        ip = entry["ip"] if entry["ip"] is not None else "N/A"
        lines.append(f"| {entry['subdomain']} | {entry['hostname']} | {ip} |")
    lines.append("")

    if recursive:
        lines.append("## Recursive Enumeration (Per Depth)")
        for depth_data in data.get("per_depth", []):
            depth = depth_data.get("depth", 0)
            if depth == 0:
                continue
            lines.append(f"### Depth {depth}")
            lines.append(f"- **Base Domains:** {depth_data.get('subdomains_tested', 0)} subdomains tested")
            lines.append(f"- **Resolved:** {depth_data.get('resolved_count', 0)}")
            results = depth_data.get("results", [])
            if results:
                lines.append("| Subdomain | Hostname | IP |")
                lines.append("|-----------|----------|----|")
                for entry in results:
                    lines.append(f"| {entry['subdomain']} | {entry['hostname']} | {entry['ip']} |")
            else:
                lines.append("*No subdomains resolved at this depth.*")
            lines.append("")

    return "\n".join(lines)