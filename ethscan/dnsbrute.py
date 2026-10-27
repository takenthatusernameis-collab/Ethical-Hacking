"""DNS brute force module for ethscan (AXFR attempt + subdomain brute force)."""
from __future__ import annotations

import csv
import io
import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import cast

from ethscan.dns import resolve_a_records, resolve_aaaa_records, resolve_with_dnspython
from ethscan.subdomains import DEFAULT_SUBDOMAINS
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


DEFAULT_TIMEOUT = 2.0
DNS_PORT = 53
AXFR_QTYPE = 252
DEFAULT_QUERY_ID = 0x2B00
DEFAULT_RECURSIVE_DEPTH = 2

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
    parsed = parse_url(normalized)
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


def _parse_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Parse a (possibly compressed) DNS name starting at offset.

    Args:
        data: Raw DNS message bytes.
        offset: Byte offset to start parsing at.

    Returns:
        Tuple of (name, new_offset) where new_offset points past the
        name in the original message (after any compression pointer).
    """
    labels: list[str] = []
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


def parse_dns_response(data: bytes) -> dict[str, object]:
    """Parse a raw DNS response message.

    Args:
        data: Raw DNS response bytes (without TCP length prefix).

    Returns:
        Dictionary with header fields and parsed answer records.
    """
    result: dict[str, object] = {
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

    answers: list[dict[str, object]] = []
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
    nameserver: str, success: bool, records: list[str], error: str | None
) -> dict[str, object]:
    """Build a single AXFR attempt result entry."""
    return {
        "nameserver": nameserver,
        "success": success,
        "records_count": len(records),
        "records": records,
        "error": error,
    }


def _extract_ns_records(records: list[str]) -> list[str]:
    """Extract NS record target hostnames from AXFR records.

    Args:
        records: List of AXFR record strings in format "NAME TTL IN TYPE RDATA".

    Returns:
        Sorted list of unique nameserver hostnames found in NS records.
    """
    ns_names: set = set()
    for record in records:
        parts = record.split()
        if len(parts) >= 4 and parts[3] == "NS":
            # NS record format: name ttl IN NS target
            target = parts[4] if len(parts) > 4 else ""
            if target:
                ns_names.add(target.rstrip("."))
    return sorted(ns_names)


def _is_subdomain_of(hostname: str, domain: str) -> bool:
    """Check if hostname is a subdomain of domain (including exact match)."""
    hostname = hostname.rstrip(".")
    domain = domain.rstrip(".")
    return hostname == domain or hostname.endswith("." + domain)


def query_axfr_raw(
    nameserver: str,
    zone: str,
    timeout: float = DEFAULT_TIMEOUT,
    port: int = DNS_PORT,
) -> dict[str, object]:
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
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        message = str(exc) or exc.__class__.__name__
        return _axfr_result(nameserver, False, [], message)

    parsed = parse_dns_response(data)
    if not parsed.get("valid"):
        return _axfr_result(nameserver, False, [], "invalid response")
    if parsed.get("response_code") != 0:
        code_name = parsed.get("response_code_name")
        return _axfr_result(nameserver, False, [], f"transfer refused ({code_name})")
    if parsed.get("answer_count") == 0:
        return _axfr_result(nameserver, False, [], "empty response (no records)")

    parsed_answers = parsed.get("answers") or []
    records = [
        str(cast(dict[str, object], answer).get("name", ""))
        for answer in cast(list[object], parsed_answers)
        if cast(dict[str, object], answer).get("name")
    ]
    return _axfr_result(nameserver, True, records, None)


def _axfr_dnspython(
    nameserver: str,
    zone: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
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
    # A transport failure of an unnamed type must not escape the command, the
    # same way the raw socket path reports it.  Fall back to the exception
    # class name when the message is empty, so a malformed zone-transfer
    # response (which dnspython raises as ValueError() with no message) is
    # reported instead of an empty string.
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        message = str(exc) or exc.__class__.__name__
        return _axfr_result(nameserver, False, [], message)

    records: list[str] = []
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
) -> dict[str, object]:
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


def discover_nameservers(domain: str, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
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


def _resolve_label(label: str, domain: str, timeout: float, resolver: str | None = None) -> dict[str, object]:
    """Resolve a single subdomain label to its A and AAAA records."""
    hostname = f"{label}.{domain}"
    a_records: list[str] = []
    aaaa_records: list[str] = []
    if resolver and DNS_AVAILABLE:
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "A")
            a_records = sorted({str(rdata) for rdata in answers})
        # A transport failure of an unnamed type must not escape the command.
        except Exception:  # noqa: BLE001, S110 - resolver can raise any type
            pass
        try:
            dns_resolver = dns.resolver.Resolver()
            dns_resolver.timeout = timeout
            dns_resolver.lifetime = timeout
            dns_resolver.nameservers = [resolver]
            answers = dns_resolver.resolve(hostname, "AAAA")
            aaaa_records = sorted({str(rdata) for rdata in answers})
        # A transport failure of an unnamed type must not escape the command.
        except Exception:  # noqa: BLE001, S110 - resolver can raise any type
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
    nameservers: list[str] | None = None,
    subdomains: list[str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = 50,
    resolver: str | None = None,
    recursive: bool = False,
    max_depth: int = DEFAULT_RECURSIVE_DEPTH,
) -> dict[str, object]:
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
        recursive: If True, attempt recursive AXFR against nameservers
                   discovered in successful zone transfers.
        max_depth: Maximum recursion depth for recursive AXFR attempts.

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

    axfr_results: list[dict[str, object]] = []
    recursive_axfr_results: list[dict[str, object]] = []

    def _run_axfr_for_zone(zone: str, ns_candidates: list[str], depth: int) -> None:
        """Run AXFR attempts for a zone and optionally recurse."""
        if depth > max_depth:
            return
        for ns in ns_candidates:
            result = attempt_axfr(ns, zone, timeout=timeout)
            axfr_entry = {
                "nameserver": ns,
                "zone": zone,
                "depth": depth,
                "success": bool(result.get("success")),
                "records_count": int(cast(int, result.get("records_count") or 0)),
                "records": result.get("records") or [],
                "error": result.get("error"),
            }
            if depth == 1:
                axfr_results.append(axfr_entry)
            else:
                recursive_axfr_results.append(axfr_entry)

            # If successful and we can recurse deeper, extract NS records and continue
            if result.get("success") and depth < max_depth:
                records = result.get("records") or []
                ns_records = _extract_ns_records(cast(list[str], records))
                # Filter to only nameservers that are subdomains of the original domain
                filtered_ns = [ns_name for ns_name in ns_records if _is_subdomain_of(ns_name, domain)]
                if filtered_ns:
                    _run_axfr_for_zone(zone, filtered_ns, depth + 1)

    # Initial AXFR attempts
    _run_axfr_for_zone(domain, ns_list, 1)

    axfr_success = any(bool(entry.get("success")) for entry in axfr_results)
    axfr_total_records = sum(int(cast(int, entry.get("records_count") or 0)) for entry in axfr_results)
    recursive_total_records = sum(int(cast(int, entry.get("records_count") or 0)) for entry in recursive_axfr_results)

    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_label = {
            executor.submit(_resolve_label, label, domain, timeout, resolver): label
            for label in labels
        }
        for future in as_completed(future_to_label):
            results.append(future.result())

    resolved = [entry for entry in results if entry.get("a") or entry.get("aaaa")]

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
        "recursive_axfr": recursive_axfr_results,
        "recursive_axfr_total_records": recursive_total_records,
        "subdomains_tested": len(labels),
        "resolved_count": len(resolved),
        "resolved": sorted(resolved, key=lambda entry: cast(str, entry["subdomain"])),
        "all_results": sorted(results, key=lambda entry: cast(str, entry["subdomain"])),
        "resolver": resolver,
        "recursive": recursive,
        "max_depth": max_depth if recursive else 0,
    }


def format_dnsbrute_report_json(data: dict[str, object]) -> str:
    """Format DNS brute force results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _format_records_table(lines: list[str], entries: list[dict[str, object]]) -> None:
    lines.append("| Subdomain | Hostname | A | AAAA |")
    lines.append("|-----------|----------|---|------|")
    for entry in entries:
        a_raw = entry.get("a") or []
        aaaa_raw = entry.get("aaaa") or []
        a_records = ", ".join(str(x) for x in cast(list[object], a_raw)) if a_raw else "N/A"
        aaaa_records = ", ".join(str(x) for x in cast(list[object], aaaa_raw)) if aaaa_raw else "N/A"
        lines.append(
            f"| {_markdown_escape(entry.get('subdomain'))} | "
            f"{_markdown_escape(entry.get('hostname'))} | "
            f"{_markdown_escape(a_records)} | "
            f"{_markdown_escape(aaaa_records)} |"
        )
    lines.append("")


def format_dnsbrute_report_markdown(data: dict[str, object]) -> str:
    """Format DNS brute force results as Markdown."""
    lines = ["# ethscan DNS Brute Force Report", ""]
    lines.append(f"- **Target:** {data.get('target')}")
    lines.append(f"- **Domain:** {data.get('domain')}")
    lines.append(f"- **Zone:** {data.get('zone')}")
    ns_list_md = cast(list[object], data.get("nameservers") or [])
    nameservers = ", ".join(str(x) for x in ns_list_md) if ns_list_md else "None"
    lines.append(
        f"- **Nameservers:** {nameservers} (source: {data.get('nameserver_source')})"
    )
    resolver = data.get("resolver")
    if resolver:
        lines.append(
            f"- **Resolver:** {resolver} (dnspython: {'Yes' if data.get('dnspython_available') else 'No'})"
        )
    lines.append(
        f"- **dnspython Available:** "
        f"{'Yes' if data.get('dnspython_available') else 'No (stdlib only)'}"
    )
    if data.get("recursive"):
        lines.append(f"- **Recursive AXFR:** Yes (max depth: {data.get('max_depth', 0)})")
        lines.append(f"- **Recursive AXFR Records:** {data.get('recursive_axfr_total_records', 0)}")
    lines.append(f"- **AXFR Successful:** {'Yes' if data.get('axfr_success') else 'No'}")
    lines.append(f"- **AXFR Records:** {data.get('axfr_total_records')}")
    lines.append(f"- **Subdomains Tested:** {data.get('subdomains_tested')}")
    lines.append(f"- **Resolved:** {data.get('resolved_count')}")
    lines.append("")

    lines.append("## AXFR Attempts")
    axfr_entries = cast(list[object], data.get("axfr") or [])
    if axfr_entries:
        for entry_raw in axfr_entries:
            entry = cast(dict[str, object], entry_raw)
            lines.append(f"### {entry.get('nameserver')} (zone: {entry.get('zone', data.get('zone'))}, depth: {entry.get('depth', 1)})")
            lines.append(f"- **Success:** {'Yes' if entry.get('success') else 'No'}")
            lines.append(f"- **Records:** {entry.get('records_count')}")
            if entry.get("error"):
                lines.append(f"- **Error:** {entry.get('error')}")
            records_axfr = cast(list[object], entry.get("records") or [])
            if records_axfr:
                lines.append("")
                lines.append("```")
                for record in records_axfr:
                    lines.append(str(record))
                lines.append("```")
            lines.append("")
    else:
        lines.append("*No nameservers available for AXFR attempts.*")
        lines.append("")

    # Recursive AXFR attempts
    recursive_axfr = cast(list[object], data.get("recursive_axfr", []) or [])
    if recursive_axfr:
        lines.append("## Recursive AXFR Attempts")
        for entry_raw in recursive_axfr:
            entry = cast(dict[str, object], entry_raw)
            lines.append(f"### {entry.get('nameserver')} (zone: {entry.get('zone', data.get('zone'))}, depth: {entry.get('depth', 0)})")
            lines.append(f"- **Success:** {'Yes' if entry.get('success') else 'No'}")
            lines.append(f"- **Records:** {entry.get('records_count')}")
            if entry.get("error"):
                lines.append(f"- **Error:** {entry.get('error')}")
            records_axfr_r = cast(list[object], entry.get("records") or [])
            if records_axfr_r:
                lines.append("")
                lines.append("```")
                for record in records_axfr_r:
                    lines.append(str(record))
                lines.append("```")
            lines.append("")
        lines.append("")

    lines.append("## Resolved Subdomains")
    _format_records_table(lines, cast(list[dict[str, object]], data.get("resolved") or []))

    lines.append("## All Results")
    _format_records_table(lines, cast(list[dict[str, object]], data.get("all_results") or []))

    return "\n".join(lines)


def _dnsbrute_csv_header() -> list[str]:
    """Return the CSV header row for dnsbrute output."""
    return [
        "target",
        "domain",
        "record_type",
        "subdomain",
        "hostname",
        "a_records",
        "aaaa_records",
        "resolved",
        "nameserver",
        "zone",
        "depth",
        "success",
        "error",
        "record",
    ]


def _dnsbrute_subdomain_row(
    target: str, domain: str, entry: dict[str, object]
) -> list[str]:
    """Build a CSV row for a subdomain brute-force result."""
    a_raw = entry.get("a") or []
    aaaa_raw = entry.get("aaaa") or []
    a_records = cast(list[object], a_raw)
    aaaa_records = cast(list[object], aaaa_raw)
    return [
        target,
        domain,
        "subdomain",
        str(entry.get("subdomain", "")),
        str(entry.get("hostname", "")),
        " ".join(str(ip) for ip in a_records),
        " ".join(str(ip) for ip in aaaa_records),
        "true" if (a_records or aaaa_records) else "false",
        "",
        "",
        "",
        "",
        "",
        "",
    ]


def _dnsbrute_axfr_row(
    target: str, domain: str, entry: dict[str, object], record: str, record_type: str
) -> list[str]:
    """Build a CSV row for an AXFR record (initial or recursive)."""
    return [
        target,
        domain,
        record_type,
        "",
        "",
        "",
        "",
        "",
        str(entry.get("nameserver", "")),
        str(entry.get("zone", domain)),
        str(entry.get("depth", 1)),
        "true" if entry.get("success") else "false",
        str(entry.get("error", "") or ""),
        record,
    ]


def format_dnsbrute_report_csv(data: dict[str, object]) -> str:
    """Format dnsbrute results as CSV.

    Emits a header row followed by:
    1. Subdomain brute-force results (record_type="subdomain")
    2. AXFR zone-transfer records (record_type="axfr")
    3. Recursive AXFR records (record_type="recursive_axfr")

    All rows share the same schema; non-applicable fields are left empty.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_dnsbrute_csv_header())

    target = str(data.get("target", "") or "")
    domain = str(data.get("domain", "") or "")

    # Subdomain brute-force results
    for entry in cast(list[object], data.get("all_results", []) or []):
        writer.writerow(_dnsbrute_subdomain_row(target, domain, cast(dict[str, object], entry)))

    # Initial AXFR attempts
    for entry in cast(list[object], data.get("axfr", []) or []):
        entry_dict = cast(dict[str, object], entry)
        records_raw = entry_dict.get("records", []) or []
        records = cast(list[object], records_raw)
        if records:
            for record in records:
                writer.writerow(_dnsbrute_axfr_row(target, domain, entry_dict, str(record), "axfr"))
        else:
            # Emit a row even for failed/empty AXFR attempts to preserve metadata
            writer.writerow(_dnsbrute_axfr_row(target, domain, entry_dict, "", "axfr"))

    # Recursive AXFR attempts
    for entry in cast(list[object], data.get("recursive_axfr", []) or []):
        entry_dict = cast(dict[str, object], entry)
        records_raw = entry_dict.get("records", []) or []
        records = cast(list[object], records_raw)
        if records:
            for record in records:
                writer.writerow(_dnsbrute_axfr_row(target, domain, entry_dict, str(record), "recursive_axfr"))
        else:
            writer.writerow(_dnsbrute_axfr_row(target, domain, entry_dict, "", "recursive_axfr"))

    return output.getvalue().rstrip("\r\n")
