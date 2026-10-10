"""Command-line interface for ethscan."""

import json

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