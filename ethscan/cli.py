"""Command-line interface for ethscan."""
from __future__ import annotations

import json
import os
from typing import Any

import click

from ethscan import __version__
from ethscan.brute import (
    format_brute_report_csv,
    format_brute_report_json,
    format_brute_report_markdown,
    run_brute,
)
from ethscan.brute import load_wordlist as load_cred_wordlist
from ethscan.cert import (
    format_cert_report_csv,
    format_cert_report_json,
    format_cert_report_markdown,
    run_cert,
)
from ethscan.cidr import (
    format_cidr_report_csv,
    format_cidr_report_json,
    format_cidr_report_markdown,
    run_cidr,
)
from ethscan.completion import (
    format_completion_report_csv,
    format_completion_report_json,
    format_completion_report_markdown,
    run_completion,
)
from ethscan.config import (
    build_default_map,
    format_config_report_csv,
    load_config,
    validate_config,
)
from ethscan.cve import (
    format_cve_report_csv,
    format_cve_report_json,
    format_cve_report_markdown,
    run_cve,
)
from ethscan.dns import (
    format_dns_report_csv,
    format_dns_report_json,
    format_dns_report_markdown,
    run_dns,
)
from ethscan.dnsbrute import (
    format_dnsbrute_report_csv,
    format_dnsbrute_report_json,
    format_dnsbrute_report_markdown,
    run_dnsbrute,
)
from ethscan.dnssec import (
    format_dnssec_report_csv,
    format_dnssec_report_json,
    format_dnssec_report_markdown,
    run_dnssec,
)
from ethscan.ftp import (
    format_ftp_report_csv,
    format_ftp_report_json,
    format_ftp_report_markdown,
    run_ftp,
)
from ethscan.fuzz import (
    format_fuzz_report_csv,
    format_fuzz_report_json,
    format_fuzz_report_markdown,
    load_wordlist,
    run_fuzz,
)
from ethscan.fuzz import (
    load_wordlist as load_fuzz_wordlist,
)
from ethscan.geo import (
    format_geo_report_csv,
    format_geo_report_json,
    format_geo_report_markdown,
    run_geo,
)
from ethscan.hash import (
    format_check_report_csv,
    format_check_report_json,
    format_check_report_markdown,
    format_hash_report_csv,
    format_hash_report_json,
    format_hash_report_markdown,
    load_passwords_from_file,
    run_check,
    run_hash,
)
from ethscan.headers import (
    format_headers_report_csv,
    format_headers_report_json,
    format_headers_report_markdown,
    run_headers,
)
from ethscan.jwt import (
    format_jwt_report_csv,
    format_jwt_report_json,
    format_jwt_report_markdown,
    run_jwt,
)
from ethscan.ldap import (
    format_ldap_report_csv,
    format_ldap_report_json,
    format_ldap_report_markdown,
    run_ldap,
)
from ethscan.mac import (
    format_mac_report_csv,
    format_mac_report_json,
    format_mac_report_markdown,
    run_mac,
)
from ethscan.memcached import (
    format_memcached_report_csv,
    format_memcached_report_json,
    format_memcached_report_markdown,
    run_memcached,
)
from ethscan.mongodb import (
    format_mongodb_report_csv,
    format_mongodb_report_json,
    format_mongodb_report_markdown,
    run_mongodb,
)
from ethscan.mssql import (
    format_mssql_report_csv,
    format_mssql_report_json,
    format_mssql_report_markdown,
    run_mssql,
)
from ethscan.mysql import (
    format_mysql_report_csv,
    format_mysql_report_json,
    format_mysql_report_markdown,
    run_mysql,
)
from ethscan.netbios import (
    format_netbios_report_csv,
    format_netbios_report_json,
    format_netbios_report_markdown,
    run_netbios,
)
from ethscan.nmap import (
    format_nmap_report_csv,
    format_nmap_report_json,
    format_nmap_report_markdown,
    run_nmap,
)
from ethscan.ntp import (
    format_ntp_report_csv,
    format_ntp_report_json,
    format_ntp_report_markdown,
    run_ntp,
)
from ethscan.oracle import (
    format_oracle_report_csv,
    format_oracle_report_json,
    format_oracle_report_markdown,
    run_oracle,
)
from ethscan.osdetect import (
    format_osdetect_report_csv,
    format_osdetect_report_json,
    format_osdetect_report_markdown,
    run_osdetect,
)
from ethscan.passwords import (
    audit_passwords,
    format_audit_report_csv,
    format_audit_report_json,
    format_audit_report_markdown,
)
from ethscan.ping import (
    format_ping_report_csv,
    format_ping_report_json,
    format_ping_report_markdown,
    run_ping,
)
from ethscan.postgresql import (
    format_postgresql_report_csv,
    format_postgresql_report_json,
    format_postgresql_report_markdown,
    run_postgresql,
)
from ethscan.radix import (
    format_radix_report_csv,
    format_radix_report_json,
    format_radix_report_markdown,
    run_radix,
)
from ethscan.recon import (
    format_recon_report_csv,
    format_recon_report_json,
    format_recon_report_markdown,
    run_recon,
)
from ethscan.redis import (
    DEFAULT_PROBES,
    format_redis_report_csv,
    format_redis_report_json,
    format_redis_report_markdown,
    run_redis,
)
from ethscan.report import (
    format_report_csv,
    format_report_json,
    format_report_markdown,
    run_report,
)
from ethscan.resolve import (
    format_resolve_report_csv,
    format_resolve_report_json,
    format_resolve_report_markdown,
    run_resolve,
)
from ethscan.s3 import (
    format_s3_report_csv,
    format_s3_report_json,
    format_s3_report_markdown,
    run_s3,
)
from ethscan.scanner import (
    format_scan_report_csv,
    format_scan_report_json,
    format_scan_report_markdown,
    get_all_ports,
    get_common_ports,
    get_profile_defaults,
    get_profile_ports,
    parse_port_range,
    scan_ports,
)
from ethscan.service import (
    format_service_report_csv,
    format_service_report_json,
    format_service_report_markdown,
    run_service,
)
from ethscan.smb import (
    format_smb_report_csv,
    format_smb_report_json,
    format_smb_report_markdown,
    run_smb,
)
from ethscan.smtp import (
    format_smtp_report_csv,
    format_smtp_report_json,
    format_smtp_report_markdown,
    run_smtp,
)
from ethscan.snmp import (
    format_snmp_report_csv,
    format_snmp_report_json,
    format_snmp_report_markdown,
    run_snmp,
)
from ethscan.ssh import (
    format_ssh_report_csv,
    format_ssh_report_json,
    format_ssh_report_markdown,
    run_ssh,
)
from ethscan.ssl import (
    format_ssl_report_csv,
    format_ssl_report_json,
    format_ssl_report_markdown,
    run_ssl,
)
from ethscan.stale import (
    DEFAULT_MAX_WORKERS,
    DEFAULT_TIMEOUT,
    format_stale_report_csv,
    format_stale_report_json,
    format_stale_report_markdown,
    load_domains_from_file,
    run_stale,
)
from ethscan.subdomains import (
    format_subdomains_report_csv,
    format_subdomains_report_json,
    format_subdomains_report_markdown,
    load_subdomain_wordlist,
    run_subdomains,
)
from ethscan.subtake import (
    format_subtake_report_csv,
    format_subtake_report_json,
    format_subtake_report_markdown,
    run_subtake,
)
from ethscan.tls import (
    format_tls_report_csv,
    format_tls_report_json,
    format_tls_report_markdown,
    run_tls,
)
from ethscan.trace import (
    format_trace_report_csv,
    format_trace_report_json,
    format_trace_report_markdown,
    run_trace,
)
from ethscan.urlcheck import (
    format_urlcheck_report_csv,
    format_urlcheck_report_json,
    format_urlcheck_report_markdown,
    run_urlcheck,
)
from ethscan.validate import (
    format_validate_report_csv,
    format_validate_report_json,
    format_validate_report_markdown,
    run_validate,
)
from ethscan.vuln import (
    format_vuln_report_csv,
    format_vuln_report_json,
    format_vuln_report_markdown,
    run_vuln,
)
from ethscan.web import (
    format_web_report_csv,
    format_web_report_json,
    format_web_report_markdown,
    run_web_checks,
)
from ethscan.whois import (
    format_whois_report_csv,
    format_whois_report_json,
    format_whois_report_markdown,
    run_whois,
)
from ethscan.wifi import (
    format_wifi_report_csv,
    format_wifi_report_json,
    format_wifi_report_markdown,
    run_wifi,
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
def cli(ctx, config_path: str | None) -> None:
    """ethscan: ethical hacking toolkit."""
    config = load_config(config_path)
    ctx.obj = {"config": config, "config_path": config_path}
    known_commands = sorted(cli.commands.keys())
    for warning in validate_config(config, known_commands=known_commands):
        click.echo(f"Warning: {warning}", err=True)
    default_map: dict[str, dict[str, Any]] = {}
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
@click.option("--workers", default=100, type=click.IntRange(min=1), help="Maximum concurrent workers")
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
def scan(target: str, ports: str, profile: str | None, timeout: float, workers: int, output_fmt: str | None, fmt: str, out_path: str | None) -> None:
    """Run a port scan against TARGET."""
    if profile:
        defaults = get_profile_defaults(profile)
        ports_spec = ports.lower()
        if ports_spec == "common":
            port_list = get_profile_ports(profile)
        elif ports_spec == "all":
            port_list = get_all_ports()
        else:
            port_list = parse_port_range(ports)
        if timeout == 1.0:
            timeout = defaults["timeout"]
        if workers == 100:
            workers = defaults["workers"]
    elif ports.lower() == "common":
        port_list = get_common_ports()
    elif ports.lower() == "all":
        port_list = get_all_ports()
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
    "--min-length",
    "min_length",
    type=int,
    help="Flag passwords shorter than this length as too short.",
)
@click.option(
    "--salt",
    help="Salt prepended to each password before evaluation (for salted password auditing).",
)
@click.option(
    "--pepper",
    help="Pepper used as HMAC key for peppered password evaluation (requires hashlib-backed algorithm).",
)
@click.option(
    "--algorithm",
    type=click.Choice(["md5", "sha1", "sha256", "sha512"], case_sensitive=False),
    default="sha256",
    help="Hash algorithm for salted/peppered evaluation (default: sha256).",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["score", "verdict", "length"]),
    default=None,
    help="Sort audit results by score, verdict, or length.",
)
@click.option(
    "--sort-desc/--sort-asc",
    "sort_desc",
    default=True,
    help="Sort direction: descending (default) or ascending.",
)
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
def audit(
    file: str,
    min_length: int | None,
    salt: str | None,
    pepper: str | None,
    algorithm: str,
    sort_by: str | None,
    sort_desc: bool,
    output_fmt: str | None,
    fmt: str,
    out_path: str,
) -> None:
    """Audit passwords for strength and common weaknesses."""
    if file:
        with open(file, "r", encoding="utf-8") as handle:
            passwords = [line.strip() for line in handle if line.strip()]
    else:
        passwords = [line.strip() for line in click.get_text_stream("stdin") if line.strip()]

    if not passwords:
        click.echo("No passwords provided.")
        return

    results = audit_passwords(
        passwords,
        min_length=min_length,
        sort_by=sort_by,
        sort_desc=sort_desc,
        salt=salt,
        pepper=pepper,
        algorithm=algorithm,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_audit_report_json(
            passwords,
            results,
            min_length=min_length,
            sort_by=sort_by,
            sort_desc=sort_desc,
            salt=salt,
            pepper=pepper,
        )
    elif chosen_format == "markdown":
        output = format_audit_report_markdown(
            passwords,
            results,
            min_length=min_length,
            sort_by=sort_by,
            sort_desc=sort_desc,
            salt=salt,
            pepper=pepper,
        )
    else:
        output = format_audit_report_csv(passwords, results, min_length=min_length, salt=salt, pepper=pepper)

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
@click.option(
    "--profile",
    type=click.Choice(["fast", "normal", "full"]),
    help="Scan profile: fast (top ~18 ports), normal (common ports), full (1-1024 + common). Overrides --ports, --timeout, --workers unless explicitly set.",
)
@click.option("--timeout", default=1.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=100, type=click.IntRange(min=1), help="Maximum concurrent workers")
@click.option(
    "--audit-file",
    "audit_file",
    help="Path to a file containing one password per line for password audit",
)
@click.option(
    "--min-length",
    "min_length",
    type=int,
    default=None,
    help="Flag passwords shorter than this length as too short (passed to the embedded audit).",
)
@click.option(
    "--salt",
    help="Salt prepended to each password before audit evaluation (for salted password auditing).",
)
@click.option(
    "--pepper",
    help="Pepper used as HMAC key for peppered password audit evaluation (requires hashlib-backed algorithm).",
)
@click.option(
    "--algorithm",
    type=click.Choice(["md5", "sha1", "sha256", "sha512"], case_sensitive=False),
    default="sha256",
    help="Hash algorithm for salted/peppered audit evaluation (default: sha256).",
)
@click.option(
    "--open-only/--no-open-only",
    "open_only",
    default=False,
    help="Filter scan results to open ports only (JSON, Markdown, and CSV output).",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["score", "verdict", "length"]),
    default=None,
    help="Sort audit (password) results by score, verdict, or length.",
)
@click.option(
    "--sort-desc/--sort-asc",
    "sort_desc",
    default=True,
    help="Sort direction: descending (default) or ascending.",
)
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
    "--output",
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def report(
    target: str,
    ports: str,
    profile: str | None,
    timeout: float,
    workers: int,
    audit_file: str,
    min_length: int | None,
    salt: str | None,
    pepper: str | None,
    algorithm: str,
    open_only: bool,
    sort_by: str | None,
    sort_desc: bool,
    output_fmt: str | None,
    fmt: str,
    out_path: str,
) -> None:
    """Generate a report combining port scan and password audit results."""
    report_data = run_report(
        target,
        ports,
        timeout=timeout,
        workers=workers,
        audit_file=audit_file,
        min_length=min_length,
        profile=profile,
        open_only=open_only,
        sort_by=sort_by,
        sort_desc=sort_desc,
        salt=salt,
        pepper=pepper,
        algorithm=algorithm,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_report_json(report_data)
    elif chosen_format == "markdown":
        output = format_report_markdown(report_data)
    else:
        output = format_report_csv(report_data)

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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def web(target: str, checks: str, timeout: float, fmt: str, output_fmt: str | None, out_path: str) -> None:
    """Run web application security checks against TARGET."""
    check_list = [c.strip() for c in checks.split(",") if c.strip()]
    valid = {"headers", "info_disclosure", "ssl"}
    unknown = [c for c in check_list if c not in valid]
    if unknown:
        click.echo(f"Unknown checks: {', '.join(unknown)}")
        click.echo(f"Valid checks: {', '.join(sorted(valid))}")
        return

    results = run_web_checks(target, check_list, timeout=timeout)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_web_report_json(results)
    elif chosen_format == "csv":
        output = format_web_report_csv(results)
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
    "--workers",
    default=1,
    type=click.IntRange(min=1),
    help="Number of concurrent workers (default: 1).",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def fuzz(
    target: str,
    wordlist_path: str,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str,
) -> None:
    """Run HTTP fuzzing against TARGET using a wordlist of paths."""
    wordlist = load_wordlist(wordlist_path) if wordlist_path else None

    results = run_fuzz(target, wordlist=wordlist, timeout=timeout, workers=workers)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_fuzz_report_json(results)
    elif chosen_format == "csv":
        output = format_fuzz_report_csv(results)
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
    type=click.IntRange(min=1),
    help="Maximum concurrent DNS resolution workers",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    resolver: str | None,
    recursive: bool,
    max_depth: int,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_subdomains_report_json(results)
    elif chosen_format == "csv":
        output = format_subdomains_report_csv(results)
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
    type=click.IntRange(min=1),
    help="Maximum concurrent DNS resolution workers",
)
@click.option("--http-timeout", default=5.0, type=float, help="HTTP request timeout for fingerprinting in seconds")
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
def subtake(
    target: str,
    wordlist_path: str | None,
    resolver: str | None,
    timeout: float,
    workers: int,
    http_timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_subtake_report_json(results)
    elif chosen_format == "markdown":
        output = format_subtake_report_markdown(results)
    else:
        output = format_subtake_report_csv(results)

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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    output_fmt: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_whois_report_json(results)
    elif chosen_format == "csv":
        output = format_whois_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def headers(target: str, timeout: float, fmt: str, output_fmt: str | None, out_path: str) -> None:
    """Run security headers check against TARGET."""
    results = run_headers(target, timeout=timeout)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_headers_report_json(results)
    elif chosen_format == "csv":
        output = format_headers_report_csv(results)
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
    "--workers",
    default=1,
    type=click.IntRange(min=1),
    help="Number of concurrent workers for parallel record type resolution (default: 1).",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv). Overrides --format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    workers: int,
    output_fmt: str,
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

    results = run_dns(target, record_types=types_list, server=server, timeout=timeout, workers=workers)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_dns_report_json(results)
    elif chosen_format == "markdown":
        output = format_dns_report_markdown(results)
    else:
        output = format_dns_report_csv(results)

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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def resolve(
    target: str,
    record_types: str | None,
    server: str | None,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_resolve_report_json(results)
    elif chosen_format == "csv":
        output = format_resolve_report_csv(results)
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
    type=click.IntRange(min=1),
    help="Maximum concurrent DNS resolution workers",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def dnsbrute(
    target: str,
    nameservers_option: str | None,
    wordlist_path: str | None,
    resolver: str | None,
    recursive: bool,
    max_depth: int,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_dnsbrute_report_json(results)
    elif chosen_format == "csv":
        output = format_dnsbrute_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ssl(target: str, port: int, timeout: float, fmt: str, output_fmt: str | None, out_path: str) -> None:
    """Inspect the SSL/TLS certificate for TARGET."""
    results = run_ssl(target, port=port, timeout=timeout)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_ssl_report_json(results)
    elif chosen_format == "csv":
        output = format_ssl_report_csv(results)
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
@click.option("--workers", default=10, type=click.IntRange(min=1), help="Maximum concurrent probe workers")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    cipher_option: str | None,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_tls_report_json(results)
    elif chosen_format == "csv":
        output = format_tls_report_csv(results)
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
@click.option("--workers", default=50, type=click.IntRange(min=1), help="Maximum concurrent workers")
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
def service(target: str, ports: str | None, profile: str | None, timeout: float, workers: int, output_fmt: str | None, fmt: str, out_path: str | None) -> None:
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
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Enable recursive scanning of hosts discovered in service banners.",
)
@click.option(
    "--max-depth",
    default=2,
    type=int,
    help="Maximum recursion depth for recursive scanning (default: 2).",
)
@click.option(
    "--salt",
    help="Salt prepended to each service banner before vulnerability matching (for salted vulnerability signatures).",
)
@click.option(
    "--pepper",
    help="Pepper used as HMAC key for peppered banner matching (requires hashlib-backed algorithm).",
)
@click.option(
    "--algorithm",
    type=click.Choice(["md5", "sha1", "sha256", "sha512"], case_sensitive=False),
    default="sha256",
    help="Hash algorithm for salted/peppered banner matching (default: sha256).",
)
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=50, type=click.IntRange(min=1), help="Maximum concurrent workers")
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
def vuln(
    target: str,
    ports: str | None,
    services_file: str | None,
    tls_file: str | None,
    ssl_file: str | None,
    severity: str | None,
    min_severity: str | None,
    recursive: bool,
    max_depth: int,
    salt: str | None,
    pepper: str | None,
    algorithm: str,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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
        recursive=recursive,
        max_depth=max_depth,
        salt=salt,
        pepper=pepper,
        algorithm=algorithm,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_vuln_report_json(results)
    elif chosen_format == "markdown":
        output = format_vuln_report_markdown(results)
    else:
        output = format_vuln_report_csv(results)

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
@click.option("--workers", default=10, type=click.IntRange(min=1), help="Maximum concurrent workers for fuzzing")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    wordlist_path: str | None,
    fuzz_paths: bool,
    port: int,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_urlcheck_report_json(results)
    elif chosen_format == "csv":
        output = format_urlcheck_report_csv(results)
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
@click.option("--workers", default=10, type=click.IntRange(min=1), help="Maximum concurrent workers")
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
    port: int | None,
    user_file: str | None,
    pass_file: str | None,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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
@click.option("--workers", default=10, type=click.IntRange(min=1), help="Maximum concurrent probe workers")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def osdetect(
    target: str,
    ports: str | None,
    banners_file: str | None,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_osdetect_report_json(results)
    elif chosen_format == "csv":
        output = format_osdetect_report_csv(results)
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
    "--recursive/--no-recursive",
    default=False,
    help="Recursively trace routes to intermediate hops (default: off)",
)
@click.option(
    "--max-depth",
    default=2,
    type=int,
    help="Maximum recursion depth for recursive tracing (default: 2)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    recursive: bool,
    max_depth: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run TCP traceroute against TARGET using TTL-incremented SYN probes."""
    results = run_trace(
        target,
        port=port,
        max_hops=max_hops,
        timeout=timeout,
        probes_per_hop=probes_per_hop,
        recursive=recursive,
         max_depth=max_depth,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_trace_report_json(results)
    elif chosen_format == "csv":
        output = format_trace_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run ICMP ping (or TCP connect fallback) against TARGET for host discovery."""
    results = run_ping(
        target,
        count=count,
        timeout=timeout,
        ttl=ttl,
         port=tcp_port,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_ping_report_json(results)
    elif chosen_format == "csv":
        output = format_ping_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def wifi(interface: str | None, fmt: str, output_fmt: str | None, out_path: str | None) -> None:
    """Scan for nearby Wi-Fi access points (Linux only)."""
    results = run_wifi(interface=interface)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_wifi_report_json(results)
    elif chosen_format == "csv":
        output = format_wifi_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    api_url: str | None,
    recursive: bool,
    max_depth: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "json":
        output = format_geo_report_json(results)
    elif chosen_format == "csv":
        output = format_geo_report_csv(results)
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
    type=click.IntRange(min=1),
    help="Maximum concurrent workers for subdomain enumeration",
)
@click.option(
    "--resolver",
    help="Custom DNS resolver IP address for subdomains (requires dnspython)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def recon(
    target: str,
    modules: str | None,
    subdomains_wordlist_path: str | None,
    dns_record_types: str,
    dns_server: str | None,
    whois_server: str,
    whois_port: int,
    no_geo_cache: bool,
    no_geo_offline_fallback: bool,
    geo_api_url: str | None,
    trace_port: int,
    trace_max_hops: int,
    trace_probes_per_hop: int,
    timeout: float,
    workers: int,
    resolver: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_recon_report_json(results)
    elif chosen_format == "csv":
        output = format_recon_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    api_url: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Search Certificate Transparency logs for certificates issued to TARGET."""
    results = run_cert(
        target,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_cert_report_json(results)
    elif chosen_format == "csv":
        output = format_cert_report_csv(results)
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
@click.option(
    "--profile",
    type=click.Choice(["fast", "normal", "full"]),
    help="Scan profile for live service detection: fast (top ~18 ports), "
    "normal (common ports), full (1-1024 + common). Overrides --ports, "
    "--service-timeout, --workers unless explicitly set.",
)
@click.option("--timeout", default=10.0, type=float, help="API request timeout in seconds")
@click.option(
    "--service-timeout",
    "service_timeout",
    default=3.0,
    type=float,
    help="Connection timeout in seconds for live service detection (default: 3.0)",
)
@click.option(
    "--workers",
    default=50,
    type=click.IntRange(min=1),
    help="Maximum concurrent workers for live service detection (default: 50)",
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
def cve(
    target: str,
    services_file: str | None,
    ports: str | None,
    profile: str | None,
    timeout: float,
    service_timeout: float,
    workers: int,
    no_cache: bool,
    no_offline_fallback: bool,
    api_url: str | None,
    severity: str | None,
    min_severity: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Query the NVD/CVE API for known vulnerabilities affecting TARGET's services."""
    if services_file:
        try:
            with open(services_file, "r", encoding="utf-8") as handle:
                json.load(handle)
        except json.JSONDecodeError as exc:
            click.echo(f"Failed to read services file: {exc}", err=True)
            return

    port_list = None
    if not services_file:
        if profile:
            defaults = get_profile_defaults(profile)
            if ports:
                from ethscan.scanner import parse_port_range
                port_list = parse_port_range(ports)
            else:
                port_list = get_profile_ports(profile)
            if service_timeout == 3.0:
                service_timeout = defaults["timeout"]
            if workers == 50:
                workers = defaults["workers"]
        elif ports:
            from ethscan.scanner import parse_port_range
            port_list = parse_port_range(ports)

    results = run_cve(
        target,
        services_file=services_file,
        timeout=timeout,
        service_timeout=service_timeout,
        workers=workers,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
        severity=severity,
        min_severity=min_severity,
        ports=port_list,
        profile=profile,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_cve_report_json(results)
    elif chosen_format == "markdown":
        output = format_cve_report_markdown(results)
    else:
        output = format_cve_report_csv(results)

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
    "--diff",
    help="Optional CIDR to compute set difference against (addresses in --cidr but not in --diff).",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def cidr(cidr: str, contains: str | None, diff: str | None, fmt: str, output_fmt: str | None, out_path: str | None) -> None:
    """Compute network calculations for a CIDR (offline)."""
    results = run_cidr(cidr, contains=contains, diff=diff)

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "json":
        output = format_cidr_report_json(results)
    elif chosen_format == "csv":
        output = format_cidr_report_csv(results)
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
    help="Password to hash (repeatable). If omitted, reads from --file or stdin.",
)
@click.option(
    "--file",
    "password_file",
    help="Path to a file containing one password per line. Takes precedence over stdin.",
)
@click.option(
    "--algorithm",
    default=None,
    type=click.Choice(["md5", "sha1", "sha256", "sha512", "ntlm", "md4"]),
    help="Hash algorithm (default: md5). In --check mode, infers from digest length when omitted.",
)
@click.option(
    "--salt",
    "salt",
    default=None,
    help="Optional salt prepended to each password before hashing "
    "(also used in --check mode to recompute a salted digest for comparison).",
)
@click.option(
    "--pepper",
    "pepper",
    default=None,
    help="Optional pepper used as the HMAC key (salt+password is the HMAC "
    "message when --salt is also supplied). Only valid for hashlib-backed "
    "algorithms (md5, sha1, sha256, sha512, md4).",
)
@click.option(
    "--iterations",
    "iterations",
    default=None,
    type=int,
    help="Optional PBKDF2 iteration count (requires --salt). When supplied, "
    "uses PBKDF2-HMAC(algorithm, password, salt, iterations) instead of a "
    "single-pass hash. Must be a positive integer.",
)
@click.option(
    "--check",
    "check_digest",
    help="Compare the plaintext password against this hex digest instead of hashing. "
    "Algorithm is inferred from the digest length when --algorithm is omitted.",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def hash_cmd(passwords, password_file, algorithm, salt, pepper, iterations, check_digest, fmt, output_fmt, out_path) -> None:
    """Generate cryptographic hashes for passwords (MD5, SHA-1, SHA-256, SHA-512, NTLM, MD4)."""
    if iterations is not None and iterations <= 0:
        click.echo("Error: --iterations must be a positive integer.")
        raise click.exceptions.Exit(1)
    if iterations is not None and not salt:
        click.echo("Error: --iterations requires --salt to be supplied.")
        raise click.exceptions.Exit(1)

    password_list = list(passwords)
    if not password_list and password_file:
        password_list = load_passwords_from_file(password_file)
    if not password_list:
        password_list = [line.strip() for line in click.get_text_stream("stdin") if line.strip()]

    if not password_list:
        click.echo("No passwords provided.")
        return

    if check_digest:
        # Check mode: compare the first password against the supplied digest.
        password = password_list[0]
        result = run_check(
            password,
            check_digest,
            algorithm=algorithm,
            salt=salt,
            pepper=pepper,
            iterations=iterations,
        )
        # --output-format takes precedence over the deprecated --format alias
        chosen_format = output_fmt if output_fmt is not None else fmt
        if chosen_format == "json":
            output = format_check_report_json(result)
        elif chosen_format == "csv":
            output = format_check_report_csv(result)
        else:
            output = format_check_report_markdown(result)
    else:
        results = run_hash(
            password_list,
            algorithm=algorithm or "md5",
            salt=salt,
            pepper=pepper,
            iterations=iterations,
        )
        # --output-format takes precedence over the deprecated --format alias
        chosen_format = output_fmt if output_fmt is not None else fmt
        if chosen_format == "json":
            output = format_hash_report_json(results)
        elif chosen_format == "csv":
            output = format_hash_report_csv(results)
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
    "--cidrs",
    "cidrs_option",
    help="Comma-separated list of CIDR networks (e.g. '192.168.1.0/24,10.0.0.0/8,192.168.2.0/23').",
)
@click.option(
    "--cidr-file",
    "cidr_file",
    type=click.Path(exists=True, readable=True),
    help="Path to a file containing CIDR networks (one per line).",
)
@click.option(
    "--diff",
    "diff_option",
    help="Comma-separated list of CIDR networks for set difference (addresses in --cidrs but not in --diff).",
)
@click.option(
    "--no-merge",
    "no_merge",
    is_flag=True,
    help="Disable merging of overlapping/supernettable networks before building the tree.",
)
@click.option(
    "--max-depth",
    default=64,
    type=int,
    help="Maximum recursion depth for the radix tree (default: 64).",
)
@click.option(
    "--contains",
    help="Optional IP address to test for membership in the merged networks.",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def radix(
    cidrs_option: str | None,
    cidr_file: str | None,
    diff_option: str | None,
    no_merge: bool,
    max_depth: int,
    contains: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Build a radix tree visualization over a set of CIDR networks.

    Merges overlapping and adjacent (supernettable) networks and renders
    the resulting aggregate ranges as a hierarchical binary radix tree.
    Fully offline and stdlib-only.

    Use --diff to compute the set difference between two CIDR sets
    (addresses in --cidrs but not in --diff).
    """
    cidrs: list[str] = []

    if cidr_file:
        with open(cidr_file, "r", encoding="utf-8") as f:
            file_cidrs = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            cidrs.extend(file_cidrs)

    if cidrs_option:
        cidrs.extend([c.strip() for c in cidrs_option.split(",") if c.strip()])

    if not cidrs:
        click.echo("Error: at least one CIDR network is required (via --cidrs or --cidr-file).", err=True)
        raise SystemExit(1)

    diff_cidrs = None
    if diff_option is not None:
        diff_cidrs = [c.strip() for c in diff_option.split(",") if c.strip()]

    results = run_radix(
        cidrs,
        merge=not no_merge,
        max_depth=max_depth,
        contains=contains,
        diff=diff_cidrs,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "json":
        output = format_radix_report_json(results)
    elif chosen_format == "csv":
        output = format_radix_report_csv(results)
    else:
        output = format_radix_report_markdown(results)

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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def dnssec(
    target: str,
    server: str | None,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Validate DNSSEC for TARGET domain."""
    results = run_dnssec(
        target,
        server=server,
        timeout=timeout,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_dnssec_report_json(results)
    elif chosen_format == "csv":
        output = format_dnssec_report_csv(results)
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
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
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
    api_url: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Look up MAC address vendor using the OUI database (api.macvendors.com) with caching."""
    results = run_mac(
        target,
        timeout=timeout,
        use_cache=not no_cache,
        offline_fallback=not no_offline_fallback,
        api_url=api_url,
    )

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_mac_report_json(results)
    elif chosen_format == "csv":
        output = format_mac_report_csv(results)
    else:
        output = format_mac_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


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
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Output format for the loaded config (json, markdown, or csv)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
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
    config_path: str | None,
    init_path: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Inspect or initialize the ethscan configuration file."""
    from ethscan.config import dump_default_config

    if init_path:
        sample = dump_default_config()
        try:
            parent_dir = os.path.dirname(os.path.abspath(init_path))
            if parent_dir and not os.path.isdir(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
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

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        payload: dict[str, Any] = {
            "config_file": path,
            "defaults": loaded.get("defaults") or {},
            "commands": loaded.get("commands") or {},
        }
        if isinstance(parse_error, str):
            payload["parse_error"] = parse_error
        output = json.dumps(payload, indent=2, default=str)
    elif chosen_format == "csv":
        output = format_config_report_csv(loaded)
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
    "--token",
    help="JWT token to inspect (e.g. eyJhbGciOiJIUzI1NiJ9...). If omitted, reads from stdin.",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def jwt(token: str | None, fmt: str, output_fmt: str | None, out_path: str | None) -> None:
    """Inspect a JWT (JSON Web Token) without verifying the signature."""
    if token:
        token = token.strip()
    else:
        stdin_text = click.get_text_stream("stdin").read()
        token = stdin_text.strip() if stdin_text else ""

    if not token:
        click.echo("No token provided.")
        return

    results = run_jwt(token)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_jwt_report_json(results)
    elif chosen_format == "csv":
        output = format_jwt_report_csv(results)
    else:
        output = format_jwt_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.argument(
    "shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    default="bash",
    required=False,
    metavar="SHELL",
)
@click.option(
    "--shell",
    "shell_option",
    type=click.Choice(["bash", "zsh", "fish"]),
    default=None,
    help="Shell to generate a completion script for (default: bash). Alias for the positional SHELL argument.",
)
@click.option(
    "--prog-name",
    "prog_name",
    default="ethscan",
    help="Program name embedded in the completion script (default: ethscan).",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def completion(
    shell: str,
    shell_option: str | None,
    prog_name: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Generate a shell completion script for ethscan.

    Supported shells: bash, zsh, fish. Save the output and source it
    in your shell to enable tab completion of commands, options, and
    option values.
    """
    # The --shell option overrides the positional SHELL argument when both are given.
    effective_shell = shell_option if shell_option is not None else shell
    try:
        results = run_completion(cli, shell=effective_shell, prog_name=prog_name)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_completion_report_json(results)
    elif chosen_format == "csv":
        output = format_completion_report_csv(results)
    else:
        output = format_completion_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo("Completion script written")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or memcached:// URL (e.g. memcached://localhost:11211)")
@click.option("--port", default=None, type=int, help="Memcached port (overrides parsed port; default 11211)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="version,stats",
    help="Comma-separated list of probes to run: version, stats (default: version,stats)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def memcached(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run Memcached reconnaissance (version and stats probes)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_memcached(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_memcached_report_json(results)
    elif chosen_format == "csv":
        output = format_memcached_report_csv(results)
    else:
        output = format_memcached_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)




@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or mysql:// URL (e.g. mysql://localhost:3306)")
@click.option("--port", default=None, type=int, help="MySQL port (overrides parsed port; default 3306)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="handshake",
    help="Comma-separated list of probes to run: handshake (default: handshake)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def mysql(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run MySQL reconnaissance (handshake/banner probe)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_mysql(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_mysql_report_json(results)
    elif chosen_format == "csv":
        output = format_mysql_report_csv(results)
    else:
        output = format_mysql_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or mongodb:// URL (e.g. mongodb://localhost:27017)")
@click.option("--port", default=None, type=int, help="MongoDB port (overrides parsed port; default 27017)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="buildInfo",
    help="Comma-separated list of probes to run: buildInfo (default: buildInfo)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def mongodb(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run MongoDB reconnaissance (buildInfo/server info probe)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_mongodb(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_mongodb_report_json(results)
    elif chosen_format == "csv":
        output = format_mongodb_report_csv(results)
    else:
        output = format_mongodb_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or postgresql:// URL (e.g. postgresql://localhost:5432)")
@click.option("--port", default=None, type=int, help="PostgreSQL port (overrides parsed port; default 5432)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="startup",
    help="Comma-separated list of probes to run: startup (default: startup)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def postgresql(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run PostgreSQL reconnaissance (wire-protocol startup probe)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_postgresql(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_postgresql_report_json(results)
    elif chosen_format == "csv":
        output = format_postgresql_report_csv(results)
    else:
        output = format_postgresql_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--ports",
    help="Comma-separated port specifications to validate and expand "
    "(e.g. '80,443,8000-9000').",
)
@click.option(
    "--cidr",
    "cidrs",
    help="Comma-separated CIDR/network specifications to validate "
    "(e.g. '192.168.1.0/24,10.0.0.0/8').",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv). Overrides --format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def validate(
    ports: str | None,
    cidrs: str | None,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Validate and expand port specifications and CIDR inputs (offline)."""
    chosen_format = output_fmt if output_fmt is not None else fmt
    results = run_validate(ports=ports, cidrs=cidrs)

    if chosen_format == "csv":
        output = format_validate_report_csv(results)
    elif chosen_format == "json":
        output = format_validate_report_json(results)
    else:
        output = format_validate_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--input-file",
    "input_file",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to Nmap XML output file (-oX).",
)
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
def nmap(
    input_file: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Parse Nmap XML scan output and cross-reference services against vulnerability database."""
    results = run_nmap(input_file)

    # --output-format takes precedence over the deprecated --format alias
    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_nmap_report_json(results)
    elif chosen_format == "markdown":
        output = format_nmap_report_markdown(results)
    else:
        output = format_nmap_report_csv(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option(
    "--target",
    "targets",
    multiple=True,
    help="Target domain or URL to check for stale DNS records. Can be specified multiple times.",
)
@click.option(
    "--file",
    "target_file",
    type=click.Path(exists=True, readable=True),
    help="Path to a file containing domains (one per line).",
)
@click.option(
    "--timeout",
    default=DEFAULT_TIMEOUT,
    type=float,
    help="DNS resolution and TCP connect timeout in seconds.",
)
@click.option(
    "--workers",
    default=DEFAULT_MAX_WORKERS,
    type=click.IntRange(min=1),
    help="Maximum concurrent workers for resolution.",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv). Overrides --format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def stale(
    targets: tuple,
    target_file: str | None,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Detect stale DNS records (A/AAAA/CNAME) pointing to deallocated or unresolvable IPs."""
    all_targets: list[str] = list(targets)
    if target_file:
        all_targets.extend(load_domains_from_file(target_file))
    if not all_targets:
        click.echo("Error: At least one target must be provided via --target or --file", err=True)
        return

    results = run_stale(all_targets, timeout=timeout, max_workers=workers)

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "csv":
        output = format_stale_report_csv(results)
    elif chosen_format == "json":
        output = format_stale_report_json(results)
    else:
        output = format_stale_report_markdown(results)

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
    help="Target host or URL (e.g. ssh.example.com or ssh://example.com:2222)",
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="Target SSH port (default: 22, or extracted from target)",
)
@click.option("--timeout", default=10.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ssh(target: str, port: int | None, timeout: float, fmt: str, output_fmt: str | None, out_path: str | None) -> None:
    """Assess SSH server security: enumerate algorithms, check for weak/deprecated ciphers, MACs, KEX, and host keys."""
    results = run_ssh(target, port=port, timeout=timeout)

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "json":
        output = format_ssh_report_json(results)
    elif chosen_format == "csv":
        output = format_ssh_report_csv(results)
    else:
        output = format_ssh_report_markdown(results)

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
    help="Path to a wordlist file (one bucket name per line). Uses built-in "
    "default derivations if omitted.",
)
@click.option(
    "--region",
    "region",
    default="us-east-1",
    help="AWS region to probe (e.g. us-east-1). Use 'all' to check every "
    "common S3 region (default: us-east-1).",
)
@click.option(
    "--timeout",
    default=5.0,
    type=float,
    help="HTTP request timeout in seconds (default: 5.0)",
)
@click.option(
    "--workers",
    default=20,
    type=click.IntRange(min=1),
    help="Maximum concurrent HTTP probes (default: 20)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def s3(
    target: str,
    wordlist_path: str | None,
    region: str,
    timeout: float,
    workers: int,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Enumerate AWS S3 buckets for TARGET and detect publicly accessible ones."""
    wordlist = load_subdomain_wordlist(wordlist_path) if wordlist_path else None

    results = run_s3(
        target,
        wordlist=wordlist,
        region=region,
        timeout=timeout,
        max_workers=workers,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt
    if chosen_format == "json":
        output = format_s3_report_json(results)
    elif chosen_format == "csv":
        output = format_s3_report_csv(results)
    else:
        output = format_s3_report_markdown(results)

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
    help="Target SMTP server, host, host:port, or URL (e.g. smtp.example.com or smtp://smtp.example.com:587)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="SMTP port (overrides any port parsed from --target; default 25).",
)
@click.option(
    "--users",
    help="Comma-separated list of usernames to probe via VRFY (user enumeration).",
)
@click.option(
    "--no-starttls-check",
    "check_starttls",
    flag_value=False,
    default=True,
    help="Skip the EHLO/STARTTLS capability check.",
)
@click.option(
    "--no-relay-check",
    "check_relay",
    flag_value=False,
    default=True,
    help="Skip the open-relay probe.",
)
@click.option("--timeout", default=2.0, type=float, help="Per-read timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def smtp(
    target: str,
    port: int | None,
    users: str | None,
    check_starttls: bool,
    check_relay: bool,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run SMTP reconnaissance (banner, STARTTLS, VRFY user enumeration, open relay) for TARGET."""
    users_list = [u.strip() for u in users.split(",") if u.strip()] if users else None
    results = run_smtp(
        target,
        port=port,
        timeout=timeout,
        users=users_list,
        check_starttls=check_starttls,
        check_relay=check_relay,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_smtp_report_json(results)
    elif chosen_format == "csv":
        output = format_smtp_report_csv(results)
    else:
        output = format_smtp_report_markdown(results)

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
    help="Target FTP server, host, host:port, or URL (e.g. ftp.example.com or ftp://ftp.example.com:2121)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="FTP port (overrides any port parsed from --target; default 21).",
)
@click.option(
    "--no-anonymous-check",
    "check_anonymous",
    flag_value=False,
    default=True,
    help="Skip the anonymous-login probe.",
)
@click.option("--timeout", default=3.0, type=float, help="Per-read timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ftp(
    target: str,
    port: int | None,
    check_anonymous: bool,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run FTP reconnaissance (banner grab + anonymous-login check) for TARGET."""
    results = run_ftp(
        target,
        port=port,
        timeout=timeout,
        check_anonymous=check_anonymous,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_ftp_report_json(results)
    elif chosen_format == "csv":
        output = format_ftp_report_csv(results)
    else:
        output = format_ftp_report_markdown(results)

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
    help="Target NTP server, host, host:port, or URL (e.g. ntp.example.com or ntp://ntp.example.com:123)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="NTP port (overrides any port parsed from --target; default 123).",
)
@click.option(
    "--no-monlist-check",
    "check_monlist",
    flag_value=False,
    default=True,
    help="Skip the monlist amplification check.",
)
@click.option("--timeout", default=3.0, type=float, help="Per-request timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ntp(
    target: str,
    port: int | None,
    check_monlist: bool,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run NTP reconnaissance (time response + monlist amplification check) for TARGET."""
    results = run_ntp(
        target,
        port=port,
        timeout=timeout,
        check_monlist=check_monlist,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_ntp_report_json(results)
    elif chosen_format == "csv":
        output = format_ntp_report_csv(results)
    else:
        output = format_ntp_report_markdown(results)

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
    help="Target SNMP device, host, host:port, or URL (e.g. snmp.example.com or snmp://snmp.example.com:161)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="SNMP port (overrides any port parsed from --target; default 161).",
)
@click.option(
    "--communities",
    default=None,
    help="Comma-separated community strings to probe (default: public,private,default,'').",
)
@click.option("--timeout", default=3.0, type=float, help="Per-request timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def snmp(
    target: str,
    port: int | None,
    communities: str | None,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run SNMP reconnaissance (community probing + system info) for TARGET."""
    community_list = None
    if communities is not None:
        community_list = [part.strip() for part in communities.split(",")]

    results = run_snmp(
        target,
        port=port,
        timeout=timeout,
        communities=community_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_snmp_report_json(results)
    elif chosen_format == "csv":
        output = format_snmp_report_csv(results)
    else:
        output = format_snmp_report_markdown(results)

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
    help="Target NetBIOS host, host:port, or URL (e.g. 192.168.1.100 or netbios://192.168.1.100:137)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="NetBIOS Name Service port (overrides any port parsed from --target; default 137).",
)
@click.option(
    "--name",
    default="*",
    help="NetBIOS name to query (default '*' to enumerate all registered names).",
)
@click.option(
    "--suffix",
    default=None,
    type=int,
    help="Service suffix byte (hex or decimal) for the queried name (default 0).",
)
@click.option("--timeout", default=3.0, type=float, help="Per-request timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def netbios(
    target: str,
    port: int | None,
    name: str,
    suffix: int | None,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run NetBIOS (NBNS) NODE STATUS reconnaissance (names, flags, MAC)."""
    if suffix is None:
        suffix_value = 0x00
    else:
        suffix_value = suffix

    results = run_netbios(
        target,
        port=port,
        timeout=timeout,
        name=name,
        suffix=suffix_value,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_netbios_report_json(results)
    elif chosen_format == "csv":
        output = format_netbios_report_csv(results)
    else:
        output = format_netbios_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or smb:// URL (e.g. smb://localhost:445)")
@click.option("--port", default=None, type=int, help="SMB port (overrides parsed port; default 445)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--smb2/--no-smb2",
    "smb2",
    default=False,
    help="Also run an SMB2/SMB3 SMB2_NEGOTIATE probe (reports the negotiated dialect on modern hosts with SMB1 disabled).",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def smb(
    target: str,
    port: int | None,
    timeout: float,
    smb2: bool,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run SMB dialect negotiation reconnaissance (SMB1 and optional SMB2/SMB3)."""
    results = run_smb(
        target,
        port=port,
        timeout=timeout,
        smb2=smb2,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_smb_report_json(results)
    elif chosen_format == "csv":
        output = format_smb_report_csv(results)
    else:
        output = format_smb_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or redis:// URL (e.g. redis://localhost:6379)")
@click.option("--port", default=None, type=int, help="Redis port (overrides parsed port; default 6379)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default=",".join(DEFAULT_PROBES),
    help="Comma-separated list of probes to run: ping, info, config (default: ping,info,config)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def redis(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run Redis reconnaissance (ping, info, config)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else list(DEFAULT_PROBES)
    results = run_redis(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_redis_report_json(results)
    elif chosen_format == "csv":
        output = format_redis_report_csv(results)
    else:
        output = format_redis_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or ldap:// URL (e.g. ldap://localhost:389)")
@click.option("--port", default=None, type=int, help="LDAP port (overrides parsed port; default 389)")
@click.option(
    "--ldap-version",
    "ldap_version",
    type=click.Choice(["2", "3"]),
    default="3",
    show_default=True,
    help="LDAP protocol version used for the anonymous bind probe.",
)
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def ldap(
    target: str,
    port: int | None,
    ldap_version: str,
    timeout: float,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run LDAP anonymous bind and RootDSE reconnaissance."""
    results = run_ldap(
        target,
        port=port,
        timeout=timeout,
        ldap_version=int(ldap_version),
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_ldap_report_json(results)
    elif chosen_format == "csv":
        output = format_ldap_report_csv(results)
    else:
        output = format_ldap_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or mssql:// URL (e.g. mssql://localhost:1433)")
@click.option("--port", default=None, type=int, help="MSSQL port (overrides parsed port; default 1433)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="prelogin",
    help="Comma-separated list of probes to run: prelogin (default: prelogin)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv). Overrides --format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def mssql(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run MSSQL reconnaissance (TDS prelogin probe)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_mssql(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_mssql_report_json(results)
    elif chosen_format == "csv":
        output = format_mssql_report_csv(results)
    else:
        output = format_mssql_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


@cli.command()
@click.option("--target", required=True, help="Target host, host:port, or oracle:// URL (e.g. oracle://localhost:1521)")
@click.option("--port", default=None, type=int, help="Oracle port (overrides parsed port; default 1521)")
@click.option("--timeout", default=3.0, type=float, help="Connection timeout in seconds")
@click.option(
    "--probes",
    default="version",
    help="Comma-separated list of probes to run: version (default: version)",
)
@click.option(
    "--output-format",
    "output_fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default=None,
    help="Output format (json, markdown, or csv). Overrides --format.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "csv"]),
    default="json",
    show_default=True,
    help="Output format (json, markdown, or csv) [deprecated; use --output-format].",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(writable=True),
    help="Output file path (default: stdout)",
)
def oracle(
    target: str,
    port: int | None,
    timeout: float,
    probes: str,
    fmt: str,
    output_fmt: str | None,
    out_path: str | None,
) -> None:
    """Run Oracle reconnaissance (TNS connect probe)."""
    probe_list = [p.strip().lower() for p in probes.split(",") if p.strip()] if probes else None
    results = run_oracle(
        target,
        port=port,
        timeout=timeout,
        probes=probe_list,
    )

    chosen_format = output_fmt if output_fmt is not None else fmt

    if chosen_format == "json":
        output = format_oracle_report_json(results)
    elif chosen_format == "csv":
        output = format_oracle_report_csv(results)
    else:
        output = format_oracle_report_markdown(results)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(output)


if __name__ == "__main__":
    cli()
