"""Stale DNS record detection module for ethscan."""
from __future__ import annotations

import contextlib
import csv
import io
import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

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
        previous = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            results = socket.getaddrinfo(domain, None, socket.AF_INET)
            ips = [str(r[4][0]) for r in results]
            return sorted(set(ips))
        finally:
            socket.setdefaulttimeout(previous)
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return []


def resolve_aaaa_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve AAAA records (IPv6 addresses) for a domain using stdlib."""
    try:
        previous = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            results = socket.getaddrinfo(domain, None, socket.AF_INET6)
            ips = [str(r[4][0]) for r in results]
            return sorted(set(ips))
        finally:
            socket.setdefaulttimeout(previous)
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return []


def resolve_cname(domain: str, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """Resolve CNAME record for a domain using stdlib getaddrinfo (follows CNAME)."""
    try:
        previous = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            results = socket.getaddrinfo(domain, None, socket.AF_UNSPEC, 0, 0, socket.AI_CANONNAME)
            if results:
                canonname = results[0][3]
                if canonname and canonname != domain:
                    return canonname.rstrip(".")
        finally:
            socket.setdefaulttimeout(previous)
    except Exception:  # noqa: BLE001, S110 - resolver can raise any type
        pass
    return None


def check_tcp_connect(ip: str, port: int = 80, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Check if an IP is reachable via TCP connect."""
    sock = None
    try:
        addr_family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        sock = socket.socket(addr_family, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        if addr_family == socket.AF_INET6:
            sock.connect((ip, port, 0, 0))
        else:
            sock.connect((ip, port))
        return True
    except Exception:  # noqa: BLE001 - transport can raise any type
        return False
    finally:
        if sock is not None:
            with contextlib.suppress(Exception):
                sock.close()


def check_ip_reachable(ip: str, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """Check if an IP is reachable on common ports (80, 443, 22)."""
    return any(check_tcp_connect(ip, port, timeout) for port in (80, 443, 22))


def resolve_domain_all(domain: str, timeout: float) -> dict[str, Any]:
    """Resolve all record types for a domain and check reachability."""
    result: dict[str, Any] = {
        "domain": domain,
        "A": [],
        "AAAA": [],
        "CNAME": None,
        "stale": False,
        "stale_reasons": [],
    }

    try:
        a_records = resolve_a_records(domain, timeout)
        result["A"] = a_records
    except Exception:  # noqa: BLE001 - resolver can raise any type
        a_records = []
        result["A"] = []
        result["stale"] = True
        result["stale_reasons"].append("DNS resolution failed")

    try:
        aaaa_records = resolve_aaaa_records(domain, timeout)
        result["AAAA"] = aaaa_records
    except Exception:  # noqa: BLE001 - resolver can raise any type
        aaaa_records = []
        result["AAAA"] = []

    try:
        cname = resolve_cname(domain, timeout)
        result["CNAME"] = cname
    except Exception:  # noqa: BLE001 - resolver can raise any type
        cname = None
        result["CNAME"] = None

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
) -> dict[str, Any]:
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

    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {
            executor.submit(resolve_domain_all, domain, timeout): domain
            for domain in unique_targets
        }
        for future in as_completed(future_to_domain):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - resolver can raise any type
                domain = future_to_domain.get(future, "")
                results.append(
                    {
                        "domain": domain,
                        "A": [],
                        "AAAA": [],
                        "CNAME": None,
                        "stale": True,
                        "stale_reasons": [str(exc)],
                    }
                )

    stale_results = [r for r in results if r.get("stale")]
    fresh_results = [r for r in results if not r.get("stale")]

    return {
        "targets": targets,
        "total_checked": len(results),
        "stale_count": len(stale_results),
        "fresh_count": len(fresh_results),
        "results": results,
        "stale_results": stale_results,
    }


def format_stale_report_json(data: dict[str, Any]) -> str:
    """Format stale detection results as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_stale_report_markdown(data: dict[str, Any]) -> str:
    """Format stale detection results as Markdown."""
    lines = ["# ethscan Stale DNS Record Detection Report", ""]
    lines.append(f"- **Total Checked:** {data.get('total_checked', 0)}")
    lines.append(f"- **Stale Records:** {data.get('stale_count', 0)}")
    lines.append(f"- **Fresh Records:** {data.get('fresh_count', 0)}")
    lines.append("")

    stale_results = data.get("stale_results") or []
    if isinstance(stale_results, list) and stale_results:
        lines.append("## Stale Records")
        lines.append("| Domain | A Records | AAAA Records | CNAME | Stale Reasons |")
        lines.append("|--------|-----------|--------------|-------|---------------|")
        for entry in stale_results:
            if not isinstance(entry, dict):
                continue
            a_list = entry.get("A") or []
            aaaa_list = entry.get("AAAA") or []
            a_str = ", ".join(str(x) for x in a_list) if a_list else "None"
            aaaa_str = ", ".join(str(x) for x in aaaa_list) if aaaa_list else "None"
            cname_str = entry.get("CNAME") or "None"
            reasons = entry.get("stale_reasons") or []
            reasons_str = "; ".join(str(x) for x in reasons)
            lines.append(f"| {entry.get('domain', '')} | {a_str} | {aaaa_str} | {cname_str} | {reasons_str} |")
        lines.append("")

    results = data.get("results") or []
    if isinstance(results, list) and results:
        lines.append("## All Results")
        lines.append("| Domain | A Records | AAAA Records | CNAME | Stale |")
        lines.append("|--------|-----------|--------------|-------|-------|")
        for entry in results:
            if not isinstance(entry, dict):
                continue
            a_list = entry.get("A") or []
            aaaa_list = entry.get("AAAA") or []
            a_str = ", ".join(str(x) for x in a_list) if a_list else "None"
            aaaa_str = ", ".join(str(x) for x in aaaa_list) if aaaa_list else "None"
            cname_str = entry.get("CNAME") or "None"
            stale_str = "Yes" if entry.get("stale") else "No"
            lines.append(f"| {entry.get('domain', '')} | {a_str} | {aaaa_str} | {cname_str} | {stale_str} |")
        lines.append("")

    return "\n".join(lines)


def format_stale_report_csv(data: dict[str, Any]) -> str:
    """Format stale detection results as CSV.

    Emits a header row followed by one row per domain with columns:
    domain, A_records, AAAA_records, CNAME, stale, stale_reasons.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["domain", "A_records", "AAAA_records", "CNAME", "stale", "stale_reasons"])

    results = data.get("results", []) or []
    if isinstance(results, list):
        for entry in results:
            if not isinstance(entry, dict):
                continue
            a_list = entry.get("A") or []
            aaaa_list = entry.get("AAAA") or []
            a_str = ", ".join(str(x) for x in a_list)
            aaaa_str = ", ".join(str(x) for x in aaaa_list)
            cname_str = entry.get("CNAME") or ""
            stale_str = "true" if entry.get("stale") else "false"
            reasons = entry.get("stale_reasons") or []
            reasons_str = "; ".join(str(x) for x in reasons)
            writer.writerow([entry.get("domain", ""), a_str, aaaa_str, cname_str, stale_str, reasons_str])

    return output.getvalue().rstrip("\r\n")