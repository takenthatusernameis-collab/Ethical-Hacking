"""Command-line interface for ethscan."""

import click

from ethscan import __version__


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """ethscan: ethical hacking toolkit."""


@cli.command()
@click.option("--target", required=True, help="Target host or IP range")
def scan(target: str) -> None:
    """Run a basic port scan against TARGET."""
    click.echo(f"Scanning {target} ... (placeholder)")


if __name__ == "__main__":
    cli()