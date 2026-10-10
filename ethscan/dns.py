"""DNS record enumeration module for ethscan."""

import socket
from typing import Dict, List, Optional, Set

try:
    import dns.resolver
    import dns.exception
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
    from urllib.parse import urlparse
    parsed = urlparse(normalized)
    return parsed.netloc.lower()


def resolve_a_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> List[str]:
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


def resolve_aaaa_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> List[str]:
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
) -> List[str]:
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
        return sorted(set(str(rdata) for rdata in answers))
    except (dns.exception.DNSException, OSError, ValueError):
        return []


def run_dns(
    target: str,
    record_types: Optional[List[str]] = None,
    server: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, object]:
    """Enumerate DNS records for a target domain.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        record_types: List of DNS record types to query (A, AAAA, MX, NS, TXT, CNAME, SOA).
                      If None, uses DEFAULT_DNS_TYPES (A, AAAA).
        server: Custom DNS resolver IP address (only used with dnspython).
        timeout: Resolution timeout in seconds.

    Returns:
        Structured results with target, domain, and records per type.
    """
    domain = _normalize_domain(target)
    types = record_types if record_types is not None else DEFAULT_DNS_TYPES

    results: Dict[str, List[str]] = {}
    all_supported = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"}

    for rtype in types:
        rtype_upper = rtype.upper()
        if rtype_upper not in all_supported:
            continue

        if rtype_upper == "A":
            results["A"] = resolve_a_records(domain, timeout)
        elif rtype_upper == "AAAA":
            results["AAAA"] = resolve_aaaa_records(domain, timeout)
        elif DNS_AVAILABLE:
            if server:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.timeout = timeout
                    resolver.lifetime = timeout
                    resolver.nameservers = [server]
                    answers = resolver.resolve(domain, rtype_upper)
                    results[rtype_upper] = sorted(set(str(rdata) for rdata in answers))
                except (dns.exception.DNSException, OSError, ValueError):
                    results[rtype_upper] = []
            else:
                results[rtype_upper] = resolve_with_dnspython(domain, rtype_upper, timeout)
        else:
            results[rtype_upper] = []

    return {
        "target": target,
        "domain": domain,
        "record_types_queried": types,
        "records": results,
        "dnspython_available": DNS_AVAILABLE,
    }


def format_dns_report_json(data: Dict[str, object]) -> str:
    """Format DNS results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_dns_report_markdown(data: Dict[str, object]) -> str:
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