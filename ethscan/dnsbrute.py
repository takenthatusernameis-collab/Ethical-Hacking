"""DNS brute force module for ethscan (AXFR attempt + subdomain brute force)."""

import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ethscan.dns import resolve_a_records, resolve_aaaa_records, resolve_with_dnspython
from ethscan.subdomains import DEFAULT_SUBDOMAINS, load_subdomain_wordlist  # noqa: F401

try:
    import dns.exception
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


DEFAULT_TIMEOUT = 2.0
DNS_PORT = 53
AXFR_QTYPE = 252
DEFAULT_QUERY_ID = 0x2B00

RCODE_NAMES = {
    0: "NOERROR",
    1: "FORMERR",
    2: "SERVFAIL",
    3: "NXDOMAIN",
    4: "NOTIMP",
    5: "REFUSED",
    6: "YXDOMAIN",
    7: "YXRRSET",
    8: "NXRRSET",
    9: "NOTAUTH",
    10: "NOTZONE",
}


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
    parsed = urlparse(normalized)
    return parsed.netloc.lower()


def build_axfr_query(zone: str, query_id: int = DEFAULT_QUERY_ID) -> bytes:
    """Build a TCP-prefixed DNS AXFR query message for a zone.

    Args:
        zone: Zone to transfer (e.g. example.com).
        query_id: DNS transaction identifier.

    Returns:
        DNS message prefixed with the 2-byte TCP length.
    """
    header = struct.pack(
        ">HHHHHH", query_id, 0x0000, 1, 0, 0, 0
    )
    labels = [
        label for label in zone.strip().rstrip(".").split(".") if label
    ]
    question = b"".join(
        bytes([len(label)]) + label.encode("ascii", errors="replace")
        for label in labels
    ) + b"\x00"
    question += struct.pack(">HH", AXFR_QTYPE, 1)

    message = header + question
    return struct.pack(">H", len(message)) + message


def _parse_dns_name(data: bytes, offset: int) -> Tuple[str, int]:
    """Parse a (possibly compressed) DNS name starting at offset.

    Args:
        data: Raw DNS message bytes.
        offset: Byte offset to start parsing at.

    Returns:
        Tuple of (name, new_offset) where new_offset points past the
        name in the original message (after any compression pointer).
    """
    labels: List[str] = []
    jumped = False
    end_offset = offset
    seen = set()

    while True:
        if offset >= len(data):
            break
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                offset += 2
                break
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if pointer in seen or pointer >= len(data):
                offset += 2
                break
            seen.add(pointer)
            if not jumped:
                end_offset = offset + 2
                jumped = True
            offset = pointer
            continue
        if length & 0xC0 != 0:
            offset += 1
            break
        offset += 1
        if offset + length > len(data):
            break
        labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
        offset += length

    if not jumped:
        end_offset = offset
    return ".".join(labels), end_offset


def parse_dns_response(data: bytes) -> Dict[str, object]:
    """Parse a raw DNS response message.

    Args:
        data: Raw DNS response bytes (without TCP length prefix).

    Returns:
        Dictionary with header fields and parsed answer records.
    """
    result: Dict[str, object] = {
        "valid": False,
        "query_id": None,
        "response_code": None,
        "response_code_name": None,
        "question_count": 0,
        "answer_count": 0,
        "authority_count": 0,
        "additional_count": 0,
        "answers": [],
    }
    if len(data) < 12:
        return result

    query_id = struct.unpack(">H", data[0:2])[0]
    flags = struct.unpack(">H", data[2:4])[0]
    response_code = flags & 0x000F
    question_count = struct.unpack(">H", data[4:6])[0]
    answer_count = struct.unpack(">H", data[6:8])[0]
    authority_count = struct.unpack(">H", data[8:10])[0]
    additional_count = struct.unpack(">H", data[10:12])[0]

    result.update(
        {
            "valid": True,
            "query_id": query_id,
            "response_code": response_code,
            "response_code_name": RCODE_NAMES.get(response_code, "UNKNOWN"),
            "question_count": question_count,
            "answer_count": answer_count,
            "authority_count": authority_count,
            "additional_count": additional_count,
        }
    )

    offset = 12
    for _ in range(question_count):
        _, offset = _parse_dns_name(data, offset)
        offset += 4

    answers: List[Dict[str, object]] = []
    for _ in range(answer_count):
        name, offset = _parse_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        record_type = struct.unpack(">H", data[offset:offset + 2])[0]
        rdlength = struct.unpack(">H", data[offset + 8:offset + 10])[0]
        offset += 10 + rdlength
        answers.append({"name": name, "type": record_type})

    result["answers"] = answers
    return result


def _axfr_result(
    nameserver: str, success: bool, records: List[str], error: Optional[str]
) -> Dict[str, object]:
    """Build a single AXFR attempt result entry."""
    return {
        "nameserver": nameserver,
        "success": success,
        "records_count": len(records),
        "records": records,
        "error": error,
    }


def query_axfr_raw(
    nameserver: str,
    zone: str,
    timeout: float = DEFAULT_TIMEOUT,
    port: int = DNS_PORT,
) -> Dict[str, object]:
    """Attempt a DNS zone transfer (AXFR) using a raw TCP socket.

    Args:
        nameserver: Authoritative nameserver hostname or IP.
        zone: Zone to transfer (e.g. example.com).
        timeout: Connection/read timeout in seconds.
        port: DNS server port (default: 53).

    Returns:
        AXFR attempt result with success flag, records, and error.
    """
    query = build_axfr_query(zone)
    try:
        with socket.create_connection((nameserver, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(query)
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
    except (socket.timeout, socket.gaierror, OSError) as exc:
        message = str(exc) or exc.__class__.__name__
        return _axfr_result(nameserver, False, [], message)

    parsed = parse_dns_response(data)
    if not parsed["valid"]:
        return _axfr_result(nameserver, False, [], "invalid response")
    if parsed["response_code"] != 0:
        code_name = parsed["response_code_name"]
        return _axfr_result(nameserver, False, [], f"transfer refused ({code_name})")
    if parsed["answer_count"] == 0:
        return _axfr_result(nameserver, False, [], "empty response (no records)")

    records = [
        str(answer["name"]) for answer in parsed["answers"] if answer["name"]
    ]
    return _axfr_result(nameserver, True, records, None)


def _axfr_dnspython(
    nameserver: str,
    zone: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, object]:
    """Attempt a DNS zone transfer (AXFR) using dnspython.

    Args:
        nameserver: Authoritative nameserver hostname or IP.
        zone: Zone to transfer (e.g. example.com).
        timeout: Query timeout in seconds.

    Returns:
        AXFR attempt result with success flag, records, and error.
    """
    try:
        import dns.query
        import dns.zone
    except ImportError:
        return _axfr_result(nameserver, False, [], "dnspython not installed")

    try:
        xfr_source = dns.query.xfr(nameserver, zone, timeout=timeout, lifetime=timeout)
        zone_obj = dns.zone.from_xfr(xfr_source)
    except dns.exception.FormError as exc:
        return _axfr_result(nameserver, False, [], f"transfer refused ({exc})")
    except (dns.exception.DNSException, OSError, ValueError) as exc:
        return _axfr_result(nameserver, False, [], str(exc))

    records: List[str] = []
    for name in sorted(zone_obj.nodes.keys(), key=str):
        node = zone_obj.nodes[name]
        for rdataset in node.rdatasets:
            for rdata in rdataset:
                records.append(
                    f"{name} {rdataset.ttl} IN {rdataset.rdtype_name} {rdata}"
                )
    return _axfr_result(nameserver, True, records, None)


def attempt_axfr(
    nameserver: str,
    zone: str,
    timeout: float = DEFAULT_TIMEOUT,
    port: int = DNS_PORT,
) -> Dict[str, object]:
    """Attempt a DNS zone transfer (AXFR) against a nameserver.

    Uses dnspython when available, falling back to a raw TCP socket
    implementation otherwise.

    Args:
        nameserver: Authoritative nameserver hostname or IP.
        zone: Zone to transfer (e.g. example.com).
        timeout: Query timeout in seconds.
        port: DNS server port (default: 53).

    Returns:
        AXFR attempt result with success flag, records, and error.
    """
    if DNS_AVAILABLE:
        return _axfr_dnspython(nameserver, zone, timeout=timeout)
    return query_axfr_raw(nameserver, zone, timeout=timeout, port=port)


def discover_nameservers(domain: str, timeout: float = DEFAULT_TIMEOUT) -> List[str]:
    """Discover authoritative nameservers for a domain via NS lookup.

    Args:
        domain: Domain to look up.
        timeout: Resolution timeout in seconds.

    Returns:
        Sorted list of nameserver hostnames (empty when dnspython
        is unavailable or the lookup fails).
    """
    if not DNS_AVAILABLE:
        return []
    values = resolve_with_dnspython(domain, "NS", timeout=timeout)
    return sorted({value.rstrip(".") for value in values if value.strip()})


def _resolve_label(label: str, domain: str, timeout: float, resolver: Optional[str] = None) -> Dict[str, object]:
    """Resolve a single subdomain label to its A and AAAA records."""
    hostname = f"{label}.{domain}"
    a_records: List[str] = []
    aaaa_records: List[str] = []
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "A")
            a_records = sorted(set(str(rdata) for rdata in answers))
        except (dns.exception.DNSException, OSError, ValueError):
            pass
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "AAAA")
            aaaa_records = sorted(set(str(rdata) for rdata in answers))
        except (dns.exception.DNSException, OSError, ValueError):
            pass
    else:
        a_records = resolve_a_records(hostname, timeout=timeout)
        aaaa_records = resolve_aaaa_records(hostname, timeout=timeout)
    return {
        "subdomain": label,
        "hostname": hostname,
        "a": a_records,
        "aaaa": aaaa_records,
    }


def run_dnsbrute(
    target: str,
    nameservers: Optional[List[str]] = None,
    subdomains: Optional[List[str]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = 50,
    resolver: Optional[str] = None,
) -> Dict[str, object]:
    """Attempt AXFR zone transfers and brute-force subdomains for a target.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        nameservers: Authoritative nameservers for AXFR attempts. If None,
                     discovered via NS lookup (requires dnspython).
        subdomains: List of subdomain labels to test. If None, uses
                    the built-in DEFAULT_SUBDOMAINS list.
        timeout: DNS timeout in seconds.
        max_workers: Maximum number of concurrent resolution workers.
        resolver: Custom DNS resolver IP address (requires dnspython).

    Returns:
        Structured results with nameservers, AXFR attempts, and resolved
        subdomains with their A/AAAA records.
    """
    domain = _normalize_domain(target)
    labels = subdomains if subdomains is not None else DEFAULT_SUBDOMAINS

    if nameservers is not None:
        ns_list = sorted({ns.strip() for ns in nameservers if ns and ns.strip()})
        ns_source = "option"
    else:
        ns_list = discover_nameservers(domain, timeout=timeout)
        ns_source = "lookup" if ns_list else "none"

    axfr_results: List[Dict[str, object]] = []
    for ns in ns_list:
        axfr_results.append(attempt_axfr(ns, domain, timeout=timeout))

    axfr_success = any(entry["success"] for entry in axfr_results)
    axfr_total_records = sum(entry["records_count"] for entry in axfr_results)

    results: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_label = {
            executor.submit(_resolve_label, label, domain, timeout, resolver): label
            for label in labels
        }
        for future in as_completed(future_to_label):
            results.append(future.result())

    resolved = [entry for entry in results if entry["a"] or entry["aaaa"]]

    return {
        "target": target,
        "domain": domain,
        "zone": domain,
        "nameservers": ns_list,
        "nameserver_source": ns_source,
        "dnspython_available": DNS_AVAILABLE,
        "axfr": axfr_results,
        "axfr_success": axfr_success,
        "axfr_total_records": axfr_total_records,
        "subdomains_tested": len(labels),
        "resolved_count": len(resolved),
        "resolved": sorted(resolved, key=lambda entry: entry["subdomain"]),
        "all_results": sorted(results, key=lambda entry: entry["subdomain"]),
        "resolver": resolver,
    }


def format_dnsbrute_report_json(data: Dict[str, object]) -> str:
    """Format DNS brute force results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _format_records_table(lines: List[str], entries: List[Dict[str, object]]) -> None:
    lines.append("| Subdomain | Hostname | A | AAAA |")
    lines.append("|-----------|----------|---|------|")
    for entry in entries:
        a_records = ", ".join(entry["a"]) if entry["a"] else "N/A"
        aaaa_records = ", ".join(entry["aaaa"]) if entry["aaaa"] else "N/A"
        lines.append(
            f"| {_markdown_escape(entry['subdomain'])} | "
            f"{_markdown_escape(entry['hostname'])} | "
            f"{_markdown_escape(a_records)} | "
            f"{_markdown_escape(aaaa_records)} |"
        )
    lines.append("")


def format_dnsbrute_report_markdown(data: Dict[str, object]) -> str:
    """Format DNS brute force results as Markdown."""
    lines = ["# ethscan DNS Brute Force Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    lines.append(f"- **Zone:** {data['zone']}")
    nameservers = ", ".join(data["nameservers"]) if data["nameservers"] else "None"
    lines.append(
        f"- **Nameservers:** {nameservers} (source: {data['nameserver_source']})"
    )
    resolver = data.get("resolver")
    if resolver:
        lines.append(
            f"- **Resolver:** {resolver} (dnspython: {'Yes' if data['dnspython_available'] else 'No'})"
        )
    lines.append(
        f"- **dnspython Available:** "
        f"{'Yes' if data['dnspython_available'] else 'No (stdlib only)'}"
    )
    lines.append(f"- **AXFR Successful:** {'Yes' if data['axfr_success'] else 'No'}")
    lines.append(f"- **AXFR Records:** {data['axfr_total_records']}")
    lines.append(f"- **Subdomains Tested:** {data['subdomains_tested']}")
    lines.append(f"- **Resolved:** {data['resolved_count']}")
    lines.append("")

    lines.append("## AXFR Attempts")
    if data["axfr"]:
        for entry in data["axfr"]:
            lines.append(f"### {entry['nameserver']}")
            lines.append(f"- **Success:** {'Yes' if entry['success'] else 'No'}")
            lines.append(f"- **Records:** {entry['records_count']}")
            if entry["error"]:
                lines.append(f"- **Error:** {entry['error']}")
            if entry["records"]:
                lines.append("")
                lines.append("```")
                for record in entry["records"]:
                    lines.append(str(record))
                lines.append("```")
            lines.append("")
    else:
        lines.append("*No nameservers available for AXFR attempts.*")
        lines.append("")

    lines.append("## Resolved Subdomains")
    _format_records_table(lines, data["resolved"])

    lines.append("## All Results")
    _format_records_table(lines, data["all_results"])

    return "\n".join(lines)
