"""WHOIS lookup module for ethscan."""
from __future__ import annotations

import csv
import io
import re
import socket

from ethscan.target import parse_url

DEFAULT_WHOIS_SERVER = "whois.iana.org"
DEFAULT_TIMEOUT = 5.0
DEFAULT_RECURSIVE_DEPTH = 2


def _normalize_target(target: str) -> str:
    """Extract a bare hostname or IP from a target that may be a URL."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "http://" + normalized
    parsed = parse_url(normalized)
    host = (parsed.hostname or parsed.netloc or "").lower()
    return host


def query_whois(
    target: str,
    server: str = DEFAULT_WHOIS_SERVER,
    port: int = 43,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Query a WHOIS server for a target domain or IP.

    Args:
        target: Domain name or IP address to query.
        server: WHOIS server hostname (default: whois.iana.org).
        port: WHOIS server port (default: 43).
        timeout: Connection timeout in seconds.

    Returns:
        Raw WHOIS response as a string.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((server, port))
        request = f"{target}\r\n"
        sock.sendall(request.encode("utf-8"))

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        return response.decode("utf-8", errors="replace")
    finally:
        sock.close()


def parse_whois(raw: str) -> dict[str, object]:
    """Parse key fields from a raw WHOIS response.

    Args:
        raw: Raw WHOIS response text.

    Returns:
        Dictionary with parsed fields: registrar, creation_date, expiration_date,
        nameservers, registrant_org, status_codes, raw.
    """
    result: dict[str, object] = {
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "nameservers": [],
        "registrant_org": None,
        "status_codes": [],
        "raw": raw,
    }

    patterns = {
        "registrar": [
            r"Registrar:\s*(.+)",
            r"Registrar Name:\s*(.+)",
            r"Sponsoring Registrar:\s*(.+)",
        ],
        "creation_date": [
            r"Creation Date:\s*(.+)",
            r"Created:\s*(.+)",
            r"Registration Date:\s*(.+)",
            r"Domain Registration Date:\s*(.+)",
        ],
        "expiration_date": [
            r"Expiration Date:\s*(.+)",
            r"Expiry Date:\s*(.+)",
            r"Registry Expiry Date:\s*(.+)",
        ],
        "registrant_org": [
            r"Registrant Organization:\s*(.+)",
            r"Registrant Org:\s*(.+)",
            r"Organization:\s*(.+)",
        ],
    }

    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, raw, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
                break

    nameserver_matches = re.findall(
        r"Name Server:\s*(\S+)", raw, re.IGNORECASE
    )
    if nameserver_matches:
        result["nameservers"] = sorted({ns.strip().rstrip(".") for ns in nameserver_matches})

    status_matches = re.findall(
        r"Status:\s*(\S+)", raw, re.IGNORECASE
    )
    if status_matches:
        result["status_codes"] = sorted({status.strip() for status in status_matches})

    return result


def extract_referral_server(raw: str) -> str | None:
    """Extract a referral WHOIS server hostname from a raw WHOIS response.

    WHOIS responses often include a line pointing to the registrar's WHOIS
    server, e.g. ``Registrar WHOIS Server: whois.example.com`` or
    ``Refer: whois.example.com``. Returns the first match, lowercased and
    stripped of trailing dots, or None when no referral is present.

    Args:
        raw: Raw WHOIS response text.

    Returns:
        Referral server hostname, or None.
    """
    patterns = [
        r"Registrar WHOIS Server:\s*(\S+)",
        r"WHOIS Server:\s*(\S+)",
        r"Referral Server:\s*(\S+)",
        r"Refer:\s*(\S+)",
        r"Registrar URL:\s*whois://(\S+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            server = match.group(1).strip().rstrip(".")
            if server and server.lower() != "whois.iana.org":
                return server.lower()
    return None


def run_whois(
    target: str,
    server: str = DEFAULT_WHOIS_SERVER,
    port: int = 43,
    timeout: float = DEFAULT_TIMEOUT,
    recursive: bool = False,
    max_depth: int = DEFAULT_RECURSIVE_DEPTH,
) -> dict[str, object]:
    """Perform a WHOIS lookup and return parsed results.

    Args:
        target: Domain name or IP address to query.
        server: WHOIS server hostname (default: whois.iana.org).
        port: WHOIS server port (default: 43).
        timeout: Connection timeout in seconds.
        recursive: Enable recursive WHOIS queries: follow referral servers
            extracted from each response (e.g. from whois.iana.org to the
            registrar's WHOIS server) up to ``max_depth`` hops.
        max_depth: Maximum number of recursive hops when ``recursive`` is
            True (default: 2).

    Returns:
        Structured results with target, server, raw response, parsed fields,
        and (when recursive) per-hop results in ``recursive_hops``.

        A WHOIS server that cannot be reached is reported as a failed lookup
        (``error`` is set, ``raw`` is empty) instead of a traceback.
    """
    try:
        raw = query_whois(target, server=server, port=port, timeout=timeout)
    except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError, RuntimeError) as exc:
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": parse_whois(""),
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
            "error": f"Connection failed: {exc}",
        }
    parsed = parse_whois(raw)

    result: dict[str, object] = {
        "target": target,
        "server": server,
        "port": port,
        "raw": raw,
        "parsed": parsed,
        "recursive": recursive,
        "max_depth": max_depth,
        "recursive_hops": [],
    }

    if not recursive:
        return result

    hops: list[dict[str, object]] = []
    seen_raw: list[str] = [raw]
    current_server = server
    current_port = port

    for depth in range(1, max_depth + 1):
        referral = extract_referral_server(raw)
        if not referral:
            break
        if referral == current_server:
            break

        try:
            hop_raw = query_whois(
                target, server=referral, port=current_port, timeout=timeout
            )
        except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError, RuntimeError):
            hops.append(
                {
                    "depth": depth,
                    "server": referral,
                    "port": current_port,
                    "raw": "",
                    "parsed": parse_whois(""),
                    "error": "Connection failed",
                    "referral_server": None,
                }
            )
            break

        hop_parsed = parse_whois(hop_raw)
        hop_entry: dict[str, object] = {
            "depth": depth,
            "server": referral,
            "port": current_port,
            "raw": hop_raw,
            "parsed": hop_parsed,
            "referral_server": extract_referral_server(hop_raw),
        }
        hops.append(hop_entry)

        # Stop when the response repeats (loop protection) or no further referral.
        if hop_raw in seen_raw:
            break
        seen_raw.append(hop_raw)
        if not hop_entry["referral_server"]:
            break
        # Update raw so the next iteration extracts the referral from the
        # most recent hop's response.
        raw = hop_raw
        current_server = referral

    result["recursive_hops"] = hops
    return result


def format_whois_report_json(data: dict[str, object]) -> str:
    """Format WHOIS results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_whois_report_markdown(data: dict[str, object]) -> str:
    """Format WHOIS results as Markdown."""
    parsed = data["parsed"]
    lines = ["# ethscan WHOIS Lookup Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Server:** {data['server']}:{data['port']}")
    if data.get("error"):
        lines.append(f"- **Error:** {data['error']}")
    lines.append("")

    lines.append("## Parsed Fields")
    lines.append(f"- **Registrar:** {parsed['registrar'] or 'N/A'}")
    lines.append(f"- **Creation Date:** {parsed['creation_date'] or 'N/A'}")
    lines.append(f"- **Expiration Date:** {parsed['expiration_date'] or 'N/A'}")
    lines.append(f"- **Registrant Organization:** {parsed['registrant_org'] or 'N/A'}")
    lines.append("")

    if parsed["nameservers"]:
        lines.append("## Nameservers")
        for ns in parsed["nameservers"]:
            lines.append(f"- {ns}")
        lines.append("")

    if parsed["status_codes"]:
        lines.append("## Status Codes")
        for status in parsed["status_codes"]:
            lines.append(f"- {status}")
        lines.append("")

    lines.append("## Raw Response")
    lines.append("```")
    lines.append(data["raw"].strip())
    lines.append("```")

    recursive_hops = data.get("recursive_hops") or []
    if data.get("recursive") and recursive_hops:
        lines.append("")
        lines.append("## Recursive WHOIS Queries")
        for hop in recursive_hops:
            depth = hop.get("depth", 0)
            server = hop.get("server", "N/A")
            port = hop.get("port", 43)
            hop_parsed = hop.get("parsed") or {}
            error = hop.get("error")
            if error:
                lines.append(f"- **Depth {depth}:** {server}:{port} - {error}")
                continue
            lines.append(f"- **Depth {depth}:** {server}:{port}")
            if hop_parsed.get("registrar"):
                lines.append(f"  - Registrar: {hop_parsed['registrar']}")
            if hop_parsed.get("creation_date"):
                lines.append(f"  - Creation Date: {hop_parsed['creation_date']}")
            if hop_parsed.get("expiration_date"):
                lines.append(f"  - Expiration Date: {hop_parsed['expiration_date']}")
            if hop_parsed.get("registrant_org"):
                lines.append(f"  - Registrant Org: {hop_parsed['registrant_org']}")
            referral = hop.get("referral_server")
            if referral:
                lines.append(f"  - Referral Server: {referral}")
        lines.append("")
    elif data.get("recursive") and not recursive_hops:
        lines.append("")
        lines.append("## Recursive WHOIS Queries")
        lines.append("*No referral servers found; no additional hops performed.*")
        lines.append("")

    return "\n".join(lines)


def format_whois_report_csv(data: dict[str, object]) -> str:
    """Format WHOIS results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    parsed = data.get("parsed", {})
    writer.writerow(["field", "value"])
    writer.writerow(["target", data.get("target", "")])
    writer.writerow(["server", data.get("server", "")])
    writer.writerow(["port", data.get("port", "")])
    writer.writerow(["registrar", parsed.get("registrar") or ""])
    writer.writerow(["creation_date", parsed.get("creation_date") or ""])
    writer.writerow(["expiration_date", parsed.get("expiration_date") or ""])
    writer.writerow(["registrant_org", parsed.get("registrant_org") or ""])
    writer.writerow(["nameservers", ";".join(parsed.get("nameservers") or [])])
    writer.writerow(["status_codes", ";".join(parsed.get("status_codes") or [])])
    if data.get("error"):
        writer.writerow(["error", data["error"]])

    recursive_hops = data.get("recursive_hops") or []
    if recursive_hops:
        writer.writerow([])
        writer.writerow(["recursive_hop_depth", "server", "port", "registrar", "creation_date", "expiration_date", "registrant_org", "referral_server", "error"])
        for hop in recursive_hops:
            hop_parsed = hop.get("parsed") or {}
            writer.writerow([
                hop.get("depth", ""),
                hop.get("server", ""),
                hop.get("port", ""),
                hop_parsed.get("registrar") or "",
                hop_parsed.get("creation_date") or "",
                hop_parsed.get("expiration_date") or "",
                hop_parsed.get("registrant_org") or "",
                hop.get("referral_server") or "",
                hop.get("error") or "",
            ])
    return output.getvalue().rstrip("\r\n")