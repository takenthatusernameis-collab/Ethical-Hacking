"""DNS record enumeration module for ethscan."""
from __future__ import annotations

import csv
import io
import socket
from concurrent.futures import ThreadPoolExecutor

from ethscan.target import parse_url

try:
    import dns.exception
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


DEFAULT_DNS_TYPES = ["A", "AAAA"]
DEFAULT_TIMEOUT = 2.0


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
    netloc = parsed.netloc.lower()
    # parse_url preserves IPv6 brackets in netloc (e.g. "[::1]" or "[::1]:8080").
    # Strip them so IPv6 literals are consistently represented bare and are
    # correctly recognized as IP addresses by _is_ip_address(). Bare IPv6 inputs
    # without brackets (e.g. "2001:db8::1") are passed through unchanged.
    if netloc.startswith("[") and "]" in netloc:
        netloc = netloc[1 : netloc.index("]")]
    return netloc


def resolve_a_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve A records (IPv4 addresses) for a domain using stdlib.

    Args:
        domain: Domain name to resolve.
        timeout: Resolution timeout in seconds.

    Returns:
        List of IPv4 addresses.
    """
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        return []


def resolve_aaaa_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve AAAA records (IPv6 addresses) for a domain using stdlib.

    Args:
        domain: Domain name to resolve.
        timeout: Resolution timeout in seconds.

    Returns:
        List of IPv6 addresses.
    """
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET6)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        return []


def resolve_with_dnspython(
    domain: str, record_type: str, timeout: float = DEFAULT_TIMEOUT
) -> list[str]:
    """Resolve DNS records using dnspython if available.

    Args:
        domain: Domain name to resolve.
        record_type: DNS record type (e.g., MX, NS, TXT, CNAME, SOA).
        timeout: Resolution timeout in seconds.

    Returns:
        List of record values as strings.
    """
    if not DNS_AVAILABLE:
        return []

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout

        answers = resolver.resolve(domain, record_type)
        return sorted({str(rdata) for rdata in answers})
    except (dns.exception.DNSException, OSError, ValueError):
        return []


def run_dns(
    target: str,
    record_types: list[str] | None = None,
    server: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    workers: int = 1,
) -> dict[str, object]:
    """Enumerate DNS records for a target domain.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        record_types: List of DNS record types to query (A, AAAA, MX, NS, TXT, CNAME, SOA).
                      If None, uses DEFAULT_DNS_TYPES (A, AAAA).
        server: Custom DNS resolver IP address (only used with dnspython).
        timeout: Resolution timeout in seconds.
        workers: Number of concurrent workers (default: 1).

    Returns:
        Structured results with target, domain, and records per type.
    """
    domain = _normalize_domain(target)
    types = record_types if record_types is not None else DEFAULT_DNS_TYPES

    all_supported = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"}

    # Filter to only supported types, preserving input order
    valid_types = [rtype.upper() for rtype in types if rtype.upper() in all_supported]

    def resolve_type(rtype: str) -> tuple:
        """Resolve a single record type, returning (rtype, results_list)."""
        if rtype == "A":
            return rtype, resolve_a_records(domain, timeout)
        elif rtype == "AAAA":
            return rtype, resolve_aaaa_records(domain, timeout)
        if server:
            if DNS_AVAILABLE:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.timeout = timeout
                    resolver.lifetime = timeout
                    resolver.nameservers = [server]
                    answers = resolver.resolve(domain, rtype)
                    return rtype, sorted({str(rdata) for rdata in answers})
                except (dns.exception.DNSException, OSError, ValueError):
                    return rtype, []
            return rtype, []
        return rtype, resolve_with_dnspython(domain, rtype, timeout)

    results: dict[str, list[str]] = {}

    if workers <= 1:
        for rtype in valid_types:
            rtype_key, values = resolve_type(rtype)
            results[rtype_key] = values
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs and keep futures in the same order as valid_types
            futures = [executor.submit(resolve_type, rtype) for rtype in valid_types]
            # Collect results in the order of valid_types to preserve insertion order
            for i, rtype in enumerate(valid_types):
                rtype_key, values = futures[i].result()
                results[rtype_key] = values

    return {
        "target": target,
        "domain": domain,
        "record_types_queried": types,
        "records": results,
        "dnspython_available": DNS_AVAILABLE,
    }


def format_dns_report_json(data: dict[str, object]) -> str:
    """Format DNS results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_dns_report_markdown(data: dict[str, object]) -> str:
    """Format DNS results as Markdown."""
    records = data["records"]
    lines = ["# ethscan DNS Record Enumeration Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    lines.append(f"- **Record Types Queried:** {', '.join(data['record_types_queried'])}")
    lines.append(f"- **dnspython Available:** {'Yes' if data['dnspython_available'] else 'No (stdlib only)'}")
    lines.append("")

    for rtype, values in records.items():
        lines.append(f"## {rtype} Records")
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("*No records found*")
        lines.append("")

    return "\n".join(lines)


def format_dns_report_csv(data: dict[str, object]) -> str:
    """Format DNS results as CSV.

    Emits a header row (``target,domain,record_type,record_value``) followed
    by one row per resolved record value, using stdlib ``csv.writer`` for
    proper quoting/escaping of values containing commas or double-quotes.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "domain", "record_type", "record_value"])

    records = data.get("records", {}) or {}
    for rtype, values in records.items():
        record_type = str(rtype)
        for value in values or []:
            writer.writerow([data.get("target", ""), data.get("domain", ""), record_type, str(value)])

    return output.getvalue().rstrip("\r\n")