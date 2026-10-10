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


def test_subdomains_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_subdomains() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "subdomains" in result.output


def test_subdomains_offline_target_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["subdomains", "--target", "nonexistent.invalid.domain.tld", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "nonexistent.invalid.domain.tld" in result.output
    assert "resolved_count" in result.output


def test_subdomains_offline_target_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Subdomain Enumeration Report" in result.output


def test_subdomains_wordlist_option(tmp_path) -> None:
    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "www" in result.output
    assert "mail" in result.output


def test_subdomains_out_option(tmp_path) -> None:
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "nonexistent.invalid.domain.tld" in content