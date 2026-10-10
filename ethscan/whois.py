"""WHOIS lookup module for ethscan."""

import re
import socket
from typing import Dict, List, Optional


DEFAULT_WHOIS_SERVER = "whois.iana.org"
DEFAULT_TIMEOUT = 5.0


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


def parse_whois(raw: str) -> Dict[str, object]:
    """Parse key fields from a raw WHOIS response.

    Args:
        raw: Raw WHOIS response text.

    Returns:
        Dictionary with parsed fields: registrar, creation_date, expiration_date,
        nameservers, registrant_org, status_codes, raw.
    """
    result: Dict[str, object] = {
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
        result["nameservers"] = sorted(set(ns.strip().rstrip(".") for ns in nameserver_matches))

    status_matches = re.findall(
        r"Status:\s*(\S+)", raw, re.IGNORECASE
    )
    if status_matches:
        result["status_codes"] = sorted(set(status.strip() for status in status_matches))

    return result


def run_whois(
    target: str,
    server: str = DEFAULT_WHOIS_SERVER,
    port: int = 43,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, object]:
    """Perform a WHOIS lookup and return parsed results.

    Args:
        target: Domain name or IP address to query.
        server: WHOIS server hostname (default: whois.iana.org).
        port: WHOIS server port (default: 43).
        timeout: Connection timeout in seconds.

    Returns:
        Structured results with target, server, raw response, and parsed fields.
    """
    raw = query_whois(target, server=server, port=port, timeout=timeout)
    parsed = parse_whois(raw)

    return {
        "target": target,
        "server": server,
        "port": port,
        "raw": raw,
        "parsed": parsed,
    }


def format_whois_report_json(data: Dict[str, object]) -> str:
    """Format WHOIS results as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_whois_report_markdown(data: Dict[str, object]) -> str:
    """Format WHOIS results as Markdown."""
    parsed = data["parsed"]
    lines = ["# ethscan WHOIS Lookup Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Server:** {data['server']}:{data['port']}")
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

    return "\n".join(lines)