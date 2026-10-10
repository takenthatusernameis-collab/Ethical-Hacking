"""Command-line interface for ethscan."""

import json
from typing import Optional

import click

from ethscan import __version__
from ethscan.passwords import audit_passwords
from ethscan.scanner import get_common_ports, parse_port_range, scan_ports
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
)
from ethscan.brute import (
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


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """ethscan: ethical hacking toolkit."""


@cli.command()
@click.option("--target", required=True, help="Target host or IP address")
@click.option(
    "--ports",
    default="common",
    help="Ports to scan: 'common', 'all', or comma-separated list/ranges (e.g., '80,443,8000-9000')",
)
@click.option("--timeout", default=1.0, type=float, help="Connection timeout in seconds")
@click.option("--workers", default=100, type=int, help="Maximum concurrent workers")
def scan(target: str, ports: str, timeout: float, workers: int) -> None:
    """Run a port scan against TARGET."""
    if ports.lower() == "common":
        port_list = get_common_ports()
    elif ports.lower() == "all":
        port_list = list(range(1, 65536))
    else:
        port_list = parse_port_range(ports)

    click.echo(f"Scanning {target} ({len(port_list)} ports)...")

    results = scan_ports(target, port_list, timeout=timeout, max_workers=workers)

    open_ports = [port for port, is_open in results if is_open]
    if open_ports:
        click.echo(f"Open ports: {', '.join(map(str, open_ports))}")
    else:
        click.echo("No open ports found.")


@cli.command()
@click.option(
    "--file",
    help="Path to a file containing one password per line. If omitted, reads stdin.",
)
def audit(file: str) -> None:
    """Audit passwords for strength and common weaknesses."""
    if file:
        with open(file, "r", encoding="utf-8") as handle:
            passwords = [line.strip() for line in handle if line.strip()]
    else:
        passwords = [line.strip() for line in click.get_text_stream("stdin") if line.strip()]

    if not passwords:
        click.echo("No passwords provided.")
        return

    for password, evaluation in audit_passwords(passwords):
        click.echo(
            f"{password!r}: score={evaluation['score']} "
            f"({evaluation['verdict']}) entropy={evaluation['entropy']} "
            f"common={evaluation['common']} patterns={evaluation['patterns']}"
        )


@cli.command()
@click.option("--target", required=True, help="Target host or IP address for port scan")
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
        target, subdomains=subdomains_list, timeout=timeout, max_workers=workers
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
@click.option("--target", required=True, help="Target domain or IP address")
@click.option(
    "--server",
    default="whois.iana.org",
    help="WHOIS server to query (default: whois.iana.org)",
)
@click.option("--port", default=43, type=int, help="WHOIS server port (default: 43)")
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
def whois(
    target: str,
    server: str,
    port: int,
    timeout: float,
    fmt: str,
    out_path: str,
) -> None:
    """Run a WHOIS lookup for TARGET."""
    results = run_whois(target, server=server, port=port, timeout=timeout)

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
@click.option("--target", required=True, help="Target domain or URL (e.g. example.com or https://example.com)")
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
def service(target: str, ports: Optional[str], timeout: float, workers: int, fmt: str, out_path: Optional[str]) -> None:
    """Detect services and grab banners on open ports (nmap-style)."""
    port_list = None
    if ports:
        from ethscan.scanner import parse_port_range
        port_list = parse_port_range(ports)

    results = run_service(target, ports=port_list, timeout=timeout, max_workers=workers)

    if fmt == "json":
        output = format_service_report_json(results)
    else:
        output = format_service_report_markdown(results)

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
def brute(
    target: str,
    protocol: str,
    port: Optional[int],
    user_file: Optional[str],
    pass_file: Optional[str],
    timeout: float,
    workers: int,
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

    if fmt == "json":
        output = format_brute_report_json(results)
    else:
        output = format_brute_report_markdown(results)

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


if __name__ == "__main__":
    cli()