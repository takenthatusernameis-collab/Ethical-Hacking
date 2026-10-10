"""Command-line interface for ethscan."""

import click

from ethscan import __version__
from ethscan.scanner import get_common_ports, parse_port_range, scan_ports


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


if __name__ == "__main__":
    cli()