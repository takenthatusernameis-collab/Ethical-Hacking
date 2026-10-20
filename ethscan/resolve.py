"""DNS forward/reverse resolution module for ethscan."""
from __future__ import annotations

import csv
import io
import ipaddress
import socket

from ethscan.target import parse_url

try:
    import dns.exception
    import dns.resolver
    import dns.reversename
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


DEFAULT_RECORD_TYPES = ["A", "AAAA", "CNAME"]
DEFAULT_TIMEOUT = 2.0


def _normalize_target(target: str) -> str:
    """Extract a bare domain/IP from a target that may be a URL or host.

    Args:
        target: Bare domain (e.g. example.com), IP (e.g. 1.2.3.4), or URL.

    Returns:
        Lowercased domain/IP without scheme or path.
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


def _is_ip_address(value: str) -> bool:
    """Check if a string is a valid IP address (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def resolve_a_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve A records (IPv4 addresses) for a domain using stdlib."""
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        return []


def resolve_aaaa_records(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
    """Resolve AAAA records (IPv6 addresses) for a domain using stdlib."""
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(domain, None, socket.AF_INET6)
        ips = [r[4][0] for r in results]
        return sorted(set(ips))
    except (socket.timeout, socket.gaierror, OSError, ValueError):
        return []


def resolve_cname_records(
    domain: str, timeout: float = DEFAULT_TIMEOUT, server: str | None = None
) -> list[str]:
    """Resolve CNAME records using dnspython if available."""
    if not DNS_AVAILABLE:
        return []

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if server:
            resolver.nameservers = [server]

        answers = resolver.resolve(domain, "CNAME")
        return sorted({str(rdata) for rdata in answers})
    except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
        return []


def resolve_ptr_records(ip: str, timeout: float = DEFAULT_TIMEOUT, server: str | None = None) -> list[str]:
    """Resolve PTR records (reverse DNS) for an IP address."""
    if not DNS_AVAILABLE:
        try:
            socket.setdefaulttimeout(timeout)
            hostname, _, _ = socket.gethostbyaddr(ip)
            return [hostname]
        except (socket.timeout, socket.herror, OSError, ValueError):
            return []

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if server:
            resolver.nameservers = [server]

        rev_name = dns.reversename.from_address(ip)
        answers = resolver.resolve(rev_name, "PTR")
        return sorted({str(rdata) for rdata in answers})
    except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
        return []


def resolve_with_dnspython(
    domain: str, record_type: str, timeout: float = DEFAULT_TIMEOUT, server: str | None = None
) -> list[str]:
    """Resolve DNS records using dnspython if available."""
    if not DNS_AVAILABLE:
        return []

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if server:
            resolver.nameservers = [server]

        answers = resolver.resolve(domain, record_type)
        return sorted({str(rdata) for rdata in answers})
    except (dns.exception.DNSException, OSError, ValueError, IndexError, AttributeError, KeyError):
        return []


def run_resolve(
    target: str,
    record_types: list[str] | None = None,
    server: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Perform forward/reverse DNS resolution for a target.

    Args:
        target: Domain name, IP address, or URL (e.g. example.com, 8.8.8.8, https://example.com).
        record_types: List of DNS record types to query (A, AAAA, CNAME, PTR).
                      If None, uses DEFAULT_RECORD_TYPES (A, AAAA, CNAME) for domains,
                      or ["PTR"] for IP addresses.
        server: Custom DNS resolver IP address (only used with dnspython).
        timeout: Resolution timeout in seconds.

    Returns:
        Structured results with target, normalized target, and records per type.
    """
    normalized = _normalize_target(target)
    is_ip = _is_ip_address(normalized)

    if record_types is None:
        if is_ip:
            types = ["PTR"]
        else:
            types = DEFAULT_RECORD_TYPES
    else:
        types = record_types

    results: dict[str, list[str]] = {}
    all_supported = {"A", "AAAA", "CNAME", "PTR"}

    for rtype in types:
        rtype_upper = rtype.upper()

        if is_ip and rtype_upper != "PTR":
            continue
        if not is_ip and rtype_upper == "PTR":
            continue

        if rtype_upper == "A":
            results["A"] = resolve_a_records(normalized, timeout)
        elif rtype_upper == "AAAA":
            results["AAAA"] = resolve_aaaa_records(normalized, timeout)
        elif rtype_upper == "CNAME":
            results["CNAME"] = resolve_cname_records(normalized, timeout, server)
        elif rtype_upper == "PTR":
            results["PTR"] = resolve_ptr_records(normalized, timeout, server)
        elif rtype_upper in all_supported:
            continue  # should not happen due to above
        else:
            if DNS_AVAILABLE:
                results[rtype_upper] = resolve_with_dnspython(normalized, rtype_upper, timeout, server)
            else:
                continue  # ignore unknown types when dnspython unavailable

    return {
        "target": target,
        "normalized": normalized,
        "is_ip": is_ip,
        "record_types_queried": types,
        "records": results,
        "dnspython_available": DNS_AVAILABLE,
        "server": server,
    }


def format_resolve_report_json(data: dict[str, object]) -> str:
    """Format resolve results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_resolve_report_markdown(data: dict[str, object]) -> str:
    """Format resolve results as Markdown."""
    records = data["records"]
    lines = ["# ethscan DNS Forward/Reverse Resolution Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Normalized:** {data['normalized']}")
    lines.append(f"- **Type:** {'IP Address' if data['is_ip'] else 'Domain Name'}")
    lines.append(f"- **Record Types Queried:** {', '.join(data['record_types_queried'])}")
    lines.append(f"- **dnspython Available:** {'Yes' if data['dnspython_available'] else 'No (stdlib only)'}")
    server = data.get("server")
    if server:
        lines.append(f"- **Custom Resolver:** {server}")
    lines.append("")

    def _escape(value: str) -> str:
        return value.replace("|", "\\|")

    for rtype, values in records.items():
        lines.append(f"## {rtype} Records")
        if values:
            for value in values:
                lines.append(f"- {_escape(str(value))}")
        else:
            lines.append("*No records found*")
        lines.append("")

    return "\n".join(lines)


def format_resolve_report_csv(data: dict[str, object]) -> str:
    """Format resolve results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target", "normalized", "record_type", "record_value"])
    for rtype, values in (data.get("records") or {}).items():
        for value in values or []:
            writer.writerow([
                data.get("target", ""),
                data.get("normalized", ""),
                str(rtype),
                str(value),
            ])
    return output.getvalue().rstrip("\r\n")