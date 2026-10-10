"""Reconnaissance module for ethscan.

Runs multiple reconnaissance modules (subdomains, dns, whois, geo, trace)
in sequence and produces a consolidated report.
"""

import json
from typing import Dict, List, Optional

from ethscan.subdomains import run_subdomains
from ethscan.dns import run_dns
from ethscan.whois import run_whois
from ethscan.geo import run_geo
from ethscan.trace import run_trace


DEFAULT_RECON_MODULES = ["subdomains", "dns", "whois", "geo", "trace"]


def _normalize_domain(target: str) -> str:
    """Extract a bare domain from a target that may be a URL or host."""
    normalized = target.strip()
    if "://" not in normalized:
        normalized = "https://" + normalized
    from urllib.parse import urlparse
    parsed = urlparse(normalized)
    return parsed.netloc.lower()


def run_recon(
    target: str,
    modules: Optional[List[str]] = None,
    subdomains_wordlist: Optional[List[str]] = None,
    dns_record_types: Optional[List[str]] = None,
    dns_server: Optional[str] = None,
    whois_server: str = "whois.iana.org",
    whois_port: int = 43,
    geo_use_cache: bool = True,
    geo_offline_fallback: bool = True,
    geo_api_url: Optional[str] = None,
    trace_port: int = 80,
    trace_max_hops: int = 30,
    trace_probes_per_hop: int = 3,
    timeout: float = 5.0,
    max_workers: int = 50,
    resolver: Optional[str] = None,
) -> Dict[str, object]:
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

    results: Dict[str, object] = {
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
        results["modules_run"].append("subdomains")
        try:
            results["subdomains"] = run_subdomains(
                target,
                subdomains=subdomains_wordlist,
                timeout=timeout,
                max_workers=max_workers,
                resolver=resolver,
            )
        except Exception as exc:
            results["notes"].append(f"subdomains module failed: {exc}")

    # DNS record enumeration
    if "dns" in enabled_modules:
        results["modules_run"].append("dns")
        try:
            results["dns"] = run_dns(
                target,
                record_types=dns_record_types,
                server=dns_server,
                timeout=timeout,
            )
        except Exception as exc:
            results["notes"].append(f"dns module failed: {exc}")

    # WHOIS lookup
    if "whois" in enabled_modules:
        results["modules_run"].append("whois")
        try:
            results["whois"] = run_whois(
                target,
                server=whois_server,
                port=whois_port,
                timeout=timeout,
            )
        except Exception as exc:
            results["notes"].append(f"whois module failed: {exc}")

    # Geolocation lookup
    if "geo" in enabled_modules:
        results["modules_run"].append("geo")
        try:
            results["geo"] = run_geo(
                target,
                timeout=timeout,
                use_cache=geo_use_cache,
                offline_fallback=geo_offline_fallback,
                api_url=geo_api_url,
            )
        except Exception as exc:
            results["notes"].append(f"geo module failed: {exc}")

    # TCP traceroute
    if "trace" in enabled_modules:
        results["modules_run"].append("trace")
        try:
            results["trace"] = run_trace(
                target,
                port=trace_port,
                max_hops=trace_max_hops,
                timeout=timeout,
                probes_per_hop=trace_probes_per_hop,
            )
            results["modules_run"].append("trace")
        except Exception as exc:
            results["notes"].append(f"trace module failed: {exc}")

    return results


def format_recon_report_json(data: Dict[str, object]) -> str:
    """Format recon results as JSON."""
    return json.dumps(data, indent=2, default=str)


def _markdown_escape(text: object) -> str:
    """Escape pipe characters and newlines for Markdown table cells."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_recon_report_markdown(data: Dict[str, object]) -> str:
    """Format recon results as Markdown."""
    lines = ["# ethscan Reconnaissance Report", ""]
    lines.append(f"- **Target:** {data['target']}")
    lines.append(f"- **Domain:** {data['domain']}")
    lines.append(f"- **Modules Run:** {', '.join(data['modules_run']) if data['modules_run'] else 'None'}")
    lines.append("")

    # Subdomains section
    subdomains = data.get("subdomains")
    if subdomains:
        lines.append("## Subdomain Enumeration")
        lines.append(f"- **Subdomains Tested:** {subdomains.get('subdomains_tested', 0)}")
        lines.append(f"- **Resolved:** {subdomains.get('resolved_count', 0)}")
        resolver = subdomains.get("resolver")
        if resolver:
            lines.append(f"- **Resolver:** {resolver} (dnspython: {'Yes' if subdomains.get('dnspython_available') else 'No'})")
        lines.append("")

        resolved = subdomains.get("resolved", [])
        if resolved:
            lines.append("### Resolved Subdomains")
            lines.append("| Subdomain | Hostname | IP |")
            lines.append("|-----------|----------|----|")
            for entry in resolved:
                lines.append(
                    f"| {_markdown_escape(entry['subdomain'])} | "
                    f"{_markdown_escape(entry['hostname'])} | "
                    f"{_markdown_escape(entry['ip'])} |"
                )
            lines.append("")

    # DNS section
    dns = data.get("dns")
    if dns:
        lines.append("## DNS Record Enumeration")
        lines.append(f"- **Record Types Queried:** {', '.join(dns.get('record_types_queried', []))}")
        lines.append(f"- **dnspython Available:** {'Yes' if dns.get('dnspython_available') else 'No'}")
        lines.append("")

        records = dns.get("records", {})
        for rtype, values in records.items():
            lines.append(f"### {rtype} Records")
            if values:
                for value in values:
                    lines.append(f"- {value}")
            else:
                lines.append("*No records found*")
            lines.append("")

    # WHOIS section
    whois = data.get("whois")
    if whois:
        lines.append("## WHOIS Lookup")
        parsed = whois.get("parsed", {})
        lines.append(f"- **Server:** {whois.get('server', 'N/A')}:{whois.get('port', 'N/A')}")
        lines.append(f"- **Registrar:** {parsed.get('registrar') or 'N/A'}")
        lines.append(f"- **Creation Date:** {parsed.get('creation_date') or 'N/A'}")
        lines.append(f"- **Expiration Date:** {parsed.get('expiration_date') or 'N/A'}")
        lines.append(f"- **Registrant Organization:** {parsed.get('registrant_org') or 'N/A'}")
        lines.append("")

        nameservers = parsed.get("nameservers", [])
        if nameservers:
            lines.append("### Nameservers")
            for ns in nameservers:
                lines.append(f"- {ns}")
            lines.append("")

        status_codes = parsed.get("status_codes", [])
        if status_codes:
            lines.append("### Status Codes")
            for status in status_codes:
                lines.append(f"- {status}")
            lines.append("")

    # Geolocation section
    geo = data.get("geo")
    if geo:
        lines.append("## IP Geolocation")
        geo_data = geo.get("geolocation")
        if geo_data:
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
                    lines.append(f"- **Error:** {geo_data['error']}")
        else:
            lines.append("*No geolocation data available.*")
        lines.append("")

    # Traceroute section
    trace = data.get("trace")
    if trace:
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

        hops = trace.get("hops", [])
        if hops:
            lines.append("### Hop Table")
            lines.append("| Hop | IP | RTT (ms) | Response | Reached |")
            lines.append("|-----|-----|----------|----------|---------|")
            for hop in hops:
                hop_num = hop.get("hop", "")
                ip = str(hop.get("ip") or "*").replace("|", "\\|")
                rtt = hop.get("rtt_avg_ms")
                rtt_str = str(rtt) if rtt is not None else str(hop.get("rtt_ms") or "")
                response = str(hop.get("response_type") or "").replace("|", "\\|")
                reached = "Yes" if hop.get("reached_destination") else "No"
                lines.append(f"| {hop_num} | {ip} | {rtt_str} | {response} | {reached} |")
            lines.append("")

    # Notes
    notes = data.get("notes", [])
    if notes:
        lines.append("## Notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)