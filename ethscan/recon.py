"""Reconnaissance module for ethscan.

Runs multiple reconnaissance modules (subdomains, dns, whois, geo, trace)
in sequence and produces a consolidated report.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Mapping, cast

from ethscan.dns import run_dns
from ethscan.geo import run_geo
from ethscan.subdomains import run_subdomains
from ethscan.target import parse_url
from ethscan.trace import run_trace
from ethscan.whois import run_whois

DEFAULT_RECON_MODULES = ["subdomains", "dns", "whois", "geo", "trace"]


def _normalize_domain(target: str) -> str:
    """Extract a bare domain from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    parsed = parse_url(normalized)
    return parsed.netloc.lower()


def run_recon(
    target: str,
    modules: list[str] | None = None,
    subdomains_wordlist: list[str] | None = None,
    dns_record_types: list[str] | None = None,
    dns_server: str | None = None,
    whois_server: str = "whois.iana.org",
    whois_port: int = 43,
    geo_use_cache: bool = True,
    geo_offline_fallback: bool = True,
    geo_api_url: str | None = None,
    trace_port: int = 80,
    trace_max_hops: int = 30,
    trace_probes_per_hop: int = 3,
    timeout: float = 5.0,
    max_workers: int = 50,
    resolver: str | None = None,
) -> dict[str, object]:
    """Run multiple reconnaissance modules against a target.

    Args:
        target: Bare domain, IP, or URL (e.g. example.com or https://example.com).
        modules: List of modules to run. Defaults to all: subdomains, dns, whois, geo, trace.
        subdomains_wordlist: Custom subdomain wordlist for subdomain enumeration.
        dns_record_types: DNS record types to query (A, AAAA, MX, NS, TXT, CNAME, SOA).
        dns_server: Custom DNS resolver IP address (requires dnspython).
        whois_server: WHOIS server to query.
        whois_port: WHOIS server port.
        geo_use_cache: Whether to use local filesystem cache for geolocation.
        geo_offline_fallback: Whether to use stale cache when API is unavailable.
        geo_api_url: Optional custom geolocation API base URL.
        trace_port: Target TCP port for traceroute SYN probes.
        trace_max_hops: Maximum TTL / number of hops for traceroute.
        trace_probes_per_hop: Number of probes per hop for RTT averaging.
        timeout: Default timeout for network operations.
        max_workers: Maximum concurrent workers for subdomain enumeration.
        resolver: Custom DNS resolver IP address for subdomains (requires dnspython).

    Returns:
        Structured results with target, domain, and results from each module.
    """
    domain = _normalize_domain(target)
    enabled_modules = modules if modules is not None else DEFAULT_RECON_MODULES

    results: dict[str, object] = {
        "target": target,
        "domain": domain,
        "modules_run": [],
        "subdomains": None,
        "dns": None,
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }

    # Subdomains enumeration
    if "subdomains" in enabled_modules:
        cast(list, results["modules_run"]).append("subdomains")
        try:
            results["subdomains"] = run_subdomains(
                target,
                subdomains=subdomains_wordlist,
                timeout=timeout,
                max_workers=max_workers,
                resolver=resolver,
            )
        except Exception as exc:  # noqa: BLE001 - module failures are heterogeneous
            cast(list, results["notes"]).append(f"subdomains module failed: {exc}")

    # DNS record enumeration
    if "dns" in enabled_modules:
        cast(list, results["modules_run"]).append("dns")
        try:
            results["dns"] = run_dns(
                target,
                record_types=dns_record_types,
                server=dns_server,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - module failures are heterogeneous
            cast(list, results["notes"]).append(f"dns module failed: {exc}")

    # WHOIS lookup
    if "whois" in enabled_modules:
        cast(list, results["modules_run"]).append("whois")
        try:
            results["whois"] = run_whois(
                target,
                server=whois_server,
                port=whois_port,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - module failures are heterogeneous
            cast(list, results["notes"]).append(f"whois module failed: {exc}")

    # Geolocation lookup
    if "geo" in enabled_modules:
        cast(list, results["modules_run"]).append("geo")
        try:
            results["geo"] = run_geo(
                target,
                timeout=timeout,
                use_cache=geo_use_cache,
                offline_fallback=geo_offline_fallback,
                api_url=geo_api_url,
            )
        except Exception as exc:  # noqa: BLE001 - module failures are heterogeneous
            cast(list, results["notes"]).append(f"geo module failed: {exc}")

    # TCP traceroute
    if "trace" in enabled_modules:
        cast(list, results["modules_run"]).append("trace")
        try:
            results["trace"] = run_trace(
                target,
                port=trace_port,
                max_hops=trace_max_hops,
                timeout=timeout,
                probes_per_hop=trace_probes_per_hop,
            )
        except Exception as exc:  # noqa: BLE001 - module failures are heterogeneous
            cast(list, results["notes"]).append(f"trace module failed: {exc}")

    return results


def format_recon_report_json(data: Mapping[str, object]) -> str:
    """Format recon results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return []


def format_recon_report_markdown(data: Mapping[str, object]) -> str:
    """Format recon results as Markdown."""
    data = _as_dict(data)
    lines = ["# ethscan Reconnaissance Report", ""]
    lines.append(f"- **Target:** {data.get('target', '')}")
    lines.append(f"- **Domain:** {data.get('domain', '')}")
    modules_run = _as_list(data.get("modules_run"))
    modules_run_str = ", ".join(str(m) for m in modules_run) if modules_run else "None"
    lines.append(f"- **Modules Run:** {modules_run_str}")
    lines.append("")

    # Subdomains section
    subdomains = data.get("subdomains")
    if isinstance(subdomains, dict):
        lines.append("## Subdomain Enumeration")
        lines.append(f"- **Subdomains Tested:** {subdomains.get('subdomains_tested', 0)}")
        lines.append(f"- **Resolved:** {subdomains.get('resolved_count', 0)}")
        resolver = subdomains.get("resolver")
        if resolver:
            lines.append(f"- **Resolver:** {resolver} (dnspython: {'Yes' if subdomains.get('dnspython_available') else 'No'})")
        lines.append("")

        resolved = _as_list(subdomains.get("resolved"))
        if resolved:
            lines.append("### Resolved Subdomains")
            lines.append("| Subdomain | Hostname | IP |")
            lines.append("|-----------|----------|----|")
            for entry_raw in resolved:
                entry = _as_dict(entry_raw)
                lines.append(
                    f"| {_markdown_escape(entry.get('subdomain', ''))} | "
                    f"{_markdown_escape(entry.get('hostname', ''))} | "
                    f"{_markdown_escape(entry.get('ip', ''))} |"
                )
            lines.append("")

    # DNS section
    dns = data.get("dns")
    if isinstance(dns, dict):
        lines.append("## DNS Record Enumeration")
        record_types_queried = _as_list(dns.get("record_types_queried"))
        queried = ", ".join(str(r) for r in record_types_queried)
        lines.append(f"- **Record Types Queried:** {queried}")
        lines.append(f"- **dnspython Available:** {'Yes' if dns.get('dnspython_available') else 'No'}")
        lines.append("")

        records = _as_dict(dns.get("records"))
        for rtype, values in records.items():
            lines.append(f"### {rtype} Records")
            if isinstance(values, (list, tuple, set)):
                if values:
                    for value in values:
                        lines.append(f"- {value}")
                else:
                    lines.append("*No records found*")
            elif values:
                lines.append(f"- {values}")
            else:
                lines.append("*No records found*")
            lines.append("")

    # WHOIS section
    whois = data.get("whois")
    if isinstance(whois, dict):
        lines.append("## WHOIS Lookup")
        parsed = _as_dict(whois.get("parsed"))
        lines.append(f"- **Server:** {whois.get('server', 'N/A')}:{whois.get('port', 'N/A')}")
        lines.append(f"- **Registrar:** {parsed.get('registrar') or 'N/A'}")
        lines.append(f"- **Creation Date:** {parsed.get('creation_date') or 'N/A'}")
        lines.append(f"- **Expiration Date:** {parsed.get('expiration_date') or 'N/A'}")
        lines.append(f"- **Registrant Organization:** {parsed.get('registrant_org') or 'N/A'}")
        lines.append("")

        nameservers = _as_list(parsed.get("nameservers"))
        if nameservers:
            lines.append("### Nameservers")
            for ns in nameservers:
                lines.append(f"- {ns}")
            lines.append("")

        status_codes = _as_list(parsed.get("status_codes"))
        if status_codes:
            lines.append("### Status Codes")
            for status in status_codes:
                lines.append(f"- {status}")
            lines.append("")

    # Geolocation section
    geo = data.get("geo")
    if isinstance(geo, dict):
        lines.append("## IP Geolocation")
        geo_data = geo.get("geolocation")
        if isinstance(geo_data, dict):
            if geo_data.get("status") == "success":
                fields_map = {
                    "query": "Query IP",
                    "country": "Country",
                    "countryCode": "Country Code",
                    "region": "Region Code",
                    "regionName": "Region Name",
                    "city": "City",
                    "zip": "ZIP/Postal Code",
                    "lat": "Latitude",
                    "lon": "Longitude",
                    "timezone": "Timezone",
                    "isp": "ISP",
                    "org": "Organization",
                    "as": "AS Number/Name",
                    "reverse": "Reverse DNS",
                }
                for key, label in fields_map.items():
                    value = geo_data.get(key)
                    if value is not None and value != "":
                        lines.append(f"- **{label}:** {value}")
                if geo_data.get("cached"):
                    lines.append("- **Cached:** Yes")
                if geo_data.get("offline_fallback"):
                    lines.append("- **Offline Fallback:** Yes")
            else:
                lines.append(f"- **Status:** {geo_data.get('status', 'fail')}")
                if geo_data.get("error"):
                    lines.append(f"- **Error:** {geo_data.get('error')}")
        else:
            lines.append("*No geolocation data available.*")
        lines.append("")

    # Traceroute section
    trace = data.get("trace")
    if isinstance(trace, dict):
        lines.append("## TCP Traceroute")
        lines.append(f"- **Port:** {trace.get('port', 'N/A')}")
        lines.append(f"- **Max Hops:** {trace.get('max_hops', 'N/A')}")
        lines.append(f"- **Probes per Hop:** {trace.get('probes_per_hop', 'N/A')}")
        raw_avail = trace.get("raw_socket_available")
        lines.append(
            f"- **Raw Socket:** "
            f"{'available' if raw_avail else 'unavailable (fallback mode)'}"
        )
        dest = trace.get("destination_reached")
        lines.append(f"- **Destination Reached:** {'Yes' if dest else 'No'}")
        lines.append("")

        hops = _as_list(trace.get("hops"))
        if hops:
            lines.append("### Hop Table")
            lines.append("| Hop | IP | RTT (ms) | Response | Reached |")
            lines.append("|-----|-----|----------|----------|---------|")
            for hop_raw in hops:
                hop = _as_dict(hop_raw)
                hop_num = hop.get("hop", "")
                ip = str(hop.get("ip") or "*").replace("|", "\\|")
                rtt = hop.get("rtt_avg_ms")
                rtt_str = str(rtt) if rtt is not None else str(hop.get("rtt_ms") or "")
                response = str(hop.get("response_type") or "").replace("|", "\\|")
                reached = "Yes" if hop.get("reached_destination") else "No"
                lines.append(f"| {hop_num} | {ip} | {rtt_str} | {response} | {reached} |")
            lines.append("")

    # Notes
    notes = _as_list(data.get("notes"))
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def format_recon_report_csv(data: Mapping[str, object]) -> str:
    """Format recon results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["module", "field", "value"])
    if not isinstance(data, dict):
        return output.getvalue().rstrip("\r\n")

    writer.writerow(["meta", "target", data.get("target", "")])
    writer.writerow(["meta", "domain", data.get("domain", "")])
    modules_run = _as_list(data.get("modules_run"))
    writer.writerow(["meta", "modules_run", ",".join(str(m) for m in modules_run)])

    subdomains = data.get("subdomains")
    if isinstance(subdomains, dict):
        for entry_raw in _as_list(subdomains.get("resolved")):
            entry = _as_dict(entry_raw)
            writer.writerow(
                ["subdomains", entry.get("hostname", ""), entry.get("ip") or ""]
            )

    dns = data.get("dns")
    if isinstance(dns, dict):
        records = _as_dict(dns.get("records"))
        for rtype, values in records.items():
            for value in _as_list(values):
                writer.writerow(["dns", str(rtype), str(value)])

    whois = data.get("whois")
    if isinstance(whois, dict):
        parsed = _as_dict(whois.get("parsed"))
        for key in ("registrar", "creation_date", "expiration_date", "registrant_org"):
            if parsed.get(key):
                writer.writerow(["whois", key, str(parsed.get(key))])
        for ns in _as_list(parsed.get("nameservers")):
            writer.writerow(["whois", "nameserver", str(ns)])
        for status in _as_list(parsed.get("status_codes")):
            writer.writerow(["whois", "status_code", str(status)])

    geo = data.get("geo")
    if isinstance(geo, dict):
        geo_data = _as_dict(geo.get("geolocation"))
        if geo_data.get("error"):
            writer.writerow(["geo", "error", str(geo_data["error"])])
        for key in ("query", "country", "regionName", "city", "lat", "lon", "isp", "org", "as", "reverse"):
            if geo_data.get(key) is not None and geo_data.get(key) != "":
                writer.writerow(["geo", key, str(geo_data.get(key))])

    trace = data.get("trace")
    if isinstance(trace, dict):
        for hop_raw in _as_list(trace.get("hops")):
            hop = _as_dict(hop_raw)
            hop_num = hop.get("hop", hop.get("ttl", ""))
            writer.writerow(["trace", f"hop_{hop_num}", hop.get("ip") or ""])

    for note in _as_list(data.get("notes")):
        writer.writerow(["notes", "", str(note)])

    return output.getvalue().rstrip("\r\n")
