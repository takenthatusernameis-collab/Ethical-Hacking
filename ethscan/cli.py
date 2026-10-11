"""Command-line interface for ethscan."""

import json
from typing import Any, Dict, Optional

import click

from ethscan import __version__
from ethscan.passwords import (
    audit_passwords,
    format_audit_report_json,
    format_audit_report_markdown,
)
from ethscan.scanner import get_common_ports, parse_port_range, scan_ports, get_profile_ports, get_profile_defaults, format_scan_report_json, format_scan_report_markdown, format_scan_report_csv, format_service_report_csv
from ethscan.web import (
    format_web_report_json,
    format_web_report_markdown,
    run_web_checks,
)
from ethscan.fuzz import (
    format_fuzz_report_json,
    format_fuzz_report_markdown,
    run_fuzz,
    load_wordlist,
    load_wordlist as load_fuzz_wordlist,
)
from ethscan.brute import (
    format_brute_report_csv,
    format_brute_report_json,
    format_brute_report_markdown,
    run_brute,
)
from ethscan.brute import load_wordlist as load_cred_wordlist
from ethscan.subdomains import (
    format_subdomains_report_json,
    format_subdomains_report_markdown,
    run_subdomains,
    load_subdomain_wordlist,
)
from ethscan.whois import (
    format_whois_report_json,
    format_whois_report_markdown,
    run_whois,
)
from ethscan.dns import (
    format_dns_report_json,
    format_dns_report_markdown,
    run_dns,
)
from ethscan.resolve import (
    format_resolve_report_json,
    format_resolve_report_markdown,
    run_resolve,
)
from ethscan.dnsbrute import (
    format_dnsbrute_report_json,
    format_dnsbrute_report_markdown,
    run_dnsbrute,
)
from ethscan.ssl import (
    format_ssl_report_json,
    format_ssl_report_markdown,
    run_ssl,
)
from ethscan.tls import (
    format_tls_report_json,
    format_tls_report_markdown,
    run_tls,
)
from ethscan.service import (
    format_service_report_json,
    format_service_report_markdown,
    run_service,
)
from ethscan.vuln import (
    format_vuln_report_json,
    format_vuln_report_markdown,
    run_vuln,
)
from ethscan.urlcheck import (
    format_urlcheck_report_json,
    format_urlcheck_report_markdown,
    run_urlcheck,
)
from ethscan.osdetect import (
    format_osdetect_report_json,
    format_osdetect_report_markdown,
    run_osdetect,
)
from ethscan.trace import (
    format_trace_report_json,
    format_trace_report_markdown,
    run_trace,
)
from ethscan.wifi import (
    format_wifi_report_json,
    format_wifi_report_markdown,
    run_wifi,
)
from ethscan.geo import (
    format_geo_report_json,
    format_geo_report_markdown,
    run_geo,
)
from ethscan.recon import (
    format_recon_report_json,
    format_recon_report_markdown,
    run_recon,
)
from ethscan.cert import (
    format_cert_report_json,
    format_cert_report_markdown,
    run_cert,
)
from ethscan.cve import (
    format_cve_report_json,
    format_cve_report_markdown,
    run_cve,
)
from ethscan.cidr import (
    format_cidr_report_json,
    format_cidr_report_markdown,
    run_cidr,
)
from ethscan.hash import (
    format_hash_report_json,
    format_hash_report_markdown,
    run_hash,
)
from ethscan.dnssec import (
    format_dnssec_report_json,
    format_dnssec_report_markdown,
    run_dnssec,
)
from ethscan.subtake import (
    format_subtake_report_json,
    format_subtake_report_markdown,
    run_subtake,
)
from ethscan.mac import (
    format_mac_report_json,
    format_mac_report_markdown,
    run_mac,
)
from ethscan.subdomains import load_subdomain_wordlist
from ethscan.headers import (
    format_headers_report_json,
    format_headers_report_markdown,
    run_headers,
)
from ethscan.ping import (
    format_ping_report_json,
    format_ping_report_markdown,
    run_ping,
)
from ethscan.config import (
    build_default_map,
    load_config,
    validate_config,
)
from ethscan.completion import (
    format_completion_report_json,
    format_completion_report_markdown,
    run_completion,
)


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    help="Path to an ethscan.yaml config file (default: ethscan.yaml or ~/.ethscan.yaml).",
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx, config_path: Optional[str]) -> None:
    """ethscan: ethical hacking toolkit."""
    config = load_config(config_path)
    ctx.obj = {"config": config, "config_path": config_path}
    known_commands = sorted(cli.commands.keys())
    for warning in validate_config(config, known_commands=known_commands):
        click.echo(f"Warning: {warning}", err=True)
    default_map: Dict[str, Dict[str, Any]] = {}
    for name in cli.commands:
        default_map[name] = build_default_map(config, name)
    ctx.default_map = default_map


@cli.command()
@click.option("--target", required=True, help="Target host or IP address")
@click.option(
    "--ports",
    default="common",
    help="Ports to scan: 'common', 'all', or comma-separated list/ranges (e.g., '80,443,8000-9000')",
)
@click.option(
    "--profile",
    type=click.Choice(["fast", "normal", "full"]),
    help="Scan profile: fast (top ~18 ports), normal (common ports), full (1-1024 + common). Overrides --ports, --timeout, --workers unless explicitly set.",
)
@click.option("--timeout", default=1.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=100, type=int, help="Maximum concurrent workers")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format: json, markdown, or csv.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Deprecated alias for --output-format.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def scan(target: str, ports: str, profile: Optional[str], timeout: float, workers: int, output_fmt: Optional[str], fmt: str, out_path: Optional[str]) -> None:
    """Run a port scan against TARGET."""
    if profile:
        defaults = get_profile_defaults(profile)
        if ports == "common":
            port_list = get_profile_ports(profile)
        else:
            port_list = parse_port_range(ports)
        if timeout == 1.0:
            timeout = defaults["timeout"]
        if workers == 100:
            workers = defaults["workers"]
    elif ports.lower() == "common":
        port_list = get_common_ports()
    elif ports.lower() == "all":
        port_list = list(range(1, 65536))
    else:
        port_list = parse_port_range(ports)

    results = scan_ports(target, port_list, timeout=timeout, max_workers=workers)

    open_ports = [port for port, is_open in results if is_open]

    # Prepare structured output for formatters
    scan_data = {
        "target": target,
        "host": target,
        "timeout": timeout,
        "ports_scanned": len(port_list),
        "open_ports": open_ports,
        "details": [{"port": port, "open": is_open} for port, is_open in results],
    }

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_scan_report_json(scan_data)
    elif chosen_format == "markdown":
        output = format_scan_report_markdown(scan_data)
    else:
        output = format_scan_report_csv(scan_data)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--file",
    help="Path to a file containing one password per line. If omitted, reads stdin.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def audit(file: str, fmt: str, out_path: str) -> None:
    """Audit passwords for strength and common weaknesses."""
    if file:
        with open(file, "r", encoding="utf-8") as handle:
            passwords = [line.strip() for line in handle if line.strip()]
    else:
        passwords = [line.strip() for line in click.get_text_stream("stdin") if line.strip()]

    if not passwords:
        click.echo("No passwords provided.")
        return

    results = audit_passwords(passwords)

    if fmt == "json":
        output = format_audit_report_json(passwords, results)
    else:
        output = format_audit_report_markdown(passwords, results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--ports",
    default="common",
    help="Ports to scan: 'common', 'all', or comma-separated list/ranges (e.g., '80,443,8000-9000')",
)
@click.option("--timeout", default=1.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=100, type=int, help="Maximum concurrent workers")
@click.option(
    "--audit-file",
    "audit_file",
    help="Path to a file containing one password per line for password audit",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--output",
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def report(
    target: str,
    ports: str,
    timeout: float,
    workers: int,
    audit_file: str,
    fmt: str,
    out_path: str,
) -> None:
    """Generate a report combining port scan and password audit results."""
    if ports.lower() == "common":
        port_list = get_common_ports()
    elif ports.lower() == "all":
        port_list = list(range(1, 65536))
    else:
        port_list = parse_port_range(ports)

    scan_results = scan_ports(target, port_list, timeout=timeout, max_workers=workers)
    open_ports = [port for port, is_open in scan_results if is_open]

    passwords = []
    if audit_file:
        with open(audit_file, "r", encoding="utf-8") as handle:
            passwords = [line.strip() for line in handle if line.strip()]

    audit_results = audit_passwords(passwords) if passwords else []

    report_data = {
        "scan": {
            "target": target,
            "ports_scanned": len(port_list),
            "open_ports": open_ports,
            "details": [{"port": port, "open": is_open} for port, is_open in scan_results],
        },
        "audit": {
            "passwords_audited": len(passwords),
            "results": [
                {
                    "password": pwd,
                    "length": eval_data["length"],
                    "entropy": eval_data["entropy"],
                    "common": eval_data["common"],
                    "patterns": eval_data["patterns"],
                    "score": eval_data["score"],
                    "verdict": eval_data["verdict"],
                }
                for pwd, eval_data in audit_results
            ],
        },
    }

    if fmt == "json":
        output = json.dumps(report_data, indent=2)
    else:
        output = _generate_markdown(report_data)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--checks",
    default="headers,info_disclosure,ssl",
    help="Comma-separated list of checks: headers, info_disclosure, ssl",
)
@click.option("--timeout", default=5.0, type=float, help="Request timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def web(target: str, checks: str, timeout: float, fmt: str, out_path: str) -> None:
    """Run web application security checks against TARGET."""
    check_list = [c.strip() for c in checks.split(",") if c.strip()]
    valid = {"headers", "info_disclosure", "ssl"}
    unknown = [c for c in check_list if c not in valid]
    if unknown:
        click.echo(f"Unknown checks: {', '.join(unknown)}")
        click.echo(f"Valid checks: {', '.join(sorted(valid))}")
        return

    results = run_web_checks(target, check_list, timeout=timeout)

    if fmt == "json":
        output = format_web_report_json(results)
    else:
        output = format_web_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--wordlist",
    "wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file (one path per line). Uses built-in default if omitted.",
)
@click.option("--timeout", default=5.0, type=float, help="Request timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def fuzz(target: str, wordlist_path: str, timeout: float, fmt: str, out_path: str) -> None:
    """Run HTTP fuzzing against TARGET using a wordlist of paths."""
    wordlist = load_wordlist(wordlist_path) if wordlist_path else None

    results = run_fuzz(target, wordlist=wordlist, timeout=timeout)

    if fmt == "json":
        output = format_fuzz_report_json(results)
    else:
        output = format_fuzz_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--wordlist",
    "wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file (one subdomain per line). Uses built-in default if omitted.",
)
@click.option(
    "--resolver",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Enable recursive subdomain enumeration (discover subdomains of resolved subdomains).",
)
@click.option(
    "--max-depth",
    default=2,
    type=int,
    help="Maximum recursion depth for recursive enumeration (default: 2).",
)
@click.option("--timeout", default=2.0, type=float, help="DNS resolution timeout in seconds")
@click.option(
    "--workers",
    default=50,
    type=int,
    help="Maximum concurrent DNS resolution workers",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def subdomains(
    target: str,
    wordlist_path: str,
    resolver: Optional[str],
    recursive: bool,
    max_depth: int,
    timeout: float,
    workers: int,
    fmt: str,
    out_path: str,
) -> None:
    """Enumerate subdomains for TARGET."""
    subdomains_list = (
        load_subdomain_wordlist(wordlist_path) if wordlist_path else None
    )

    results = run_subdomains(
        target,
        subdomains=subdomains_list,
        timeout=timeout,
        max_workers=workers,
        resolver=resolver,
        recursive=recursive,
        max_depth=max_depth,
    )

    if fmt == "json":
        output = format_subdomains_report_json(results)
    else:
        output = format_subdomains_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--wordlist",
    "wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file (one subdomain per line). Uses built-in default if omitted.",
)
@click.option(
    "--resolver",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option("--timeout", default=2.0, type=float, help="DNS resolution timeout in seconds")
@click.option(
    "--workers",
    default=50,
    type=int,
    help="Maximum concurrent DNS resolution workers",
)
@click.option("--http-timeout", default=5.0, type=float, help="HTTP request timeout for fingerprinting in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def subtake(
    target: str,
    wordlist_path: Optional[str],
    resolver: Optional[str],
    timeout: float,
    workers: int,
    http_timeout: float,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Detect subdomain takeover vulnerabilities for TARGET."""
    subdomains_list = (
        load_subdomain_wordlist(wordlist_path) if wordlist_path else None
    )

    results = run_subtake(
        target,
        subdomains=subdomains_list,
        timeout=timeout,
        max_workers=workers,
        resolver=resolver,
        http_timeout=http_timeout,
    )

    if fmt == "json":
        output = format_subtake_report_json(results)
    else:
        output = format_subtake_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--server",
    default="whois.iana.org",
    help="WHOIS server to query (default: whois.iana.org)",
)
@click.option("--port", default=43, type=int, help="WHOIS server port (default: 43)")
@click.option("--timeout", default=5.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Enable recursive WHOIS queries: follow referral servers extracted from "
    "each response (e.g. from whois.iana.org to the registrar's WHOIS server).",
)
@click.option(
    "--max-depth",
    default=2,
    type=int,
    help="Maximum recursive hops when --recursive is enabled (default: 2).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def whois(
    target: str,
    server: str,
    port: int,
    timeout: float,
    recursive: bool,
    max_depth: int,
    fmt: str,
    out_path: str,
) -> None:
    """Run a WHOIS lookup for TARGET."""
    results = run_whois(
        target,
        server=server,
        port=port,
        timeout=timeout,
        recursive=recursive,
        max_depth=max_depth,
    )

    if fmt == "json":
        output = format_whois_report_json(results)
    else:
        output = format_whois_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option("--timeout", default=5.0, type=float, help="Request timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def headers(target: str, timeout: float, fmt: str, out_path: str) -> None:
    """Run security headers check against TARGET."""
    results = run_headers(target, timeout=timeout)

    if fmt == "json":
        output = format_headers_report_json(results)
    else:
        output = format_headers_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--types",
    "record_types",
    default="A,AAAA",
    help="Comma-separated list of DNS record types: A, AAAA, MX, NS, TXT, CNAME, SOA",
)
@click.option(
    "--server",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option("--timeout", default=2.0, type=float, help="Resolution timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def dns(
    target: str,
    record_types: str,
    server: str,
    timeout: float,
    fmt: str,
    out_path: str,
) -> None:
    """Enumerate DNS records for TARGET."""
    types_list = [t.strip().upper() for t in record_types.split(",") if t.strip()]
    valid_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"}
    unknown = [t for t in types_list if t not in valid_types]
    if unknown:
        click.echo(f"Unknown record types: {', '.join(unknown)}")
        click.echo(f"Valid types: {', '.join(sorted(valid_types))}")
        return

    results = run_dns(target, record_types=types_list, server=server, timeout=timeout)

    if fmt == "json":
        output = format_dns_report_json(results)
    else:
        output = format_dns_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain, IP address, or URL (e.g. example.com, 8.8.8.8, https://example.com)",
)
@click.option(
    "--types",
    "record_types",
    help="Comma-separated list of DNS record types: A, AAAA, CNAME, PTR. "
    "Defaults to A,AAAA,CNAME for domains; PTR for IP addresses.",
)
@click.option(
    "--server",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option("--timeout", default=2.0, type=float, help="Resolution timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def resolve(
    target: str,
    record_types: Optional[str],
    server: Optional[str],
    timeout: float,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Perform forward/reverse DNS resolution for TARGET."""
    types_list = None
    if record_types:
        types_list = [t.strip().upper() for t in record_types.split(",") if t.strip()]
        valid_types = {"A", "AAAA", "CNAME", "PTR"}
        unknown = [t for t in types_list if t not in valid_types]
        if unknown:
            click.echo(f"Unknown record types: {', '.join(unknown)}")
            click.echo(f"Valid types: {', '.join(sorted(valid_types))}")
            return

    results = run_resolve(target, record_types=types_list, server=server, timeout=timeout)

    if fmt == "json":
        output = format_resolve_report_json(results)
    else:
        output = format_resolve_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--ns",
    "nameservers_option",
    help="Comma-separated authoritative nameservers for AXFR attempts "
    "(discovered via NS lookup if omitted; requires dnspython).",
)
@click.option(
    "--wordlist",
    "wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file (one subdomain per line). Uses built-in default if omitted.",
)
@click.option(
    "--resolver",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Enable recursive AXFR attempts against nameservers discovered in zone transfers.",
)
@click.option(
    "--max-depth",
    default=2,
    type=int,
    help="Maximum recursion depth for recursive AXFR (default: 2).",
)
@click.option("--timeout", default=2.0, type=float, help="DNS timeout in seconds")
@click.option(
    "--workers",
    default=50,
    type=int,
    help="Maximum concurrent DNS resolution workers",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def dnsbrute(
    target: str,
    nameservers_option: Optional[str],
    wordlist_path: Optional[str],
    resolver: Optional[str],
    recursive: bool,
    max_depth: int,
    timeout: float,
    workers: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Attempt AXFR zone transfer and brute-force subdomains for TARGET."""
    nameservers = (
        [ns.strip() for ns in nameservers_option.split(",") if ns.strip()]
        if nameservers_option
        else None
    )
    wordlist = load_subdomain_wordlist(wordlist_path) if wordlist_path else None

    results = run_dnsbrute(
        target,
        nameservers=nameservers,
        subdomains=wordlist,
        timeout=timeout,
        max_workers=workers,
        resolver=resolver,
        recursive=recursive,
        max_depth=max_depth,
    )

    if fmt == "json":
        output = format_dnsbrute_report_json(results)
    else:
        output = format_dnsbrute_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host or URL (e.g. example.com or https://example.com)")
@click.option("--port", default=443, type=int, help="TLS port (default: 443)")
@click.option("--timeout", default=5.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ssl(target: str, port: int, timeout: float, fmt: str, out_path: str) -> None:
    """Inspect the SSL/TLS certificate for TARGET."""
    results = run_ssl(target, port=port, timeout=timeout)

    if fmt == "json":
        output = format_ssl_report_json(results)
    else:
        output = format_ssl_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host or URL (e.g. example.com or https://example.com)")
@click.option("--port", default=443, type=int, help="TLS port (default: 443)")
@click.option(
    "--versions",
    default="TLSv1,TLSv1_1,TLSv1_2,TLSv1_3",
    help="Comma-separated list of TLS versions to test (e.g. 'TLSv1_2,TLSv1_3')",
)
@click.option(
    "--ciphers",
    "cipher_option",
    help="Comma-separated list of cipher suites to test. Defaults to a built-in common list.",
)
@click.option("--timeout", default=5.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=10, type=int, help="Maximum concurrent probe workers")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def tls(
    target: str,
    port: int,
    versions: str,
    cipher_option: Optional[str],
    timeout: float,
    workers: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Enumerate supported TLS protocol versions and cipher suites for TARGET."""
    version_list = [v.strip() for v in versions.split(",") if v.strip()]
    cipher_list = (
        [c.strip() for c in cipher_option.split(",") if c.strip()]
        if cipher_option
        else None
    )

    try:
        results = run_tls(
            target,
            port=port,
            timeout=timeout,
            versions=version_list,
            ciphers=cipher_list,
            max_workers=workers,
        )
    except ValueError as exc:
        click.echo(str(exc))
        return

    if fmt == "json":
        output = format_tls_report_json(results)
    else:
        output = format_tls_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host or URL (e.g. example.com or https://example.com)")
@click.option(
    "--ports",
    help="Ports to scan: comma-separated list/ranges (e.g., '21,22,80,443,8000-9000'). Defaults to common ports.",
)
@click.option(
    "--profile",
    type=click.Choice(["fast", "normal", "full"]),
    help="Scan profile: fast (top ~18 ports), normal (common ports), full (1-1024 + common). Overrides --ports, --timeout, --workers unless explicitly set.",
)
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=50, type=int, help="Maximum concurrent workers")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format: json, markdown, or csv.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Deprecated alias for --output-format.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def service(target: str, ports: Optional[str], profile: Optional[str], timeout: float, workers: int, output_fmt: Optional[str], fmt: str, out_path: Optional[str]) -> None:
    """Detect services and grab banners on open ports (nmap-style)."""
    port_list = None
    if profile:
        defaults = get_profile_defaults(profile)
        if ports:
            from ethscan.scanner import parse_port_range
            port_list = parse_port_range(ports)
        else:
            port_list = get_profile_ports(profile)
        if timeout == 3.0:
            timeout = defaults["timeout"]
        if workers == 50:
            workers = defaults["workers"]
    elif ports:
        from ethscan.scanner import parse_port_range
        port_list = parse_port_range(ports)

    results = run_service(target, ports=port_list, timeout=timeout, max_workers=workers)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_service_report_json(results)
    elif chosen_format == "markdown":
        output = format_service_report_markdown(results)
    else:
        output = format_service_report_csv(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--ports",
    help="Ports to scan for service detection: comma-separated list/ranges "
    "(e.g., '21,22,80'). Defaults to common ports.",
)
@click.option(
    "--services-file",
    "services_file",
    type=click.Path(exists=True, readable=True),
    help="JSON file with 'service' command output (skips live detection).",
)
@click.option(
    "--tls-file",
    "tls_file",
    type=click.Path(exists=True, readable=True),
    help="JSON file with 'tls' command output to check protocol/cipher "
    "weaknesses.",
)
@click.option(
    "--ssl-file",
    "ssl_file",
    type=click.Path(exists=True, readable=True),
    help="JSON file with 'ssl' command output to check certificate "
    "weaknesses.",
)
@click.option(
    "--severity",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Only report findings with the given severity.",
)
@click.option(
    "--min-severity",
    "min_severity",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Drop findings below this severity threshold (e.g. --min-severity high).",
)
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=50, type=int, help="Maximum concurrent workers")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def vuln(
    target: str,
    ports: Optional[str],
    services_file: Optional[str],
    tls_file: Optional[str],
    ssl_file: Optional[str],
    severity: Optional[str],
    min_severity: Optional[str],
    timeout: float,
    workers: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Check TARGET for known service, protocol, and certificate vulnerabilities."""
    services = None
    if services_file:
        with open(services_file, "r", encoding="utf-8") as handle:
            services = json.load(handle)

    tls_data = None
    if tls_file:
        with open(tls_file, "r", encoding="utf-8") as handle:
            tls_data = json.load(handle)

    certificate = None
    if ssl_file:
        with open(ssl_file, "r", encoding="utf-8") as handle:
            certificate = json.load(handle)

    port_list = None
    if ports:
        from ethscan.scanner import parse_port_range
        port_list = parse_port_range(ports)

    results = run_vuln(
        target,
        ports=port_list,
        timeout=timeout,
        max_workers=workers,
        services=services,
        tls=tls_data,
        certificate=certificate,
        severity=severity,
        min_severity=min_severity,
    )

    if fmt == "json":
        output = format_vuln_report_json(results)
    else:
        output = format_vuln_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target URL (e.g. https://example.com)")
@click.option(
    "--checks",
    default="headers,info_disclosure,ssl",
    help="Comma-separated list of web checks: headers, info_disclosure, ssl",
)
@click.option(
    "--wordlist",
    "wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file for fuzzing (one path per line). Uses built-in default if omitted.",
)
@click.option(
    "--fuzz-paths/--no-fuzz-paths",
    default=True,
    help="Enable/disable HTTP path fuzzing (default: enabled)",
)
@click.option("--port", default=443, type=int, help="TLS port for SSL certificate inspection (default: 443)")
@click.option("--timeout", default=5.0, type=float, help="Request timeout in seconds")
@click.option("--workers", default=10, type=int, help="Maximum concurrent workers for fuzzing")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def urlcheck(
    target: str,
    checks: str,
    wordlist_path: Optional[str],
    fuzz_paths: bool,
    port: int,
    timeout: float,
    workers: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Run consolidated web assessment (headers, info disclosure, SSL, fuzzing, cert inspection)."""
    check_list = [c.strip() for c in checks.split(",") if c.strip()]
    valid = {"headers", "info_disclosure", "ssl"}
    unknown = [c for c in check_list if c not in valid]
    if unknown:
        click.echo(f"Unknown checks: {', '.join(unknown)}")
        click.echo(f"Valid checks: {', '.join(sorted(valid))}")
        return

    wordlist = load_fuzz_wordlist(wordlist_path) if wordlist_path else None

    results = run_urlcheck(
        target,
        check_list,
        wordlist=wordlist,
        fuzz_paths=fuzz_paths,
        port=port,
        timeout=timeout,
        workers=workers,
    )

    if fmt == "json":
        output = format_urlcheck_report_json(results)
    else:
        output = format_urlcheck_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. ftp.example.com or ssh.example.com)",
)
@click.option(
    "--protocol",
    type=click.Choice(["ftp", "ssh"]),
    default="ftp",
    help="Protocol to brute force (default: ftp)",
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="Target port (default: 21 for ftp, 22 for ssh)",
)
@click.option(
    "--user-file",
    "user_file",
    type=click.Path(exists=True, readable=True),
    help="Path to usernames wordlist (one per line). Uses built-in default if omitted.",
)
@click.option(
    "--pass-file",
    "pass_file",
    type=click.Path(exists=True, readable=True),
    help="Path to passwords wordlist (one per line). Uses built-in default if omitted.",
)
@click.option("--timeout", default=5.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=10, type=int, help="Maximum concurrent workers")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format: json, markdown, or csv (credential dump).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Deprecated alias for --output-format.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def brute(
    target: str,
    protocol: str,
    port: Optional[int],
    user_file: Optional[str],
    pass_file: Optional[str],
    timeout: float,
    workers: int,
    output_fmt: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Brute-force FTP or SSH login credentials against TARGET."""
    usernames = load_cred_wordlist(user_file) if user_file else None
    passwords = load_cred_wordlist(pass_file) if pass_file else None

    results = run_brute(
        target,
        protocol=protocol,
        usernames=usernames,
        passwords=passwords,
        port=port,
        timeout=timeout,
        max_workers=workers,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_brute_report_json(results)
    elif chosen_format == "markdown":
        output = format_brute_report_markdown(results)
    else:
        output = format_brute_report_csv(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--ports",
    help="Ports to probe: comma-separated list/ranges (e.g., '22,80,443'). Defaults to common ports.",
)
@click.option(
    "--banners-file",
    "banners_file",
    type=click.Path(exists=True, readable=True),
    help="JSON file with 'service' command output (port -> banner mapping) to cross-reference OS signatures.",
)
@click.option("--timeout", default=5.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=10, type=int, help="Maximum concurrent probe workers")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def osdetect(
    target: str,
    ports: Optional[str],
    banners_file: Optional[str],
    timeout: float,
    workers: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Fingerprint the target operating system using TCP/IP stack behavior."""
    port_list = None
    if ports:
        from ethscan.scanner import parse_port_range
        port_list = parse_port_range(ports)

    banners = None
    if banners_file:
        with open(banners_file, "r", encoding="utf-8") as handle:
            services = json.load(handle)
        banners = {}
        for entry in services.get("results") or []:
            port = entry.get("port")
            banner = entry.get("banner")
            if port is not None and banner:
                banners[port] = banner

    results = run_osdetect(
        target,
        ports=port_list,
        timeout=timeout,
        max_workers=workers,
        banners=banners,
    )

    if fmt == "json":
        output = format_osdetect_report_json(results)
    else:
        output = format_osdetect_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. example.com or https://example.com)",
)
@click.option("--port", default=80, type=int, help="Target TCP port for SYN probes (default: 80)")
@click.option(
    "--max-hops",
    "max_hops",
    default=30,
    type=int,
    help="Maximum TTL / hops to probe (default: 30, max: 128)",
)
@click.option(
    "--probes-per-hop",
    "probes_per_hop",
    default=3,
    type=int,
    help="Number of probes per hop for RTT averaging (default: 3)",
)
@click.option("--timeout", default=3.0, type=float, help="Per-probe timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def trace(
    target: str,
    port: int,
    max_hops: int,
    probes_per_hop: int,
    timeout: float,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Run TCP traceroute against TARGET using TTL-incremented SYN probes."""
    results = run_trace(
        target,
        port=port,
        max_hops=max_hops,
        timeout=timeout,
        probes_per_hop=probes_per_hop,
    )

    if fmt == "json":
        output = format_trace_report_json(results)
    else:
        output = format_trace_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--count",
    default=4,
    type=int,
    help="Number of echo requests to send (default: 4)",
)
@click.option(
    "--timeout",
    default=2.0,
    type=float,
    help="Per-probe timeout in seconds (default: 2.0)",
)
@click.option(
    "--ttl",
    default=64,
    type=int,
    help="Time-to-live value for probes (default: 64)",
)
@click.option(
    "--tcp-port",
    default=80,
    type=int,
    help="Target TCP port for connect-based fallback when ICMP is unavailable (default: 80)",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ping(
    target: str,
    count: int,
    timeout: float,
    ttl: int,
    tcp_port: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Run ICMP ping (or TCP connect fallback) against TARGET for host discovery."""
    results = run_ping(
        target,
        count=count,
        timeout=timeout,
        ttl=ttl,
        port=tcp_port,
    )

    if fmt == "json":
        output = format_ping_report_json(results)
    else:
        output = format_ping_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--interface",
    help="Specific wireless interface to scan (e.g., wlan0). If omitted, scans all available interfaces.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def wifi(interface: Optional[str], fmt: str, out_path: Optional[str]) -> None:
    """Scan for nearby Wi-Fi access points (Linux only)."""
    results = run_wifi(interface=interface)

    if fmt == "json":
        output = format_wifi_report_json(results)
    else:
        output = format_wifi_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target IP address, hostname, or URL (e.g., 8.8.8.8, example.com, https://example.com)",
)
@click.option("--timeout", default=5.0, type=float, help="API request timeout in seconds")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable local filesystem cache",
)
@click.option(
    "--no-offline-fallback",
    is_flag=True,
    help="Disable offline fallback to stale cache when API is unavailable",
)
@click.option(
    "--api-url",
    help="Custom geolocation API base URL (must support ip-api.com query format)",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Enable recursive hop geolocation: run a traceroute to the target and geolocate each discovered hop IP.",
)
@click.option(
    "--max-depth",
    default=30,
    type=int,
    help="Maximum number of traceroute hops when --recursive is enabled (default: 30, max: 128).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def geo(
    target: str,
    timeout: float,
    no_cache: bool,
    no_offline_fallback: bool,
    api_url: Optional[str],
    recursive: bool,
    max_depth: int,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Look up IP geolocation for TARGET using a public API with caching."""
    results = run_geo(
        target,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
        recursive=recursive,
        max_depth=max_depth,
    )

    if fmt == "json":
        output = format_geo_report_json(results)
    else:
        output = format_geo_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain, IP, or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--modules",
    default=None,
    help="Comma-separated list of modules to run: subdomains, dns, whois, geo, trace. Default: all.",
)
@click.option(
    "--subdomains-wordlist",
    "subdomains_wordlist_path",
    type=click.Path(exists=True, readable=True),
    help="Path to wordlist file for subdomain enumeration.",
)
@click.option(
    "--dns-types",
    "dns_record_types",
    default="A,AAAA,MX,NS,TXT,CNAME,SOA",
    help="Comma-separated list of DNS record types to query.",
)
@click.option(
    "--dns-server",
    help="Custom DNS resolver IP address (requires dnspython).",
)
@click.option(
    "--whois-server",
    default="whois.iana.org",
    help="WHOIS server to query (default: whois.iana.org).",
)
@click.option("--whois-port", default=43, type=int, help="WHOIS server port (default: 43)")
@click.option(
    "--no-geo-cache",
    is_flag=True,
    help="Disable local filesystem cache for geolocation.",
)
@click.option(
    "--no-geo-offline-fallback",
    is_flag=True,
    help="Disable offline fallback to stale cache when API is unavailable.",
)
@click.option(
    "--geo-api-url",
    help="Custom geolocation API base URL (must support ip-api.com query format).",
)
@click.option("--trace-port", default=80, type=int, help="Target TCP port for traceroute (default: 80)")
@click.option(
    "--trace-max-hops",
    "trace_max_hops",
    default=30,
    type=int,
    help="Maximum TTL / hops for traceroute (default: 30, max: 128)",
)
@click.option(
    "--trace-probes-per-hop",
    "trace_probes_per_hop",
    default=3,
    type=int,
    help="Number of probes per hop for RTT averaging (default: 3)",
)
@click.option("--timeout", default=5.0, type=float, help="Network timeout in seconds")
@click.option(
    "--workers",
    default=50,
    type=int,
    help="Maximum concurrent workers for subdomain enumeration",
)
@click.option(
    "--resolver",
    help="Custom DNS resolver IP address for subdomains (requires dnspython)",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def recon(
    target: str,
    modules: Optional[str],
    subdomains_wordlist_path: Optional[str],
    dns_record_types: str,
    dns_server: Optional[str],
    whois_server: str,
    whois_port: int,
    no_geo_cache: bool,
    no_geo_offline_fallback: bool,
    geo_api_url: Optional[str],
    trace_port: int,
    trace_max_hops: int,
    trace_probes_per_hop: int,
    timeout: float,
    workers: int,
    resolver: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Run multiple reconnaissance modules against TARGET and produce a consolidated report."""
    modules_list = (
        [m.strip() for m in modules.split(",") if m.strip()]
        if modules
        else None
    )
    subdomains_wordlist = (
        load_subdomain_wordlist(subdomains_wordlist_path)
        if subdomains_wordlist_path
        else None
    )
    dns_types_list = [t.strip().upper() for t in dns_record_types.split(",") if t.strip()]

    results = run_recon(
        target,
        modules=modules_list,
        subdomains_wordlist=subdomains_wordlist,
        dns_record_types=dns_types_list,
        dns_server=dns_server,
        whois_server=whois_server,
        whois_port=whois_port,
        geo_use_cache=not no_geo_cache,
        geo_offline_fallback=not no_geo_offline_fallback,
        geo_api_url=geo_api_url,
        trace_port=trace_port,
        trace_max_hops=trace_max_hops,
        trace_probes_per_hop=trace_probes_per_hop,
        timeout=timeout,
        max_workers=workers,
        resolver=resolver,
    )

    if fmt == "json":
        output = format_recon_report_json(results)
    else:
        output = format_recon_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain or URL (e.g. example.com or https://example.com)",
)
@click.option("--timeout", default=10.0, type=float, help="API request timeout in seconds")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable local filesystem cache",
)
@click.option(
    "--no-offline-fallback",
    is_flag=True,
    help="Disable offline fallback to stale cache when API is unavailable",
)
@click.option(
    "--api-url",
    help="Custom Certificate Transparency API base URL (crt.sh-compatible JSON output)",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def cert(
    target: str,
    timeout: float,
    no_cache: bool,
    no_offline_fallback: bool,
    api_url: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Search Certificate Transparency logs for certificates issued to TARGET."""
    results = run_cert(
        target,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
    )

    if fmt == "json":
        output = format_cert_report_json(results)
    else:
        output = format_cert_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target host or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--services-file",
    "services_file",
    type=click.Path(exists=True, readable=True),
    help="JSON file with 'service' command output (skips live detection).",
)
@click.option(
    "--ports",
    help="Ports to scan for live service detection: comma-separated list/ranges "
    "(e.g., '21,22,80'). Defaults to common ports.",
)
@click.option("--timeout", default=10.0, type=float, help="API request timeout in seconds")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable local filesystem cache",
)
@click.option(
    "--no-offline-fallback",
    is_flag=True,
    help="Disable offline fallback to stale cache when API is unavailable",
)
@click.option(
    "--api-url",
    help="Custom NVD/CVE API base URL (must support NVD query format)",
)
@click.option(
    "--severity",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Only report findings with the given severity.",
)
@click.option(
    "--min-severity",
    "min_severity",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Drop findings below this severity threshold (e.g. --min-severity high).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def cve(
    target: str,
    services_file: Optional[str],
    ports: Optional[str],
    timeout: float,
    no_cache: bool,
    no_offline_fallback: bool,
    api_url: Optional[str],
    severity: Optional[str],
    min_severity: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Query the NVD/CVE API for known vulnerabilities affecting TARGET's services."""
    services = None
    if services_file:
        with open(services_file, "r", encoding="utf-8") as handle:
            services = json.load(handle)

    port_list = None
    if ports and not services_file:
        from ethscan.scanner import parse_port_range
        port_list = parse_port_range(ports)

    results = run_cve(
        target,
        services_file=services_file,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
        severity=severity,
        min_severity=min_severity,
        ports=port_list,
    )

    if fmt == "json":
        output = format_cve_report_json(results)
    else:
        output = format_cve_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--cidr",
    required=True,
    help="CIDR notation (e.g. 192.168.1.0/24) or bare IP address.",
)
@click.option(
    "--contains",
    help="Optional IP address to test for network membership.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def cidr(cidr: str, contains: Optional[str], fmt: str, out_path: Optional[str]) -> None:
    """Compute network calculations for a CIDR (offline)."""
    results = run_cidr(cidr, contains=contains)

    if fmt == "json":
        output = format_cidr_report_json(results)
    else:
        output = format_cidr_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command(name="hash")
@click.option(
    "--password",
    "passwords",
    multiple=True,
    help="Password to hash (repeatable). If omitted, reads one password per line from stdin.",
)
@click.option(
    "--algorithm",
    default="md5",
    type=click.Choice(["md5", "sha1", "sha256", "sha512", "ntlm", "md4"]),
    help="Hash algorithm (default: md5).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def hash_cmd(passwords, algorithm, fmt, out_path) -> None:
    """Generate cryptographic hashes for passwords (MD5, SHA-1, SHA-256, SHA-512, NTLM, MD4)."""
    password_list = list(passwords)
    if not password_list:
        password_list = [line.strip() for line in click.get_text_stream("stdin") if line.strip()]

    if not password_list:
        click.echo("No passwords provided.")
        return

    results = run_hash(password_list, algorithm=algorithm)

    if fmt == "json":
        output = format_hash_report_json(results)
    else:
        output = format_hash_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="Target domain or URL (e.g. example.com or https://example.com)",
)
@click.option(
    "--server",
    help="Custom DNS resolver IP address (requires dnspython)",
)
@click.option("--timeout", default=5.0, type=float, help="Query timeout in seconds")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def dnssec(
    target: str,
    server: Optional[str],
    timeout: float,
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Validate DNSSEC for TARGET domain."""
    results = run_dnssec(
        target,
        server=server,
        timeout=timeout,
    )

    if fmt == "json":
        output = format_dnssec_report_json(results)
    else:
        output = format_dnssec_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    required=True,
    help="MAC address, hostname, or URL (e.g. 00:1A:2B:3C:4D:5E, example.com, https://example.com)",
)
@click.option(
    "--timeout",
    default=5.0,
    type=float,
    help="API request timeout in seconds (default: 5.0)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable local filesystem cache",
)
@click.option(
    "--no-offline-fallback",
    is_flag=True,
    help="Disable offline fallback to stale cache when API is unavailable",
)
@click.option(
    "--api-url",
    help="Custom OUI API base URL (must support api.macvendors.com query format)",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def mac(
    target: str,
    timeout: float,
    no_cache: bool,
    no_offline_fallback: bool,
    api_url: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Look up MAC address vendor using the OUI database (api.macvendors.com) with caching."""
    results = run_mac(
        target,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
    )

    if fmt == "json":
        output = format_mac_report_json(results)
    else:
        output = format_mac_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


def _generate_markdown(data: dict) -> str:
    """Generate a Markdown report from the data dictionary."""
    lines = ["# ethscan Report", ""]

    scan = data["scan"]
    lines.append("## Port Scan")
    lines.append(f"- **Target:** {scan['target']}")
    lines.append(f"- **Ports Scanned:** {scan['ports_scanned']}")
    lines.append(f"- **Open Ports:** {', '.join(map(str, scan['open_ports'])) if scan['open_ports'] else 'None'}")
    lines.append("")
    lines.append("| Port | Status |")
    lines.append("|------|--------|")
    for detail in scan["details"]:
        status = "Open" if detail["open"] else "Closed"
        lines.append(f"| {detail['port']} | {status} |")
    lines.append("")

    audit = data["audit"]
    lines.append("## Password Audit")
    lines.append(f"- **Passwords Audited:** {audit['passwords_audited']}")
    lines.append("")
    if audit["results"]:
        lines.append("| Password | Length | Entropy | Common | Patterns | Score | Verdict |")
        lines.append("|----------|--------|---------|--------|----------|-------|---------|")
        for result in audit["results"]:
            lines.append(
                f"| {result['password']!r} | {result['length']} | {result['entropy']} | "
                f"{'Yes' if result['common'] else 'No'} | {'Yes' if result['patterns'] else 'No'} | "
                f"{result['score']} | {result['verdict']} |"
            )
    else:
        lines.append("*No passwords provided for audit.*")
    lines.append("")

    return "\n".join(lines)


@cli.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    help="Path to an ethscan.yaml config file (default: ethscan.yaml or ~/.ethscan.yaml).",
)
@click.option(
    "--init",
    "init_path",
    type=click.Path(writable=True),
    help="Write a sample config file to PATH and exit.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format for the loaded config (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
@click.pass_context
def config(
    ctx,
    config_path: Optional[str],
    init_path: Optional[str],
    fmt: str,
    out_path: Optional[str],
) -> None:
    """Inspect or initialize the ethscan configuration file."""
    from ethscan.config import dump_default_config

    if init_path:
        sample = dump_default_config()
        try:
            with open(init_path, "w", encoding="utf-8") as handle:
                handle.write(sample)
        except OSError as exc:
            click.echo(f"Error writing config: {exc}", err=True)
            raise SystemExit(1)
        click.echo(f"Sample config written to {init_path}")
        return

    # Inherit the parent's --config path when the subcommand's own option
    # was not provided, so `ethscan --config X config` works as expected.
    if not config_path and ctx.obj and isinstance(ctx.obj, dict):
        parent_config = ctx.obj.get("config_path")
        if parent_config:
            config_path = parent_config

    loaded = load_config(config_path)
    path = loaded.get("_path")
    parse_error = loaded.get("_parse_error")

    if fmt == "json":
        payload: Dict[str, Any] = {
            "config_file": path,
            "defaults": loaded.get("defaults") or {},
            "commands": loaded.get("commands") or {},
        }
        if isinstance(parse_error, str):
            payload["parse_error"] = parse_error
        output = json.dumps(payload, indent=2, default=str)
    else:
        lines = ["# ethscan Configuration", ""]
        if path:
            lines.append(f"- **Config file:** {path}")
        else:
            lines.append("*No config file found; using built-in defaults.*")
        if isinstance(parse_error, str):
            lines.append("")
            lines.append("## Parse Error")
            lines.append(f"```\n{parse_error}\n```")
            lines.append("")
        lines.append("")

        defaults = loaded.get("defaults") or {}
        lines.append("## Global Defaults")
        if defaults:
            lines.append("| Option | Value |")
            lines.append("|--------|-------|")
            for key, value in defaults.items():
                lines.append(f"| {key} | {value} |")
        else:
            lines.append("*No global defaults configured.*")
        lines.append("")

        commands = loaded.get("commands") or {}
        lines.append("## Per-Command Overrides")
        if commands:
            for cmd, opts in commands.items():
                lines.append(f"### {cmd}")
                if isinstance(opts, dict) and opts:
                    lines.append("| Option | Value |")
                    lines.append("|--------|-------|")
                    for key, value in opts.items():
                        lines.append(f"| {key} | {value} |")
                else:
                    lines.append("*No overrides.*")
                lines.append("")
        else:
            lines.append("*No per-command overrides configured.*")
        lines.append("")

        lines.append("## Notes")
        lines.append(
            "- CLI arguments always take precedence over config values."
        )
        lines.append(
            "- Use `ethscan config --init PATH` to create a sample config file."
        )
        lines.append("")
        output = "\n".join(lines)

    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as handle:
                handle.write(output)
        except OSError as exc:
            click.echo(f"Error writing output: {exc}", err=True)
            raise SystemExit(1)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    default="bash",
    help="Shell to generate a completion script for (default: bash).",
)
@click.option(
    "--prog-name",
    "prog_name",
    default="ethscan",
    help="Program name embedded in the completion script (default: ethscan).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (json or markdown)",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def completion(shell: str, prog_name: str, fmt: str, out_path: Optional[str]) -> None:
    """Generate a shell completion script for ethscan.

    Supported shells: bash, zsh, fish. Save the output and source it
    in your shell to enable tab completion of commands, options, and
    option values.
    """
    try:
        results = run_completion(cli, shell=shell, prog_name=prog_name)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)

    if fmt == "json":
        output = format_completion_report_json(results)
    else:
        output = format_completion_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Completion script written to {out_path}")
    else:
        click.echo(output)


if __name__ == "__main__":
    cli()