"""Tests for the ethscan CLI."""

from click.testing import CliRunner

from ethscan.cli import cli


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help_lists_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "audit" in result.output
    assert "report" in result.output
    assert "web" in result.output


def test_web_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--checks" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_fuzz_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["fuzz", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_fuzz() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "fuzz" in result.output


def test_web_unknown_check() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["web", "--target", "https://example.com", "--checks", "bogus", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Unknown checks" in result.output