"""Subdomain enumeration module for ethscan."""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


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
    subdomain: str, domain: str, timeout: float = 2.0
) -> Tuple[str, Optional[str]]:
    """Resolve a single subdomain to an IP address.

    Args:
        subdomain: Subdomain label (e.g. www).
        domain: Base domain (e.g. example.com).
        timeout: DNS resolution timeout in seconds.

    Returns:
        Tuple of (subdomain, ip_or_None).
    """
    hostname = f"{subdomain}.{domain}"
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
) -> Dict[str, object]:
    """Enumerate subdomains for a target domain.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        subdomains: List of subdomain labels to test. If None, uses DEFAULT_SUBDOMAINS.
        timeout: DNS resolution timeout in seconds.
        max_workers: Maximum number of concurrent resolution workers.

    Returns:
        Structured results with target, domain, resolved subdomains, and all results.
    """
    domain = _normalize_domain(target)
    labels = subdomains if subdomains is not None else DEFAULT_SUBDOMAINS

    results: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_label = {
            executor.submit(resolve_subdomain, label, domain, timeout): label
            for label in labels
        }
        for future in as_completed(future_to_label):
            subdomain, ip = future.result()
            results.append({"subdomain": subdomain, "hostname": f"{subdomain}.{domain}", "ip": ip})

    resolved = [r for r in results if r["ip"] is not None]

    return {
        "target": target,
        "domain": domain,
        "subdomains_tested": len(labels),
        "resolved_count": len(resolved),
        "resolved": resolved,
        "all_results": sorted(results, key=lambda r: r["subdomain"]),
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

    return "\n".join(lines)