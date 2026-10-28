"""DNSSEC validation module for ethscan."""
from __future__ import annotations

import csv
import io
import socket
import struct

from ethscan.target import parse_url

try:
    try:
        import dns.enum
        import dns.message
    except Exception:  # noqa: BLE001, S110
        pass
    import dns.dnssec
    import dns.exception
    import dns.flags
    import dns.message
    import dns.query
    import dns.resolver
    DNS_AVAILABLE = True
except Exception:  # noqa: BLE001
    DNS_AVAILABLE = False


DEFAULT_TIMEOUT = 5.0
DNS_PORT = 53

DNSKEY_QTYPE = 48
DS_QTYPE = 43
RRSIG_QTYPE = 46
NSEC_QTYPE = 47
NSEC3_QTYPE = 50

ALGORITHM_NAMES = {
    1: "RSAMD5",
    2: "DH",
    3: "DSA",
    4: "ECC",
    5: "RSASHA1",
    6: "DSA-NSEC3-SHA1",
    7: "RSASHA1-NSEC3-SHA1",
    8: "RSASHA256",
    9: "RSASHA512",
    10: "ECC-GOST",
    11: "ECDSAP256SHA256",
    12: "ECDSAP384SHA384",
    13: "ED25519",
    14: "ED448",
    15: "INDIRECT",
    16: "PRIVATEDNS",
    17: "PRIVATEOID",
}

DIGEST_TYPE_NAMES = {
    1: "SHA-1",
    2: "SHA-256",
    3: "GOST R 34.11-94",
    4: "SHA-384",
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


def _get_parent_zone(domain: str) -> str:
    """Get the parent zone of a domain (e.g., example.com -> com).

    Args:
        domain: Domain name.

    Returns:
        Parent zone name.
    """
    labels = domain.strip().rstrip(".").split(".")
    if len(labels) <= 1:
        return "."
    return ".".join(labels[1:]) + "."


def _build_dns_query(name: str, qtype: int, want_dnssec: bool = True) -> bytes:
    """Build a DNS query message.

    Args:
        name: Domain name to query.
        qtype: Query type (e.g., DNSKEY, DS).
        want_dnssec: Whether to set the DO (DNSSEC OK) bit.

    Returns:
        DNS query message bytes.
    """
    import random
    query_id = random.randint(0, 65535)
    flags = 0x0100  # Standard query with recursion desired
    if want_dnssec:
        flags |= 0x8000  # DO bit (DNSSEC OK)
    header = struct.pack(">HHHHHH", query_id, flags, 1, 0, 0, 0)
    labels = [label for label in name.strip().rstrip(".").split(".") if label]
    question = b"".join(
        bytes([len(label)]) + label.encode("ascii", errors="replace")
        for label in labels
    ) + b"\x00"
    question += struct.pack(">HH", qtype, 1)
    return header + question


def _parse_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Parse a (possibly compressed) DNS name starting at offset."""
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


def _query_udp(
    nameserver: str,
    query: bytes,
    timeout: float = DEFAULT_TIMEOUT,
    port: int = DNS_PORT,
) -> bytes | None:
    """Send a DNS query via UDP and return the response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(query, (nameserver, port))
            data, _ = sock.recvfrom(4096)
            return data
    except Exception:  # noqa: BLE001 - transport can raise any type
        return None


def _query_tcp(
    nameserver: str,
    query: bytes,
    timeout: float = DEFAULT_TIMEOUT,
    port: int = DNS_PORT,
) -> bytes | None:
    """Send a DNS query via TCP and return the response."""
    try:
        with socket.create_connection((nameserver, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            length_prefix = struct.pack(">H", len(query))
            sock.sendall(length_prefix + query)
            length_data = sock.recv(2)
            if len(length_data) < 2:
                return None
            resp_len = struct.unpack(">H", length_data)[0]
            data = b""
            while len(data) < resp_len:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data[:resp_len]
    except Exception:  # noqa: BLE001 - transport can raise any type
        return None


def _resolve_nameservers(domain: str, timeout: float) -> list[str]:
    """Resolve authoritative nameservers for a domain using stdlib."""
    try:
        previous = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            results = socket.getaddrinfo(domain, DNS_PORT, socket.AF_INET, socket.SOCK_DGRAM)
            ips = sorted({r[4][0] for r in results if isinstance(r[4], tuple) and len(r[4]) > 0 and isinstance(r[4][0], str)})
            return ips
        finally:
            socket.setdefaulttimeout(previous)
    # A domain that is not a valid host name ("....") raises a UnicodeError,
    # which is a ValueError, when the resolver encodes it.
    except Exception:  # noqa: BLE001 - resolver can raise any type
        return []


def _query_dnskey_raw(
    nameserver: str,
    domain: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Query DNSKEY records using raw UDP/TCP socket."""
    query = _build_dns_query(domain, DNSKEY_QTYPE, want_dnssec=True)
    response = _query_udp(nameserver, query, timeout)
    if response is None or len(response) > 512:
        response = _query_tcp(nameserver, query, timeout)
    if response is None:
        return {"success": False, "keys": [], "error": "no response"}
    return _parse_dnskey_response(response, domain)


def _query_ds_raw(
    nameserver: str,
    domain: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Query DS records using raw UDP/TCP socket."""
    query = _build_dns_query(domain, DS_QTYPE, want_dnssec=True)
    response = _query_udp(nameserver, query, timeout)
    if response is None or len(response) > 512:
        response = _query_tcp(nameserver, query, timeout)
    if response is None:
        return {"success": False, "records": [], "error": "no response"}
    return _parse_ds_response(response, domain)


def _parse_dnskey_response(data: bytes, domain: str) -> dict[str, object]:
    """Parse DNSKEY response."""
    result: dict[str, object] = {
        "success": False,
        "keys": [],
        "error": None,
    }
    if len(data) < 12:
        result["error"] = "response too short"
        return result

    struct.unpack(">H", data[0:2])[0]
    flags = struct.unpack(">H", data[2:4])[0]
    response_code = flags & 0x000F
    if response_code != 0:
        result["error"] = f"response code {response_code}"
        return result

    question_count = struct.unpack(">H", data[4:6])[0]
    answer_count = struct.unpack(">H", data[6:8])[0]

    offset = 12
    for _ in range(question_count):
        _, offset = _parse_dns_name(data, offset)
        offset += 4

    keys = []
    for _ in range(answer_count):
        name, offset = _parse_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        record_type = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        offset += 2  # class
        offset += 4  # ttl
        rdlength = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2

        if record_type == DNSKEY_QTYPE:
            if offset + 4 > len(data):
                break
            key_flags = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            protocol = data[offset]
            offset += 1
            algorithm = data[offset]
            offset += 1
            key_data = data[offset:offset + rdlength - 4] if rdlength >= 4 else b""
            offset += rdlength - 4

            keys.append({
                "name": name,
                "flags": key_flags,
                "protocol": protocol,
                "algorithm": algorithm,
                "algorithm_name": ALGORITHM_NAMES.get(algorithm, f"Unknown({algorithm})"),
                "key_tag": dns.dnssec.key_id(dns.rdtypes.ANY.DNSKEY.DNSKEY(1, DNSKEY_QTYPE, key_flags, protocol, algorithm, key_data)) if DNS_AVAILABLE else None,
                "key_data": key_data.hex() if key_data else "",
            })

    result["success"] = True
    result["keys"] = keys
    return result


def _parse_ds_response(data: bytes, domain: str) -> dict[str, object]:
    """Parse DS response."""
    result: dict[str, object] = {
        "success": False,
        "records": [],
        "error": None,
    }
    if len(data) < 12:
        result["error"] = "response too short"
        return result

    struct.unpack(">H", data[0:2])[0]
    flags = struct.unpack(">H", data[2:4])[0]
    response_code = flags & 0x000F
    if response_code != 0:
        result["error"] = f"response code {response_code}"
        return result

    question_count = struct.unpack(">H", data[4:6])[0]
    answer_count = struct.unpack(">H", data[6:8])[0]

    offset = 12
    for _ in range(question_count):
        _, offset = _parse_dns_name(data, offset)
        offset += 4

    records = []
    for _ in range(answer_count):
        name, offset = _parse_dns_name(data, offset)
        if offset + 10 > len(data):
            break
        record_type = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        offset += 2  # class
        offset += 4  # ttl
        rdlength = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2

        if record_type == DS_QTYPE:
            if offset + 4 > len(data):
                break
            key_tag = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            algorithm = data[offset]
            offset += 1
            digest_type = data[offset]
            offset += 1
            digest = data[offset:offset + rdlength - 4] if rdlength >= 4 else b""
            offset += rdlength - 4

            records.append({
                "name": name,
                "key_tag": key_tag,
                "algorithm": algorithm,
                "algorithm_name": ALGORITHM_NAMES.get(algorithm, f"Unknown({algorithm})"),
                "digest_type": digest_type,
                "digest_type_name": DIGEST_TYPE_NAMES.get(digest_type, f"Unknown({digest_type})"),
                "digest": digest.hex() if digest else "",
            })

    result["success"] = True
    result["records"] = records
    return result


def _query_dnskey_dnspython(
    domain: str,
    server: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Query DNSKEY records using dnspython."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if server:
            resolver.nameservers = [server]
        request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
        server_addr = resolver.nameservers[0]
        if hasattr(server_addr, "address"):
            server_addr = getattr(server_addr, "address")
        if not isinstance(server_addr, str):
            server_addr = str(server_addr)
        response = dns.query.udp(request, server_addr, timeout=timeout)
        keys = []
        for answer in response.answer:
            for rdata in answer:
                if rdata.rdtype == dns.rdatatype.DNSKEY:
                    keys.append({
                        "name": str(answer.name),
                        "flags": rdata.flags,
                        "protocol": rdata.protocol,
                        "algorithm": rdata.algorithm,
                        "algorithm_name": ALGORITHM_NAMES.get(rdata.algorithm, f"Unknown({rdata.algorithm})"),
                        "key_tag": dns.dnssec.key_id(rdata),
                        "key_data": str(rdata).split()[-1] if str(rdata) else "",
                    })
        return {"success": True, "keys": keys, "error": None}
    # A transport failure of an unnamed type must not escape the command: a
    # hostile resolver/server can raise any type, and it is a failed probe, not
    # a crash.
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        return {"success": False, "keys": [], "error": str(exc)}


def _query_ds_dnspython(
    domain: str,
    server: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Query DS records using dnspython."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if server:
            resolver.nameservers = [server]
        request = dns.message.make_query(domain, dns.rdatatype.DS, want_dnssec=True)
        server_addr = resolver.nameservers[0]
        if hasattr(server_addr, "address"):
            server_addr = getattr(server_addr, "address")
        if not isinstance(server_addr, str):
            server_addr = str(server_addr)
        response = dns.query.udp(request, server_addr, timeout=timeout)
        records = []
        for answer in response.answer:
            for rdata in answer:
                if rdata.rdtype == dns.rdatatype.DS:
                    records.append({
                        "name": str(answer.name),
                        "key_tag": rdata.key_tag,
                        "algorithm": rdata.algorithm,
                        "algorithm_name": ALGORITHM_NAMES.get(rdata.algorithm, f"Unknown({rdata.algorithm})"),
                        "digest_type": rdata.digest_type,
                        "digest_type_name": DIGEST_TYPE_NAMES.get(rdata.digest_type, f"Unknown({rdata.digest_type})"),
                        "digest": rdata.digest.hex() if rdata.digest else "",
                    })
        return {"success": True, "records": records, "error": None}
    # A transport failure of an unnamed type must not escape the command: a
    # hostile resolver/server can raise any type, and it is a failed probe, not
    # a crash.
    except Exception as exc:  # noqa: BLE001 - transport can raise any type
        return {"success": False, "records": [], "error": str(exc)}


def run_dnssec(
    target: str,
    server: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Validate DNSSEC for a target domain.

    Args:
        target: Bare domain or URL (e.g. example.com or https://example.com).
        server: Custom DNS resolver IP address (requires dnspython).
        timeout: Query timeout in seconds.

    Returns:
        Structured results with DNSSEC validation status, keys, and chain info.
    """
    domain = _normalize_domain(target)

    dnskey_result = {"success": False, "keys": [], "error": None}
    ds_result = {"success": False, "records": [], "error": None}
    chain: list[dict[str, object]] = []
    notes: list[str] = []

    try:
        if DNS_AVAILABLE:
            dnskey_result = _query_dnskey_dnspython(domain, server, timeout)
            parent = _get_parent_zone(domain)
            if parent != ".":
                ds_result = _query_ds_dnspython(parent.rstrip("."), server, timeout)
        else:
            nameservers = _resolve_nameservers(domain, timeout)
            if nameservers:
                dnskey_result = _query_dnskey_raw(nameservers[0], domain, timeout)
                parent = _get_parent_zone(domain)
                if parent != ".":
                    parent_ns = _resolve_nameservers(parent.rstrip("."), timeout)
                    if parent_ns:
                        ds_result = _query_ds_raw(parent_ns[0], parent.rstrip("."), timeout)
            else:
                dnskey_result["error"] = "no nameservers found"
                ds_result["error"] = "no nameservers found"
    # A hostile server must never crash the command: whatever it sends is
    # reported through the module's own failure field.
    except Exception as exc:  # noqa: BLE001 - a remote answer must not raise
        dnskey_result = {
            "success": False,
            "keys": [],
            "error": f"dnssec probe failed: {exc}",
        }
        ds_result = {
            "success": False,
            "records": [],
            "error": f"dnssec probe failed: {exc}",
        }

    chain.append({
        "zone": domain,
        "dnskey": dnskey_result,
    })

    if ds_result.get("success") and ds_result.get("records"):
        chain.append({
            "zone": _get_parent_zone(domain).rstrip("."),
            "ds": ds_result,
        })

    validated = dnskey_result.get("success", False) and bool(dnskey_result.get("keys"))
    if ds_result.get("success") and ds_result.get("records"):
        validated = True

    if not DNS_AVAILABLE:
        notes.append("dnspython not installed; using stdlib-only validation (limited)")

    if not dnskey_result.get("success"):
        notes.append(f"DNSKEY query failed: {dnskey_result.get('error')}")
    elif not dnskey_result.get("keys"):
        notes.append("No DNSKEY records found (unsigned zone)")

    if not ds_result.get("success"):
        error = ds_result.get("error")
        if error:
            notes.append(f"DS query failed: {error}")
    elif not ds_result.get("records"):
        notes.append("No DS records found at parent (zone may be unsigned or parent not DNSSEC-signed)")

    return {
        "target": target,
        "domain": domain,
        "validated": validated,
        "dnskey": dnskey_result,
        "ds": ds_result,
        "chain": chain,
        "notes": notes,
        "dnspython_available": DNS_AVAILABLE,
    }


def format_dnssec_report_json(data: dict[str, object]) -> str:
    """Format DNSSEC results as JSON."""
    import json
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_dnssec_report_markdown(data: dict[str, object]) -> str:
    """Format DNSSEC results as Markdown."""
    lines = ["# ethscan DNSSEC Validation Report", ""]
    lines.append(f"- **Target:** {data.get('target')}")
    lines.append(f"- **Domain:** {data.get('domain')}")
    lines.append(f"- **Validated:** {'Yes' if data.get('validated') else 'No'}")
    lines.append(f"- **dnspython Available:** {'Yes' if data.get('dnspython_available') else 'No (stdlib only)'}")
    lines.append("")

    dnskey = data.get("dnskey")
    lines.append("## DNSKEY Records")
    if isinstance(dnskey, dict) and dnskey.get("success") and dnskey.get("keys"):
        lines.append("| Name | Flags | Protocol | Algorithm | Key Tag |")
        lines.append("|------|-------|----------|-----------|---------|")
        keys_list = dnskey.get("keys") or []
        if isinstance(keys_list, list):
            for key in keys_list:
                if not isinstance(key, dict):
                    continue
                lines.append(
                    f"| {_markdown_escape(key.get('name'))} | "
                    f"{key.get('flags')} | "
                    f"{key.get('protocol')} | "
                    f"{_markdown_escape(key.get('algorithm_name'))} | "
                    f"{key.get('key_tag', 'N/A')} |"
                )
    elif isinstance(dnskey, dict) and dnskey.get("success"):
        lines.append("*No DNSKEY records found (unsigned zone)*")
    elif isinstance(dnskey, dict):
        lines.append(f"*Query failed: {dnskey.get('error', 'unknown error')}*")
    else:
        lines.append("*Query failed: unknown error*")
    lines.append("")

    ds = data.get("ds")
    lines.append("## DS Records (Parent Zone)")
    if isinstance(ds, dict) and ds.get("success") and ds.get("records"):
        lines.append("| Name | Key Tag | Algorithm | Digest Type | Digest |")
        lines.append("|------|---------|-----------|-------------|--------|")
        recs_list = ds.get("records") or []
        if isinstance(recs_list, list):
            for record in recs_list:
                if not isinstance(record, dict):
                    continue
                lines.append(
                    f"| {_markdown_escape(record.get('name'))} | "
                    f"{record.get('key_tag')} | "
                    f"{_markdown_escape(record.get('algorithm_name'))} | "
                    f"{_markdown_escape(record.get('digest_type_name'))} | "
                    f"{_markdown_escape(record.get('digest'))} |"
                )
    elif isinstance(ds, dict) and ds.get("success"):
        lines.append("*No DS records found at parent zone*")
    elif isinstance(ds, dict):
        error = ds.get("error")
        if error:
            lines.append(f"*Query failed: {error}*")
        else:
            lines.append("*Query failed: unknown error*")
    else:
        lines.append("*Query failed: unknown error*")
    lines.append("")

    if data.get("chain"):
        lines.append("## Chain of Trust")
        chain = data.get("chain") or []
        if isinstance(chain, list):
            for i, link in enumerate(chain):
                if not isinstance(link, dict):
                    continue
                lines.append(f"### Level {i + 1}: {link.get('zone')}")
                if "dnskey" in link:
                    dk = link["dnskey"]
                    if isinstance(dk, dict):
                        if dk.get("success") and dk.get("keys"):
                            keys_list = dk.get("keys") or []
                            if isinstance(keys_list, list):
                                lines.append(f"- **DNSKEYs:** {len(keys_list)} key(s) found")
                            else:
                                lines.append("- **DNSKEYs:** key(s) found")
                        elif dk.get("success"):
                            lines.append("- **DNSKEYs:** None (unsigned)")
                        else:
                            lines.append(f"- **DNSKEY Error:** {dk.get('error')}")
                if "ds" in link:
                    ds_rec = link["ds"]
                    if isinstance(ds_rec, dict):
                        if ds_rec.get("success") and ds_rec.get("records"):
                            recs = ds_rec.get("records") or []
                            if isinstance(recs, list):
                                lines.append(f"- **DS Records:** {len(recs)} record(s) found")
                            else:
                                lines.append("- **DS Records:** record(s) found")
                        elif ds_rec.get("success"):
                            lines.append("- **DS Records:** None")
                        else:
                            lines.append(f"- **DS Error:** {ds_rec.get('error')}")
                lines.append("")

    if data.get("notes"):
        lines.append("## Notes")
        notes = data.get("notes") or []
        if isinstance(notes, list):
            for note in notes:
                if isinstance(note, str):
                    lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def _dnssec_csv_header() -> list[str]:
    """Return the CSV header row for dnssec output."""
    return [
        "target",
        "domain",
        "validated",
        "record_type",
        "name",
        "flags",
        "protocol",
        "algorithm",
        "key_tag",
        "digest_type",
        "digest",
        "count",
        "success",
        "error",
    ]


def _dnssec_row(
    target: str,
    domain: str,
    validated: bool,
    record_type: str,
    name: str = "",
    flags: str = "",
    protocol: str = "",
    algorithm: str = "",
    key_tag: str = "",
    digest_type: str = "",
    digest: str = "",
    count: str = "",
    success: str = "",
    error: str = "",
) -> list[str]:
    """Build a single CSV row for a DNSSEC record (key, DS record, or status)."""
    return [
        target,
        domain,
        "true" if validated else "false",
        record_type,
        name,
        flags,
        protocol,
        algorithm,
        key_tag,
        digest_type,
        digest,
        count,
        success,
        error,
    ]


def _dnssec_status_row(
    target: str,
    domain: str,
    validated: bool,
    record_type: str,
    name: str,
    result: dict[str, object],
    item_key: str,
) -> list[str]:
    """Build a CSV status row summarizing a DNSKEY/DS query."""
    items = result.get(item_key) or []
    count_str = "0"
    if isinstance(items, list):
        count_str = str(len(items))
    elif isinstance(items, (int, float)):
        count_str = str(items)
    return _dnssec_row(
        target,
        domain,
        validated,
        record_type,
        name=name,
        count=count_str,
        success="true" if result.get("success") else "false",
        error=str(result.get("error") or ""),
    )


def format_dnssec_report_csv(data: dict[str, object]) -> str:
    """Format DNSSEC results as CSV.

    Emits a header row followed by one row per DNSKEY record, one row per DS
    record, and one row per chain-of-trust delegation level, using stdlib
    ``csv.writer`` for proper quoting/escaping of values containing commas or
    double-quotes. ``record_type`` discriminates the row kind (``dnskey``,
    ``ds``, ``chain``); non-applicable fields are left empty.

    A failed or record-less DNSKEY/DS query still emits a single status row
    (carrying ``count``, ``success`` and ``error``) so diagnostic information is
    not silently dropped, mirroring the Markdown formatter's status lines.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_dnssec_csv_header())

    target = data.get("target") or ""
    domain = data.get("domain") or ""
    validated = bool(data.get("validated"))
    target_s = str(target)
    domain_s = str(domain)
    validated_b = bool(validated)

    # DNSKEY records (mirrors the Markdown "DNSKEY Records" table)
    dnskey = data.get("dnskey") or {}
    if isinstance(dnskey, dict):
        keys = dnskey.get("keys") or []
        if isinstance(keys, list) and keys:
            for key in keys:
                if not isinstance(key, dict):
                    continue
                writer.writerow(_dnssec_row(
                    target_s,
                    domain_s,
                    validated_b,
                    "dnskey",
                    name=str(key.get("name", "")),
                    flags=str(key.get("flags", "")),
                    protocol=str(key.get("protocol", "")),
                    algorithm=str(key.get("algorithm_name") or key.get("algorithm", "")),
                    key_tag=str(key.get("key_tag", "")),
                ))
        else:
            writer.writerow(_dnssec_status_row(
                target_s, domain_s, validated_b, "dnskey", "", dnskey, "keys"
            ))
    else:
        writer.writerow(_dnssec_status_row(
            target_s, domain_s, validated_b, "dnskey", "", {}, "keys"
        ))

    # DS records (mirrors the Markdown "DS Records (Parent Zone)" table)
    ds = data.get("ds") or {}
    if isinstance(ds, dict):
        records = ds.get("records") or []
        if isinstance(records, list) and records:
            for record in records:
                if not isinstance(record, dict):
                    continue
                writer.writerow(_dnssec_row(
                    target_s,
                    domain_s,
                    validated_b,
                    "ds",
                    name=str(record.get("name", "")),
                    algorithm=str(record.get("algorithm_name") or record.get("algorithm", "")),
                    key_tag=str(record.get("key_tag", "")),
                    digest_type=str(record.get("digest_type_name") or record.get("digest_type", "")),
                    digest=str(record.get("digest", "")),
                ))
        else:
            writer.writerow(_dnssec_status_row(
                target_s, domain_s, validated_b, "ds", "", ds, "records"
            ))
    else:
        writer.writerow(_dnssec_status_row(
            target_s, domain_s, validated_b, "ds", "", {}, "records"
        ))

    # Chain of trust (mirrors the Markdown "Chain of Trust" section)
    chain = data.get("chain") or []
    if isinstance(chain, list):
        for link in chain:
            if not isinstance(link, dict):
                continue
            zone = str(link.get("zone", ""))
            for sub_key, item_key in (("dnskey", "keys"), ("ds", "records")):
                sub = link.get(sub_key)
                if not isinstance(sub, dict):
                    continue
                writer.writerow(_dnssec_status_row(
                    target_s, domain_s, validated_b, "chain", zone, sub, item_key
                ))

    return output.getvalue().rstrip("\r\n")