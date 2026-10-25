"""Nmap XML parser module for ethscan.

Parses Nmap XML scan output and cross-references detected service versions
against the built-in vulnerability database.
"""
from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET

from ethscan.fileio import read_text
from ethscan.vuln import (
    SEVERITIES,
    match_service_vulns,
    parse_banner,
)


class NmapParseError(ValueError):
    """Raised when the Nmap XML file cannot be parsed."""


def _extract_text(element: ET.Element | None, default: str = "") -> str:
    """Safely extract text from an XML element."""
    if element is not None and element.text:
        return element.text.strip()
    return default


def _parse_port(port_elem: ET.Element) -> dict[str, object] | None:
    """Parse a single port element from Nmap XML.

    Returns:
        The parsed port, or None when the element does not hold a usable port
        number (a port id that is not a number, or a number outside the range
        of a TCP/UDP port).
    """
    try:
        port_id = int(port_elem.get("portid", 0))
    except (TypeError, ValueError):
        return None
    if not 1 <= port_id <= 65535:
        return None
    protocol = port_elem.get("protocol", "tcp")

    state_elem = port_elem.find("state")
    state = state_elem.get("state", "unknown") if state_elem is not None else "unknown"
    reason = state_elem.get("reason", "") if state_elem is not None else ""

    service_elem = port_elem.find("service")
    service_name = ""
    product = ""
    version = ""
    extrainfo = ""
    ostype = ""
    method = ""
    conf = ""
    banner_parts = []

    if service_elem is not None:
        service_name = service_elem.get("name", "")
        product = service_elem.get("product", "")
        version = service_elem.get("version", "")
        extrainfo = service_elem.get("extrainfo", "")
        ostype = service_elem.get("ostype", "")
        method = service_elem.get("method", "")
        conf = service_elem.get("conf", "")

        # Build a banner-like string for signature matching
        if product:
            banner_parts.append(product)
        if version:
            banner_parts.append(version)
        if extrainfo:
            banner_parts.append(extrainfo)
        if ostype:
            banner_parts.append(ostype)

    banner = " ".join(banner_parts).strip()

    return {
        "port": port_id,
        "protocol": protocol,
        "state": state,
        "reason": reason,
        "service_name": service_name,
        "product": product,
        "version": version,
        "extrainfo": extrainfo,
        "ostype": ostype,
        "method": method,
        "conf": conf,
        "banner": banner,
    }


def _parse_host(host_elem: ET.Element) -> dict[str, object]:
    """Parse a single host element from Nmap XML."""
    address_elem = host_elem.find("address")
    addr = address_elem.get("addr", "") if address_elem is not None else ""
    addr_type = address_elem.get("addrtype", "ipv4") if address_elem is not None else "ipv4"

    hostnames: list[str] = []
    hostnames_elem = host_elem.find("hostnames")
    if hostnames_elem is not None:
        for hn_elem in hostnames_elem.findall("hostname"):
            name = hn_elem.get("name", "")
            if name:
                hostnames.append(name)

    status_elem = host_elem.find("status")
    status = status_elem.get("state", "unknown") if status_elem is not None else "unknown"

    ports: list[dict[str, object]] = []
    ports_elem = host_elem.find("ports")
    if ports_elem is not None:
        for port_elem in ports_elem.findall("port"):
            port = _parse_port(port_elem)
            if port is not None:
                ports.append(port)

    return {
        "address": addr,
        "address_type": addr_type,
        "hostnames": hostnames,
        "status": status,
        "ports": ports,
    }


def parse_nmap_xml(xml_content: str) -> list[dict[str, object]]:
    """Parse Nmap XML content and return a list of host results.

    Args:
        xml_content: Raw XML string from Nmap output (-oX).

    Returns:
        List of host dictionaries with parsed port/service information.

    Raises:
        NmapParseError: If the content is not valid XML.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise NmapParseError(f"invalid Nmap XML: {exc}") from exc

    hosts: list[dict[str, object]] = []
    for host_elem in root.findall("host"):
        hosts.append(_parse_host(host_elem))

    return hosts


def run_nmap(
    input_file: str,
) -> dict[str, object]:
    """Parse an Nmap XML file and cross-reference findings with the vulnerability database.

    Args:
        input_file: Path to Nmap XML output file (-oX).

    Returns:
        Structured results with parsed services and matched vulnerabilities.

    Raises:
        NmapParseError: If the file does not hold valid Nmap XML.
    """
    xml_content = read_text(input_file)

    hosts = parse_nmap_xml(xml_content)

    all_findings: list[dict[str, object]] = []
    all_services: list[dict[str, object]] = []
    total_ports_scanned = 0
    total_open_ports = 0

    for host in hosts:  # type: ignore
        host_dict = host  # type: ignore
        host_addr = host_dict["address"]
        hostnames = host_dict.get("hostnames", []) or []
        ports = host_dict.get("ports", []) or []

        for port_info in ports:  # type: ignore
            port_dict = port_info  # type: ignore
            total_ports_scanned += 1
            if port_dict["state"] != "open":
                continue

            total_open_ports += 1

            service_entry = {
                "host": host_addr,
                "hostnames": hostnames,
                "port": port_dict["port"],
                "protocol": port_dict["protocol"],
                "service_name": port_dict.get("service_name"),
                "product": port_dict.get("product"),
                "version": port_dict.get("version"),
                "extrainfo": port_dict.get("extrainfo"),
                "ostype": port_dict.get("ostype"),
                "banner": port_dict.get("banner"),
            }
            all_services.append(service_entry)

            # Try to match against vulnerability database using product/version
            product = port_dict.get("product")
            version = port_dict.get("version")
            port_num = port_dict.get("port")

            # First try: use product and version directly
            findings = match_service_vulns(product or "", version or "", port=port_num)  # type: ignore

            # Second try: if no findings, try parsing the banner for product/version
            if not findings and port_dict.get("banner"):
                parsed_product, parsed_version = parse_banner(port_dict.get("banner") or "")
                findings = match_service_vulns(parsed_product, parsed_version, port=port_num)  # type: ignore

            # Add host context to findings
            for finding in findings:  # type: ignore
                finding["host"] = host_addr  # type: ignore
                finding["service_name"] = port_dict.get("service_name")  # type: ignore
                finding["state"] = port_dict.get("state")  # type: ignore
                if hostnames:
                    finding["hostnames"] = hostnames  # type: ignore

            all_findings.extend(findings)  # type: ignore

    # Count by severity
    severity_counts: dict[str, int] = {name: 0 for name in SEVERITIES}
    for finding in all_findings:  # type: ignore
        level = str((finding or {}).get("severity", "")).lower()
        if level in severity_counts:
            severity_counts[level] += 1

    # Build summary
    notes = []
    if total_open_ports == 0:
        notes.append("No open ports found in scan")
    if not all_findings:
        notes.append("No known vulnerabilities matched")

    return {
        "input_file": input_file,
        "hosts_scanned": len(hosts),  # type: ignore
        "total_ports_scanned": total_ports_scanned,
        "total_open_ports": total_open_ports,
        "services_detected": len(all_services),
        "finding_count": len(all_findings),
        "severity_counts": severity_counts,
        "services": all_services,
        "findings": all_findings,
        "notes": notes,
    }


def format_nmap_report_json(data: dict[str, object]) -> str:
    """Format Nmap parser results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _escape(value: str) -> str:
    """Escape pipe characters for Markdown output."""
    return value.replace("|", "\\|")


def _finding_detail(finding: dict[str, object]) -> str:
    """Render the per-finding details line for Markdown output."""
    kind = str(finding.get("kind", ""))
    if kind == "service":
        product = str(finding.get("product") or "Unknown")
        version = str(finding.get("version") or "")
        detail = f"{product} {version}".strip()
        port = finding.get("port")
        if port is not None:
            detail = f"{detail} (port {port})"
        host = finding.get("host")
        if host:
            detail = f"{detail} [{host}]"
        return detail
    if kind == "protocol":
        return str(finding.get("protocol") or "")
    if kind == "cipher":
        return str(finding.get("cipher") or "")
    if kind == "certificate":
        key_size = finding.get("key_size")
        if key_size is not None:
            return f"key size {key_size} bits"
        signature = finding.get("signature_algorithm")
        if signature:
            return f"signature algorithm {signature}"
        return ""
    return ""


def format_nmap_report_markdown(data: dict[str, object]) -> str:
    """Format Nmap parser results as Markdown."""
    lines = ["# ethscan Nmap Vulnerability Report", ""]
    lines.append(f"- **Input File:** {data['input_file']}")
    lines.append(f"- **Hosts Scanned:** {data.get('hosts_scanned', 0)}")
    lines.append(f"- **Total Ports Scanned:** {data.get('total_ports_scanned', 0)}")
    lines.append(f"- **Open Ports:** {data.get('total_open_ports', 0)}")
    lines.append(f"- **Services Detected:** {data.get('services_detected', 0)}")
    lines.append(f"- **Findings:** {data.get('finding_count', 0)}")
    lines.append("")

    severity_counts = data.get("severity_counts") or {}
    lines.append("## Severity Summary")
    for name in SEVERITIES:
        lines.append(f"- **{name.capitalize()}:** {(severity_counts.get(name, 0) if isinstance(severity_counts, dict) else 0)}")
    lines.append("")

    services = data.get("services") or []
    if services:
        lines.append("## Detected Services")
        lines.append("| Host | Hostnames | Port | Protocol | Service | Product | Version |")
        lines.append("|------|-----------|------|----------|---------|---------|---------|")
        for svc in services:  # type: ignore
            svc_dict = svc  # type: ignore
            hostnames = ", ".join(svc_dict.get("hostnames") or [])  # type: ignore
            lines.append(
                f"| {_escape(svc_dict.get('host', ''))} | {_escape(hostnames)} | "
                f"{svc_dict.get('port', '')} | {_escape(svc_dict.get('protocol', ''))} | "
                f"{_escape(svc_dict.get('service_name', ''))} | "
                f"{_escape(svc_dict.get('product', ''))} | "
                f"{_escape(svc_dict.get('version', ''))} |"
            )
        lines.append("")

    findings = data.get("findings") or []
    lines.append("## Vulnerability Findings")
    if findings:
        for finding in findings:  # type: ignore
            finding_dict = finding  # type: ignore
            lines.append(
                f"### {finding_dict.get('id')} ({str(finding_dict.get('severity')).upper()})"
            )
            lines.append(f"- **Type:** {finding_dict.get('kind')}")
            detail = _escape(_finding_detail(finding_dict))  # type: ignore
            if detail:
                lines.append(f"- **Details:** {detail}")
            lines.append(f"- **Title:** {_escape(str(finding_dict.get('title')))}")
            lines.append(
                f"- **Description:** {_escape(str(finding_dict.get('description')))}"
            )
            lines.append("")
    else:
        lines.append("*No known vulnerabilities matched.*")
        lines.append("")

    notes = data.get("notes") or []
    if notes:
        lines.append("## Notes")
        for note in notes:  # type: ignore
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def format_nmap_report_csv(data: dict[str, object]) -> str:
    """Format Nmap parser results as CSV.

    Produces a header row followed by one row per matched CVE finding with
    columns: host, addr, port, state, service, product, version, cve_id,
    severity, score, title.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "host",
            "addr",
            "port",
            "state",
            "service",
            "product",
            "version",
            "cve_id",
            "severity",
            "score",
            "title",
        ]
    )
    for finding in data.get("findings") or []:  # type: ignore
        finding_dict = finding  # type: ignore
        hostnames = finding_dict.get("hostnames") or []  # type: ignore
        host = ", ".join(str(name) for name in hostnames)
        if not host:
            host = str(finding_dict.get("host") or "")
        addr = str(finding_dict.get("host") or "")
        port = finding_dict.get("port", "")
        state = str(finding_dict.get("state", "open") or "open")
        service = str(finding_dict.get("service_name") or finding_dict.get("service") or "")
        product = str(finding_dict.get("product") or "")
        version = str(finding_dict.get("version") or "")
        cve_id = str(finding_dict.get("id") or "")
        severity = str(finding_dict.get("severity") or "")
        score = finding_dict.get("score", "")
        title = str(finding_dict.get("title") or "")
        writer.writerow(
            [
                host,
                addr,
                port,
                state,
                service,
                product,
                version,
                cve_id,
                severity,
                score,
                title,
            ]
        )
    return output.getvalue().rstrip("\r\n")
