"""Stale DNS record detection module for ethscan."""
from __future__ import annotations

import csv
import io
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from ethscan.fileio import read_lines
from ethscan.target import parse_url

DEFAULT_TIMEOUT = 2.0
DEFAULT_MAX_WORKERS = 50


def _normalize_domain(target: str) -> str:
    """Extract a bare domain from a target that may be a URL or host.

    Args:
        target: Bare domain (e.g. example.com) or URL (e.g. https://example.com/path).

    Returns:
        Lowercased domain without scheme or path.
    """
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = parse_url(normalized)
    return parsed.netloc.lower()


def load_domains_from_file(path: str) -> list[str]:
    """Load domains from file, one domain per line.

    Args:
        path: Path to file.

    Returns:
        List of domain names (lines stripped, empty lines and comments skipped).
    """
    return read_lines(path)


def resolve_a_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve A records (IPv4 addresses) for a domain using stdlib."""
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError, RuntimeError):
        return []


def resolve_aaaa_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve AAAA records (IPv6 addresses) for a domain using stdlib."""
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET6)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError, RuntimeError):
        return []


def resolve_cname(domain: str, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """Resolve CNAME record for a domain using stdlib getaddrinfo (follows CNAME)."""
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_UNSPEC, 0, 0, socket.AI_CANONNAME)
        if results:
            canonname = results[0][3]
            if canonname and canonname != domain:
                return canonname.rstrip(".")
    except (socket.timeout, socket.gaierror, OSError, ValueError, RuntimeError):
        pass
    return None


def check_tcp_connect(ip: str, port: int = 80, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Check if an IP is reachable via TCP connect."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        return True
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError, RuntimeError):
        return False


def check_ip_reachable(ip: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Check if an IP is reachable on common ports (80, 443, 22)."""
    return any(check_tcp_connect(ip, port, timeout) for port in (80, 443, 22))


def resolve_domain_all(domain: str, timeout: float) -> dict[str, object]:
    """Resolve all record types for a domain and check reachability."""
    result: dict[str, object] = {
        "domain": domain,
        "A": [],
        "AAAA": [],
        "CNAME": None,
        "stale": False,
        "stale_reasons": [],
    }

    a_records = resolve_a_records(domain, timeout)
    result["A"] = a_records

    aaaa_records = resolve_aaaa_records(domain, timeout)
    result["AAAA"] = aaaa_records

    cname = resolve_cname(domain, timeout)
    result["CNAME"] = cname

    if not a_records and not aaaa_records and not cname:
        result["stale"] = True
        result["stale_reasons"].append("No DNS records resolved (NXDOMAIN or SERVFAIL)")

    for ip in a_records + aaaa_records:
        if not check_ip_reachable(ip, timeout):
            result["stale"] = True
            result["stale_reasons"].append(f"IP {ip} unreachable on common ports")

    if cname:
        cname_resolved = resolve_a_records(cname, timeout) or resolve_aaaa_records(cname, timeout)
        if not cname_resolved:
            result["stale"] = True
            result["stale_reasons"].append(f"CNAME target {cname} does not resolve")

    return result


def run_stale(
    targets: list[str],
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, object]:
    """Detect stale DNS records for a list of domains.

    Args:
        targets: List of domain names or URLs to check.
        timeout: DNS resolution and TCP connect timeout in seconds.
        max_workers: Maximum number of concurrent workers.

    Returns:
        Structured results with per-domain resolution and stale status.
    """
    normalized_targets = [_normalize_domain(t) for t in targets]
    unique_targets = sorted(set(normalized_targets))

    results: list[dict[str, object]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(resolve_domain_all, domain, timeout): domain
            for domain in unique_targets
        }
        for future in as_completed(future_to_domain):
            results.append(future.result())

    stale_results = [r for r in results if r["stale"]]
    fresh_results = [r for r in results if not r["stale"]]

    return {
        "targets": targets,
        "total_checked": len(results),
        "stale_count": len(stale_results),
        "fresh_count": len(fresh_results),
        "results": results,
        "stale_results": stale_results,
    }


def format_stale_report_json(data: dict[str, object]) -> str:
    """Format stale detection results as JSON."""
    import json
    return json.dumps(data, indent=2, default=str)


def format_stale_report_markdown(data: dict[str, object]) -> str:
    """Format stale detection results as Markdown."""
    lines = ["# ethscan Stale DNS Record Detection Report", ""]
    lines.append(f"- **Total Checked:** {data['total_checked']}")
    lines.append(f"- **Stale Records:** {data['stale_count']}")
    lines.append(f"- **Fresh Records:** {data['fresh_count']}")
    lines.append("")

    if data["stale_results"]:
        lines.append("## Stale Records")
        lines.append("| Domain | A Records | AAAA Records | CNAME | Stale Reasons |")
        lines.append("|--------|-----------|--------------|-------|---------------|")
        for entry in data["stale_results"]:
            a_str = ", ".join(entry["A"]) if entry["A"] else "None"
            aaaa_str = ", ".join(entry["AAAA"]) if entry["AAAA"] else "None"
            cname_str = entry["CNAME"] or "None"
            reasons_str = "; ".join(entry["stale_reasons"])
            lines.append(f"| {entry['domain']} | {a_str} | {aaaa_str} | {cname_str} | {reasons_str} |")
        lines.append("")

    if data.get("results"):
        lines.append("## All Results")
        lines.append("| Domain | A Records | AAAA Records | CNAME | Stale |")
        lines.append("|--------|-----------|--------------|-------|-------|")
        for entry in data["results"]:
            a_str = ", ".join(entry["A"]) if entry["A"] else "None"
            aaaa_str = ", ".join(entry["AAAA"]) if entry["AAAA"] else "None"
            cname_str = entry["CNAME"] or "None"
            stale_str = "Yes" if entry["stale"] else "No"
            lines.append(f"| {entry['domain']} | {a_str} | {aaaa_str} | {cname_str} | {stale_str} |")
        lines.append("")

    return "\n".join(lines)


def format_stale_report_csv(data: dict[str, object]) -> str:
    """Format stale detection results as CSV.

    Emits a header row followed by one row per domain with columns:
    domain, A_records, AAAA_records, CNAME, stale, stale_reasons.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["domain", "A_records", "AAAA_records", "CNAME", "stale", "stale_reasons"])

    results = data.get("results", []) or []
    for entry in results:
        a_str = ", ".join(entry.get("A", []) or [])
        aaaa_str = ", ".join(entry.get("AAAA", []) or [])
        cname_str = entry.get("CNAME") or ""
        stale_str = "true" if entry.get("stale") else "false"
        reasons_str = "; ".join(entry.get("stale_reasons", []) or [])
        writer.writerow([entry.get("domain", ""), a_str, aaaa_str, cname_str, stale_str, reasons_str])

    return output.getvalue().rstrip("\r\n")