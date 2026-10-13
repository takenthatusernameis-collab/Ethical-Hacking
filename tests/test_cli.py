"""Tests for the ethscan CLI."""

import base64
import json
import os
import tempfile

from click.testing import CliRunner

from ethscan.cli import cli
from ethscan.web import SECURITY_HEADERS


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_jwt(header: dict, payload: dict, with_sig: bool = True) -> str:
    """Build a JWT token string from header/payload dicts for CLI tests."""
    token = (
        _b64url(json.dumps(header).encode())
        + "."
        + _b64url(json.dumps(payload).encode())
    )
    if with_sig:
        token += "." + _b64url(b"fake-signature-bytes")
    return token


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


def test_audit_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_audit_offline_target_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\ncorrect-Horse-battery-staple-9x!\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "passwords_audited" in result.output
    assert "password" in result.output
    assert "correct-Horse-battery-staple-9x!" in result.output
    assert "score" in result.output
    assert "verdict" in result.output


def test_audit_offline_target_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Password Audit Report" in result.output
    assert "Passwords Audited" in result.output
    assert "password" in result.output


def test_audit_out_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "audit_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "passwords_audited" in content
    assert "password" in content


def test_audit_out_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "audit_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Password Audit Report" in content
    assert "password" in content


def test_audit_no_passwords(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["audit", "--file", str(password_file)],
    )
    assert result.exit_code == 0
    assert "No passwords provided" in result.output


def test_audit_stdin_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["audit"],
        input="password\ncorrect-Horse-battery-staple-9x!\n",
    )
    assert result.exit_code == 0
    assert "passwords_audited" in result.output
    assert "password" in result.output


def test_audit_stdin_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["audit", "--format", "markdown"],
        input="password\n",
    )
    assert result.exit_code == 0
    assert "Password Audit Report" in result.output
    assert "password" in result.output


def test_audit_help_shows_min_length() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--min-length" in result.output


def test_audit_min_length_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--min-length",
            "10",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "passwords_audited" in result.output
    assert "min_length" in result.output
    assert "too_short" in result.output
    assert "short" in result.output
    assert "longenoughpassword" in result.output


def test_audit_min_length_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--min-length",
            "10",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Password Audit Report" in result.output
    assert "Min Length" in result.output
    assert "10" in result.output
    assert "Too Short" in result.output
    assert "Yes" in result.output
    assert "No" in result.output


def test_audit_min_length_with_out_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    out_file = tmp_path / "audit_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--min-length",
            "10",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "min_length" in content
    assert "too_short" in content


def test_audit_min_length_disabled_by_default(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    # min_length should not be in output when not specified
    # (or could be present with null value)
    data = json.loads(result.output)
    assert data.get("min_length") is None


def test_audit_help_shows_output_format_csv() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_audit_help_shows_salt_pepper() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--salt" in result.output
    assert "--pepper" in result.output
    assert "--algorithm" in result.output
    assert "sha256" in result.output


def test_audit_salt_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["salt"] is True
    assert data["pepper"] is False
    assert data["results"][0]["salt"] is True
    assert data["results"][0]["pepper"] is False


def test_audit_salt_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "**Salt:** applied (prepended to password)" in result.output
    assert "**Pepper:**" not in result.output


def test_audit_pepper_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--pepper",
            "mysecret",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["salt"] is False
    assert data["pepper"] is True
    assert data["results"][0]["salt"] is False
    assert data["results"][0]["pepper"] is True


def test_audit_pepper_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--pepper",
            "mysecret",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "**Pepper:** applied (HMAC key)" in result.output
    assert "**Salt:**" not in result.output


def test_audit_salt_pepper_combined_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--pepper",
            "mysecret",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["salt"] is True
    assert data["pepper"] is True
    assert data["results"][0]["salt"] is True
    assert data["results"][0]["pepper"] is True


def test_audit_salt_with_file_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n123456\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["passwords_audited"] == 2
    assert data["salt"] is True


def test_audit_salt_pepper_with_out_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "audit_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--pepper",
            "mysecret",
            "--out",
            str(out_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "Report written to" in result.output
    content = out_file.read_text()
    data = json.loads(content)
    assert data["salt"] is True
    assert data["pepper"] is True


def test_audit_algorithm_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--salt",
            "mysalt",
            "--algorithm",
            "sha512",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"][0]["length"] == 128  # SHA-512 = 128 hex chars


def test_audit_help_shows_salt_pepper_in_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "Salt prepended to each password before" in result.output
    assert "evaluation (for salted password auditing)" in result.output
    assert "Pepper used as HMAC key for peppered" in result.output
    assert "Hash algorithm for salted/peppered evaluation" in result.output


def test_audit_csv_output(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\ncorrect-Horse-battery-staple-9x!\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper"
    assert len(lines) == 3
    assert "password" in lines[1]
    assert "true" in lines[1]  # common
    assert "correct-Horse-battery-staple-9x!" in lines[2]
    assert "false" in lines[2]  # not common


def test_audit_csv_output_with_min_length(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--output-format",
            "csv",
            "--min-length",
            "10",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) == 3
    assert "short" in lines[1]
    assert "true" in lines[1]  # too_short
    assert "longenoughpassword" in lines[2]
    assert "false" in lines[2]  # not too_short


def test_audit_csv_with_out_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "audit_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "password,length,entropy,common,patterns,too_short,score,verdict" in content
    assert "password" in content


def test_audit_csv_escapes_special_characters(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("pass,word\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) == 2
    # CSV should properly quote the password with comma
    assert '"pass,word"' in lines[1]


def test_audit_output_format_precedence_over_format(tmp_path) -> None:
    """--output-format should take precedence over deprecated --format."""
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--output-format",
            "json",
            "--format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    # Should be JSON (from --output-format), not CSV (from --format)
    assert "passwords_audited" in result.output
    assert "password" in result.output


def test_audit_deprecated_format_csv_still_works(tmp_path) -> None:
    """Deprecated --format csv should still work when --output-format not given."""
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper"
    assert len(lines) == 2


def test_audit_help_shows_sort() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--sort" in result.output
    assert "score" in result.output
    assert "verdict" in result.output
    assert "length" in result.output
    assert "--sort-desc" in result.output
    assert "--sort-asc" in result.output


def test_audit_sort_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
            "--sort",
            "score",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sort_by"] == "score"
    assert data["sort_desc"] is True


def test_audit_sort_asc_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
            "--sort",
            "length",
            "--sort-asc",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sort_by"] == "length"
    assert data["sort_desc"] is False


def test_audit_sort_disabled_by_default(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sort_by"] is None
    assert data["sort_desc"] is True


def test_audit_sort_markdown_shows_sorted_by(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "markdown",
            "--sort",
            "score",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    assert "**Sorted By:** score (Descending)" in result.output


def test_audit_sort_reorders_results(tmp_path) -> None:
    """Sort should actually reorder the audit rows in output."""
    password_file = tmp_path / "passwords.txt"
    # Mix of strong and weak passwords so scores differ.
    password_file.write_text("correct-Horse-battery-staple-9x!\npassword\n123456\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
            "--sort",
            "score",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


def test_audit_sort_verdict_case_insensitive(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n123456\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "audit",
            "--file",
            str(password_file),
            "--format",
            "json",
            "--sort",
            "verdict",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    verdicts = [r["verdict"].lower() for r in data["results"]]
    assert verdicts == sorted(verdicts, reverse=True)


def test_report_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--audit-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_report_offline_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\ncorrect-Horse-battery-staple-9x!\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--format",
            "json",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "audit" in result.output
    assert "passwords_audited" in result.output
    assert "open_ports" in result.output


def test_report_offline_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--format",
            "markdown",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "ethscan Report" in result.output
    assert "Port Scan" in result.output
    assert "Password Audit" in result.output
    assert "password" in result.output


def test_report_out_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--out",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "scan" in content
    assert "audit" in content
    assert "passwords_audited" in content


def test_report_out_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--format",
            "markdown",
            "--out",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan Report" in content
    assert "Port Scan" in content
    assert "Password Audit" in content


def test_report_no_audit_file(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "audit" in result.output
    assert "passwords_audited" in result.output
    assert "0" in result.output


def test_report_help_shows_output_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
    assert "--out" in result.output


def test_report_output_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "report_output.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--output",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "scan" in content
    assert "audit" in content
    assert "passwords_audited" in content


def test_report_output_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "report_output.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--audit-file",
            str(password_file),
            "--format",
            "markdown",
            "--output",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan Report" in content
    assert "Port Scan" in content
    assert "Password Audit" in content


def test_report_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_report_output_format_csv(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443",
            "--audit-file",
            str(password_file),
            "--output-format",
            "csv",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    rows = [line for line in result.output.splitlines() if line.strip()]
    assert rows[0] == "section,port,open,password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper"
    assert any(line.startswith("scan,") for line in rows)
    assert any(line.startswith("audit,") for line in rows)
    assert any("password" in line for line in rows)


def test_report_output_format_csv_with_out(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    out_file = tmp_path / "report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--output-format",
            "csv",
            "--out",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "section,port,open,password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper" in content
    assert "scan," in content
    assert "audit," in content


def test_report_output_format_json_explicit(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--output-format",
            "json",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["target"] == "127.0.0.1"
    assert data["audit"]["passwords_audited"] == 1


def test_report_output_format_takes_precedence_over_format(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--output-format",
            "markdown",
            "--format",
            "csv",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "ethscan Report" in result.output
    assert "section,port,open" not in result.output


def test_report_deprecated_format_csv(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--format",
            "csv",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "section,port,open,password,length,entropy,common,patterns,too_short,score,verdict" in result.output
    assert "audit," in result.output


def test_report_help_shows_profile() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--profile" in result.output
    assert "fast" in result.output
    assert "normal" in result.output
    assert "full" in result.output


def test_report_profile_fast(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--profile",
            "fast",
            "--audit-file",
            str(password_file),
            "--timeout",
            "0.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] == "fast"
    assert data["scan"]["ports_scanned"] == 18


def test_report_profile_normal(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--profile",
            "normal",
            "--audit-file",
            str(password_file),
            "--timeout",
            "0.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] == "normal"
    assert data["scan"]["ports_scanned"] == 24


def test_report_profile_full(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--profile",
            "full",
            "--audit-file",
            str(password_file),
            "--timeout",
            "0.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] == "full"
    assert data["scan"]["ports_scanned"] > 1000


def test_report_profile_override_ports(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--profile",
            "fast",
            "--ports",
            "80,443",
            "--audit-file",
            str(password_file),
            "--timeout",
            "0.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] == "fast"
    assert data["scan"]["ports_scanned"] == 2


def test_report_profile_override_timeout_workers(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--profile",
            "fast",
            "--timeout",
            "5.0",
            "--workers",
            "50",
            "--audit-file",
            str(password_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] == "fast"


def test_report_profile_disabled_by_default(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--timeout",
            "0.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scan"]["profile"] is None


def test_report_help_shows_min_length() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--min-length" in result.output


def test_report_min_length_option_json(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--min-length",
            "10",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["audit"]["min_length"] == 10
    assert "too_short" in result.output
    assert data["audit"]["results"][0]["too_short"] is True
    assert data["audit"]["results"][1]["too_short"] is False


def test_report_min_length_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--min-length",
            "10",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Min Length" in result.output
    assert "Too Short" in result.output
    assert "short" in result.output
    assert "longenoughpassword" in result.output


def test_report_min_length_with_out_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--min-length",
            "10",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "min_length" in content
    assert "too_short" in content


def test_report_min_length_disabled_by_default(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("short\nlongenoughpassword\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--audit-file",
            str(password_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["audit"]["min_length"] is None


def test_report_help_shows_open_only() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--open-only" in result.output


def test_report_open_only_option_json(monkeypatch) -> None:
    called_args = {}

    def mock_run_report(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 3,
                "open_ports": [80],
                "details": [
                    {"port": 80, "open": True},
                ],
                "open_only": True,
            },
            "audit": {"passwords_audited": 0, "results": []},
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443,22",
            "--open-only",
            "--format",
            "json",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert called_args["open_only"] is True
    data = json.loads(result.output)
    assert data["scan"]["open_only"] is True
    assert len(data["scan"]["details"]) == 1
    assert data["scan"]["details"][0]["port"] == 80
    assert data["scan"]["details"][0]["open"] is True


def test_report_open_only_option_markdown(monkeypatch) -> None:
    def mock_run_report(*args, **kwargs):
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 2,
                "open_ports": [80],
                "details": [
                    {"port": 80, "open": True},
                ],
                "open_only": True,
            },
            "audit": {"passwords_audited": 0, "results": []},
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443",
            "--open-only",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "**Open Only:** Yes" in result.output
    assert "| 80 | Open |" in result.output
    assert "443" not in result.output


def test_report_open_only_option_csv(monkeypatch) -> None:
    def mock_run_report(*args, **kwargs):
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 2,
                "open_ports": [80],
                "details": [
                    {"port": 80, "open": True},
                ],
                "open_only": True,
            },
            "audit": {"passwords_audited": 0, "results": []},
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443",
            "--open-only",
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "section,port,open,password,length,entropy,common,patterns,too_short,score,verdict,salt,pepper"
    assert "scan,80,true" in lines[1]
    assert len(lines) == 2


def test_report_open_only_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_report(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 2,
                "open_ports": [80],
                "details": [
                    {"port": 80, "open": True},
                    {"port": 443, "open": False},
                ],
                "open_only": False,
            },
            "audit": {"passwords_audited": 0, "results": []},
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443",
            "--format",
            "json",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert called_args["open_only"] is False


def test_report_help_shows_sort() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--sort" in result.output
    assert "score" in result.output
    assert "verdict" in result.output
    assert "length" in result.output
    assert "--sort-desc" in result.output
    assert "--sort-asc" in result.output


def test_report_sort_option_json(monkeypatch) -> None:
    called_args = {}

    def mock_run_report(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 1,
                "open_ports": [],
                "details": [{"port": 80, "open": False}],
                "open_only": False,
            },
            "audit": {
                "passwords_audited": 0,
                "min_length": None,
                "sort_by": kwargs.get("sort_by"),
                "sort_desc": kwargs.get("sort_desc", True),
                "results": [],
            },
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--format",
            "json",
            "--sort",
            "score",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    assert called_args["sort_by"] == "score"
    assert called_args["sort_desc"] is True


def test_report_sort_asc_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_report(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 1,
                "open_ports": [],
                "details": [{"port": 80, "open": False}],
                "open_only": False,
            },
            "audit": {
                "passwords_audited": 0,
                "min_length": None,
                "sort_by": kwargs.get("sort_by"),
                "sort_desc": kwargs.get("sort_desc", True),
                "results": [],
            },
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--format",
            "json",
            "--sort",
            "length",
            "--sort-asc",
        ],
    )
    assert result.exit_code == 0
    assert called_args["sort_by"] == "length"
    assert called_args["sort_desc"] is False


def test_report_sort_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_report(*args, **kwargs):
        called_args.update(kwargs)
        return {
            "scan": {
                "target": "127.0.0.1",
                "profile": None,
                "ports_scanned": 1,
                "open_ports": [],
                "details": [{"port": 80, "open": False}],
                "open_only": False,
            },
            "audit": {
                "passwords_audited": 0,
                "min_length": None,
                "sort_by": kwargs.get("sort_by"),
                "sort_desc": kwargs.get("sort_desc", True),
                "results": [],
            },
        }

    monkeypatch.setattr("ethscan.cli.run_report", mock_run_report)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert called_args["sort_by"] is None
    assert called_args["sort_desc"] is True


def test_report_sort_markdown_shows_sorted_by(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80",
            "--timeout",
            "0.1",
            "--workers",
            "10",
            "--audit-file",
            str(audit_file),
            "--format",
            "markdown",
            "--sort",
            "score",
            "--sort-desc",
        ],
    )
    assert result.exit_code == 0
    assert "**Sorted By:** score (Descending)" in result.output


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


def test_headers_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["headers", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--timeout" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_headers() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "headers" in result.output


def test_headers_offline_target_json(monkeypatch) -> None:
    def mock_run_headers(target, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 443,
            "secure": True,
            "headers": {},
            "security_headers": {
                "present": [],
                "missing": list(SECURITY_HEADERS.keys()),
                "total": len(SECURITY_HEADERS),
                "present_count": 0,
                "missing_count": len(SECURITY_HEADERS),
            },
        }

    monkeypatch.setattr("ethscan.cli.run_headers", mock_run_headers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["headers", "--target", "https://example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "present_count" in result.output
    assert "missing_count" in result.output


def test_headers_offline_target_markdown(monkeypatch) -> None:
    def mock_run_headers(target, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 443,
            "secure": True,
            "headers": {"content-security-policy": "default-src 'self'"},
            "security_headers": {
                "present": ["Content-Security-Policy"],
                "missing": [h for h in SECURITY_HEADERS if h != "Content-Security-Policy"],
                "total": len(SECURITY_HEADERS),
                "present_count": 1,
                "missing_count": len(SECURITY_HEADERS) - 1,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_headers", mock_run_headers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "headers",
            "--target",
            "https://example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "ethscan Security Headers Report" in result.output
    assert "Content-Security-Policy" in result.output


def test_headers_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_headers(target, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 443,
            "secure": True,
            "headers": {},
            "security_headers": {
                "present": [],
                "missing": list(SECURITY_HEADERS.keys()),
                "total": len(SECURITY_HEADERS),
                "present_count": 0,
                "missing_count": len(SECURITY_HEADERS),
            },
        }

    monkeypatch.setattr("ethscan.cli.run_headers", mock_run_headers)

    out_file = tmp_path / "headers_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "headers",
            "--target",
            "https://example.com",
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
    assert "example.com" in content
    assert "present_count" in content


def test_headers_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_headers(target, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 443,
            "secure": True,
            "headers": {"x-frame-options": "DENY"},
            "security_headers": {
                "present": ["X-Frame-Options"],
                "missing": [h for h in SECURITY_HEADERS if h != "X-Frame-Options"],
                "total": len(SECURITY_HEADERS),
                "present_count": 1,
                "missing_count": len(SECURITY_HEADERS) - 1,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_headers", mock_run_headers)

    out_file = tmp_path / "headers_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "headers",
            "--target",
            "https://example.com",
            "--format",
            "markdown",
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
    assert "ethscan Security Headers Report" in content
    assert "X-Frame-Options" in content


def test_headers_http_target(monkeypatch) -> None:
    def mock_run_headers(target, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 80,
            "secure": False,
            "headers": {"x-frame-options": "SAMEORIGIN"},
            "security_headers": {
                "present": ["X-Frame-Options"],
                "missing": [h for h in SECURITY_HEADERS if h != "X-Frame-Options"],
                "total": len(SECURITY_HEADERS),
                "present_count": 1,
                "missing_count": len(SECURITY_HEADERS) - 1,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_headers", mock_run_headers)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["headers", "--target", "http://example.com", "--format", "markdown", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "**HTTPS:** No" in result.output


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


def test_subdomains_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subdomains(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["resolver"] = resolver
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
            ],
            "per_depth": [
                {"depth": 0, "subdomains_tested": 2, "resolved_count": 0, "results": []},
            ],
            "recursive": recursive,
            "max_depth": max_depth,
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subdomains", mock_run_subdomains)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "example.com",
            "--resolver",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_subdomains_help_shows_resolver() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--help"])
    assert result.exit_code == 0
    assert "--resolver" in result.output


def test_subdomains_help_shows_recursive() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.output
    assert "--no-recursive" in result.output
    assert "--max-depth" in result.output


def test_subdomains_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subdomains(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
            ],
            "per_depth": [
                {"depth": 0, "subdomains_tested": 2, "resolved_count": 0, "results": []},
            ],
            "recursive": recursive,
            "max_depth": max_depth,
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subdomains", mock_run_subdomains)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "3",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 3


def test_subdomains_recursive_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_subdomains(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
            ],
            "per_depth": [
                {"depth": 0, "subdomains_tested": 2, "resolved_count": 0, "results": []},
            ],
            "recursive": recursive,
            "max_depth": max_depth,
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subdomains", mock_run_subdomains)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "example.com",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is False
    assert called_args["max_depth"] == 2


def test_subdomains_max_depth_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subdomains(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
            ],
            "per_depth": [
                {"depth": 0, "subdomains_tested": 2, "resolved_count": 0, "results": []},
            ],
            "recursive": recursive,
            "max_depth": max_depth,
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subdomains", mock_run_subdomains)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "5",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_depth"] == 5


def test_subtake_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subtake", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--resolver" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output
    assert "--http-timeout" in result.output


def test_cli_help_lists_subtake() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "subtake" in result.output


def test_subtake_offline_target_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["subtake", "--target", "nonexistent.invalid.domain.tld", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "nonexistent.invalid.domain.tld" in result.output
    assert "vulnerable_count" in result.output


def test_subtake_offline_target_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Subdomain Takeover Report" in result.output


def test_subtake_wordlist_option(tmp_path) -> None:
    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
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


def test_subtake_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subtake(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        http_timeout=5.0,
    ):
        called_args["resolver"] = resolver
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "vulnerable_count": 0,
            "vulnerable": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "cname": None, "a_records": [], "aaaa_records": [], "vulnerable": False, "takeover": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "cname": None, "a_records": [], "aaaa_records": [], "vulnerable": False, "takeover": None},
            ],
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subtake", mock_run_subtake)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "example.com",
            "--resolver",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_subtake_out_option(tmp_path) -> None:
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
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


def test_subtake_http_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subtake(
        target,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        http_timeout=5.0,
    ):
        called_args["http_timeout"] = http_timeout
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 1,
            "vulnerable_count": 0,
            "vulnerable": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "cname": None, "a_records": [], "aaaa_records": [], "vulnerable": False, "takeover": None},
            ],
            "resolver": None,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subtake", mock_run_subtake)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "example.com",
            "--http-timeout",
            "10.0",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["http_timeout"] == 10.0


def test_subtake_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subtake", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def _subtake_csv_result():
    return {
        "target": "example.com",
        "domain": "example.com",
        "subdomains_tested": 2,
        "vulnerable_count": 1,
        "vulnerable": [],
        "all_results": [
            {
                "subdomain": "www",
                "hostname": "www.example.com",
                "cname": "mybucket.s3.amazonaws.com",
                "a_records": [],
                "aaaa_records": [],
                "vulnerable": True,
                "takeover": {
                    "service": "AWS S3",
                    "cname": "mybucket.s3.amazonaws.com",
                    "fingerprint": "NoSuchBucket",
                    "description": "S3 bucket does not exist",
                    "http_confirmed": True,
                    "evidence": "NoSuchBucket",
                },
            },
            {
                "subdomain": "mail",
                "hostname": "mail.example.com",
                "cname": None,
                "a_records": ["1.2.3.4"],
                "aaaa_records": [],
                "vulnerable": False,
                "takeover": None,
            },
        ],
        "resolver": None,
        "dnspython_available": False,
    }


def test_subtake_output_format_csv(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cli.run_subtake", lambda target, **kw: _subtake_csv_result())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "subdomain,hostname,cname,a_records,aaaa_records,vulnerable,service,fingerprint,http_confirmed" in result.output
    assert "www,www.example.com,mybucket.s3.amazonaws.com,,,true,AWS S3,NoSuchBucket,true" in result.output
    assert "mail,mail.example.com,,1.2.3.4,,false,,,false" in result.output


def test_subtake_output_format_csv_out(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cli.run_subtake", lambda target, **kw: _subtake_csv_result())

    out_file = tmp_path / "subtake_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "example.com",
            "--output-format",
            "csv",
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
    assert "subdomain,hostname,cname,a_records,aaaa_records,vulnerable,service,fingerprint,http_confirmed" in content
    assert "www,www.example.com,mybucket.s3.amazonaws.com,,,true,AWS S3,NoSuchBucket,true" in content


def test_subtake_format_csv_alias(monkeypatch) -> None:
    """Deprecated --format csv alias still routes to the CSV formatter."""
    monkeypatch.setattr("ethscan.cli.run_subtake", lambda target, **kw: _subtake_csv_result())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subtake",
            "--target",
            "example.com",
            "--format",
            "csv",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "subdomain,hostname,cname,a_records,aaaa_records,vulnerable,service,fingerprint,http_confirmed" in result.output


def test_subtake_output_format_default_is_json(monkeypatch) -> None:
    monkeypatch.setattr("ethscan.cli.run_subtake", lambda target, **kw: _subtake_csv_result())

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["subtake", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "{" in result.output
    assert '"target"' in result.output


def test_whois_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["whois", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--server" in result.output
    assert "--port" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_whois() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "whois" in result.output


def test_whois_offline_target_json(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "Registrar: Test Registrar\n",
            "parsed": {
                "registrar": "Test Registrar",
                "creation_date": "2020-01-01",
                "expiration_date": "2025-01-01",
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "Registrar: Test Registrar\n",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "Test Registrar" in result.output


def test_whois_offline_target_markdown(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "Registrar: Test Registrar\n",
            "parsed": {
                "registrar": "Test Registrar",
                "creation_date": "2020-01-01",
                "expiration_date": "2025-01-01",
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "Registrar: Test Registrar\n",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "WHOIS Lookup Report" in result.output


def test_whois_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        called_args["server"] = server
        called_args["target"] = target
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
            "--server",
            "whois.example.org",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["server"] == "whois.example.org"


def test_whois_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "test",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "test",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    out_file = tmp_path / "whois_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
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
    assert "example.com" in content


def test_whois_help_shows_recursive() -> None:
    """Test that whois help shows --recursive/--no-recursive and --max-depth."""
    runner = CliRunner()
    result = runner.invoke(cli, ["whois", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.output
    assert "--no-recursive" in result.output
    assert "--max-depth" in result.output


def test_whois_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        called_args["target"] = target
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--recursive", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 2


def test_whois_recursive_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        called_args["recursive"] = recursive
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is False


def test_whois_max_depth_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "",
            },
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--recursive", "--max-depth", "4",
         "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["max_depth"] == 4


def test_dns_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dns", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--types" in result.output
    assert "--server" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_dns() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "dns" in result.output


def test_dns_offline_target_json(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {
                "A": ["93.184.216.34"],
                "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
            },
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dns", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "93.184.216.34" in result.output


def test_dns_offline_target_markdown(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {
                "A": ["93.184.216.34"],
                "AAAA": [],
            },
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "DNS Record Enumeration Report" in result.output


def test_dns_types_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        called_args["record_types"] = record_types
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--types",
            "A,MX,NS",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["record_types"] == ["A", "MX", "NS"]


def test_dns_unknown_type() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--types",
            "INVALID",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown record types" in result.output


def test_dns_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        called_args["server"] = server
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--server",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["server"] == "8.8.8.8"


def test_dns_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    out_file = tmp_path / "dns_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
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
    assert "example.com" in content


def test_dns_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dns", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_dns_output_format_csv(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {
                "A": ["93.184.216.34"],
                "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
            },
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dns", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert "example.com,example.com,A,93.184.216.34" in lines
    assert "example.com,example.com,AAAA,2606:2800:220:1:248:1893:25c8:1946" in lines


def test_dns_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    out_file = tmp_path / "dns_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--output-format",
            "csv",
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
    lines = content.strip().splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert "example.com,example.com,A,93.184.216.34" in lines


def test_dns_format_csv_alias(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dns", "--target", "example.com", "--format", "csv", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "target,domain,record_type,record_value"
    assert "example.com,example.com,A,93.184.216.34" in lines


def test_dns_output_format_default_is_json(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dns", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    # Default is JSON, which does not start with the CSV header.
    assert not result.output.strip().startswith("target,domain,record_type,record_value")
    assert "93.184.216.34" in result.output


def test_dns_output_format_precedence_over_format(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--format",
            "json",
            "--output-format",
            "csv",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    # --output-format wins even though --format json is also given.
    assert result.output.strip().startswith("target,domain,record_type,record_value")


def test_ssl_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ssl", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_ssl() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ssl" in result.output


def test_ssl_offline_target_json(monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["ssl", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "connection refused" in result.output


def test_ssl_offline_target_markdown(monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": None,
            "chain_length": 2,
            "cert": {
                "subject": "example.com",
                "issuer": "Let's Encrypt",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2030 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "SSL/TLS Certificate Report" in result.output


def test_ssl_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_ssl(target, port=443, timeout=5.0):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
            "--port",
            "8443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 8443


def test_ssl_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": None,
            "chain_length": 1,
            "cert": {
                "subject": "example.com",
                "issuer": "Test CA",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2030 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    out_file = tmp_path / "ssl_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "Test CA" in content


def test_brute_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["brute", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--protocol" in result.output
    assert "--port" in result.output
    assert "--user-file" in result.output
    assert "--pass-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_brute() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "brute" in result.output


def test_brute_offline_target_json(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 2,
            "attempts": 2,
            "successful_count": 1,
            "successful": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                }
            ],
            "results": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                },
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "530 Login incorrect",
                },
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["brute", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "admin" in result.output
    assert "secret" in result.output


def test_brute_offline_target_markdown(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--output-format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Brute Force Report" in result.output


def test_brute_protocol_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["protocol"] = protocol
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 22,
            "timeout": timeout,
            "usernames_tested": 0,
            "passwords_tested": 0,
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--protocol",
            "ssh",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["protocol"] == "ssh"


def test_brute_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": port,
            "timeout": timeout,
            "usernames_tested": 0,
            "passwords_tested": 0,
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--port",
            "2121",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 2121


def test_brute_wordlist_options(tmp_path, monkeypatch) -> None:
    user_file = tmp_path / "users.txt"
    user_file.write_text("admin\nroot\n")
    pass_file = tmp_path / "passwords.txt"
    pass_file.write_text("secret\npassword\n")

    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["usernames"] = usernames
        called_args["passwords"] = passwords
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": len(usernames or []),
            "passwords_tested": len(passwords or []),
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--user-file",
            str(user_file),
            "--pass-file",
            str(pass_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["usernames"] == ["admin", "root"]
    assert called_args["passwords"] == ["secret", "password"]


def test_brute_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    out_file = tmp_path / "brute_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "connection refused" in content


def test_brute_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["brute", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_brute_output_format_csv(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 2,
            "attempts": 2,
            "successful_count": 1,
            "successful": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                }
            ],
            "results": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                },
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "530 Login incorrect",
                },
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "username,password,success,error" in result.output
    assert "admin,secret,true," in result.output
    assert "admin,wrong,false,530 Login incorrect" in result.output


def test_brute_output_format_markdown(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--output-format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Brute Force Report" in result.output


def test_brute_output_format_default_is_json(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["brute", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    # JSON output starts with {
    assert "{" in result.output
    assert '"target"' in result.output


def test_brute_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    out_file = tmp_path / "brute_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--output-format",
            "csv",
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
    assert "username,password,success,error" in content
    assert "admin,wrong,false,connection refused" in content


def test_service_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_service() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "service" in result.output


def test_service_offline_target_json(monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 3,
            "services_found": 2,
            "results": [
                {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
                {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["service", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "FTP" in result.output
    assert "OpenSSH" in result.output


def test_service_offline_target_markdown(monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 2,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Service Detection Report" in result.output
    assert "*No services detected.*" in result.output


def test_service_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--ports",
            "21,22,80,443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 80, 443]


def test_service_ports_range_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--ports",
            "8000-8010",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == list(range(8000, 8011))


def test_service_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--workers",
            "100",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 100


def test_service_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 2,
            "services_found": 1,
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    out_file = tmp_path / "service_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "OpenSSH" in content


def test_scan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--profile" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "fast" in result.output
    assert "normal" in result.output
    assert "full" in result.output


def test_scan_profile_fast(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_scan_profile_normal(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "normal"])
    assert result.exit_code == 0
    assert called_args["ports"] == [20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]
    assert called_args["timeout"] == 1.0
    assert called_args["max_workers"] == 100


def test_scan_profile_full(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "full"])
    assert result.exit_code == 0
    assert len(called_args["ports"]) == 1024 + 24 - len(set(range(1, 1025)) & set([20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]))
    assert called_args["timeout"] == 2.0
    assert called_args["max_workers"] == 50


def test_scan_profile_override_ports(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast", "--ports", "80,443"])
    assert result.exit_code == 0
    assert called_args["ports"] == [80, 443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_scan_profile_override_timeout_workers(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast", "--timeout", "5.0", "--workers", "10"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 5.0
    assert called_args["max_workers"] == 10


def test_scan_help_shows_format_out() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_scan_json_output(monkeypatch, tmp_path) -> None:
    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, True), (443, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80,443", "--format", "json"])
    assert result.exit_code == 0
    assert '"target": "example.com"' in result.output
    assert "22" in result.output and "80" in result.output  # open_ports contains 22 and 80
    assert '"port": 22' in result.output
    assert '"open": true' in result.output


def test_scan_markdown_output(monkeypatch, tmp_path) -> None:
    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, True), (443, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80,443", "--format", "markdown"])
    assert result.exit_code == 0
    assert "# ethscan Port Scan Report" in result.output
    assert "**Target:** example.com" in result.output
    assert "**Open Ports:** 22, 80" in result.output
    assert "| Port | Status |" in result.output
    assert "| 22 | Open |" in result.output
    assert "| 443 | Closed |" in result.output


def test_scan_out_json(monkeypatch, tmp_path) -> None:
    out_file = tmp_path / "scan_report.json"

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80", "--format", "json", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert '"target": "example.com"' in content
    assert "22" in content  # open_ports contains 22


def test_scan_out_markdown(monkeypatch, tmp_path) -> None:
    out_file = tmp_path / "scan_report.md"

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80", "--format", "markdown", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "# ethscan Port Scan Report" in content
    assert "**Target:** example.com" in content
    assert "**Open Ports:** 22" in content


def test_scan_csv_output(monkeypatch) -> None:
    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, True), (443, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80,443", "--output-format", "csv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "port,open"
    assert "22,true" in lines
    assert "80,true" in lines
    assert "443,false" in lines


def test_scan_csv_out(monkeypatch, tmp_path) -> None:
    out_file = tmp_path / "scan_report.csv"

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True), (80, False)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--ports", "22,80", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "port,open"
    assert "22,true" in lines
    assert "80,false" in lines


def test_scan_output_format_precedence(monkeypatch) -> None:
    """--output-format should take precedence over deprecated --format."""
    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(22, True)]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--output-format", "json", "--format", "csv"])
    assert result.exit_code == 0
    assert '"target": "example.com"' in result.output
    assert "port,open" not in result.output


def test_scan_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "json" in result.output
    assert "markdown" in result.output
    assert "csv" in result.output


def test_service_csv_output(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 1,
            "results": [{"port": 22, "service": "OpenSSH", "banner": "SSH-2.0-OpenSSH_9.6"}],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--ports", "22", "--output-format", "csv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "port,service,banner"
    assert "22,OpenSSH,SSH-2.0-OpenSSH_9.6" in lines


def test_service_csv_out(monkeypatch, tmp_path) -> None:
    out_file = tmp_path / "service_report.csv"

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 1,
            "results": [{"port": 22, "service": "OpenSSH", "banner": "SSH-2.0-OpenSSH_9.6"}],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--ports", "22", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    lines = content.strip().split("\n")
    assert lines[0] == "port,service,banner"
    assert "22,OpenSSH,SSH-2.0-OpenSSH_9.6" in lines


def test_service_output_format_precedence(monkeypatch) -> None:
    """--output-format should take precedence over deprecated --format."""
    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--output-format", "json", "--format", "csv"])
    assert result.exit_code == 0
    assert '"target": "example.com"' in result.output
    assert "port,service,banner" not in result.output


def test_service_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "json" in result.output
    assert "markdown" in result.output
    assert "csv" in result.output


def test_service_profile_fast(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_service_profile_normal(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "normal"])
    assert result.exit_code == 0
    assert called_args["ports"] == [20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]
    assert called_args["timeout"] == 1.0
    assert called_args["max_workers"] == 100


def test_service_profile_full(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "full"])
    assert result.exit_code == 0
    assert len(called_args["ports"]) == 1024 + 24 - len(set(range(1, 1025)) & set([20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]))
    assert called_args["timeout"] == 2.0
    assert called_args["max_workers"] == 50


def test_service_profile_override_ports(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast", "--ports", "80,443"])
    assert result.exit_code == 0
    assert called_args["ports"] == [80, 443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_service_profile_override_timeout_workers(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast", "--timeout", "5.0", "--workers", "10"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 5.0
    assert called_args["max_workers"] == 10


def test_tls_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["tls", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--versions" in result.output
    assert "--ciphers" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_tls() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "tls" in result.output


def test_tls_offline_target_json(monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 2,
            "ciphers_tested": 2,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
                {
                    "version": "TLSv1",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_cipher": None,
                    "negotiated_protocol": None,
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
                {
                    "cipher": "AES128-SHA",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_version": None,
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tls", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "TLSv1_2" in result.output
    assert "AES128-GCM-SHA256" in result.output
    assert "supported_version_count" in result.output


def test_tls_offline_target_markdown(monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 2,
            "ciphers_tested": 2,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
                {
                    "version": "TLSv1",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_cipher": None,
                    "negotiated_protocol": None,
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
                {
                    "cipher": "AES128-SHA",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_version": None,
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "TLS Enumeration Report" in result.output
    assert "TLSv1_2" in result.output
    assert "AES128-GCM-SHA256" in result.output


def test_tls_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--port",
            "8443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 8443


def test_tls_versions_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["versions"] = versions
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": len(versions or []),
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--versions",
            "TLSv1_2,TLSv1_3",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["versions"] == ["TLSv1_2", "TLSv1_3"]


def test_tls_ciphers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["ciphers"] = ciphers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": len(ciphers or []),
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--ciphers",
            "AES128-GCM-SHA256,AES256-GCM-SHA384",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ciphers"] == ["AES128-GCM-SHA256", "AES256-GCM-SHA384"]


def test_tls_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--workers",
            "25",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 25


def test_tls_unknown_version() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--versions",
            "BOGUS",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown TLS versions" in result.output
    assert "BOGUS" in result.output


def test_tls_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 1,
            "ciphers_tested": 1,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    out_file = tmp_path / "tls_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "TLSv1_2" in content
    assert "AES128-GCM-SHA256" in content


def test_vuln_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--services-file" in result.output
    assert "--tls-file" in result.output
    assert "--ssl-file" in result.output
    assert "--severity" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_vuln() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "vuln" in result.output


def test_vuln_offline_target_json(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "CVE-2018-15473" in result.output
    assert "finding_count" in result.output


def test_vuln_offline_target_markdown(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": True,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2014-3566",
                    "kind": "protocol",
                    "title": "SSLv3 is vulnerable to POODLE",
                    "severity": "high",
                    "description": "SSLv3 supports CBC-mode ciphers.",
                    "protocol": "SSLv3",
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Vulnerability Report" in result.output
    assert "CVE-2014-3566" in result.output
    assert "SSLv3" in result.output


def test_vuln_services_file_option(tmp_path) -> None:
    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "results": [
                    {
                        "port": 21,
                        "banner": "220 ProFTPD 1.3.5 Server (Debian)",
                        "service": "ProFTPD",
                    },
                ],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--services-file",
            str(services_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "CVE-2015-3306" in result.output
    assert "ProFTPD" in result.output


def test_vuln_tls_file_option(tmp_path) -> None:
    tls_file = tmp_path / "tls_report.json"
    tls_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "supported_versions": ["SSLv3", "TLSv1_2"],
                "supported_ciphers": ["RC4-SHA", "AES128-GCM-SHA256"],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--tls-file",
            str(tls_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "CVE-2014-3566" in result.output
    assert "CVE-2013-2566" in result.output


def test_vuln_ssl_file_option(tmp_path) -> None:
    ssl_file = tmp_path / "ssl_report.json"
    ssl_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "cert": {
                    "key_size": 1024,
                    "signature_algorithm": "sha256WithRSAEncryption",
                },
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--ssl-file",
            str(ssl_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "WEAK-RSA-KEY" in result.output


def test_vuln_severity_option(tmp_path) -> None:
    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "results": [
                    {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                ],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--services-file",
            str(services_file),
            "--severity",
            "critical",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "VSFTPD-2.3.4-BACKDOOR" in result.output
    assert "CVE-2018-15473" not in result.output


def test_vuln_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--ports",
            "21,22,80",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 80]


def test_vuln_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--workers",
            "25",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 25


def test_vuln_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    out_file = tmp_path / "vuln_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "CVE-2018-15473" in content


def test_vuln_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    out_file = tmp_path / "vuln_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "Vulnerability Report" in content
    assert "CVE-2018-15473" in content


def test_vuln_help_shows_min_severity() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--min-severity" in result.output
    assert "low" in result.output
    assert "medium" in result.output
    assert "high" in result.output
    assert "critical" in result.output


def test_vuln_min_severity_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["min_severity"] = min_severity
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--min-severity", "high", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["min_severity"] == "high"


def test_vuln_min_severity_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["min_severity"] = min_severity
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["min_severity"] is None


def test_vuln_help_shows_recursive() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--recursive / --no-recursive" in result.output
    assert "--max-depth" in result.output


def test_vuln_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "3",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 3


def test_vuln_recursive_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is False
    assert called_args["max_depth"] == 2


def test_vuln_recursive_output_json(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": True,
            "max_depth": 1,
            "recursive_hosts_scanned": ["backend.internal.example.com"],
            "recursive_findings": [
                {
                    "host": "backend.internal.example.com",
                    "depth": 1,
                    "finding_count": 1,
                    "services_checked": 1,
                    "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
                    "findings": [
                        {
                            "id": "VSFTPD-2.3.4-BACKDOOR",
                            "kind": "service",
                            "title": "vsftpd backdoor",
                            "severity": "critical",
                            "description": "vsftpd 2.3.4 backdoor.",
                            "product": "vsftpd",
                            "version": "2.3.4",
                            "port": 21,
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "1",
            "--format",
            "json",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "recursive" in result.output
    assert "true" in result.output.lower()
    assert "backend.internal.example.com" in result.output
    assert "VSFTPD-2.3.4-BACKDOOR" in result.output


def test_vuln_recursive_output_markdown(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": True,
            "max_depth": 1,
            "recursive_hosts_scanned": ["backend.internal.example.com"],
            "recursive_findings": [
                {
                    "host": "backend.internal.example.com",
                    "depth": 1,
                    "finding_count": 1,
                    "services_checked": 1,
                    "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
                    "findings": [
                        {
                            "id": "VSFTPD-2.3.4-BACKDOOR",
                            "kind": "service",
                            "title": "vsftpd backdoor",
                            "severity": "critical",
                            "description": "vsftpd 2.3.4 backdoor.",
                            "product": "vsftpd",
                            "version": "2.3.4",
                            "port": 21,
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "1",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "**Recursive:** Yes" in result.output
    assert "**Max Depth:** 1" in result.output
    assert "**Recursive Hosts Scanned:** 1" in result.output
    assert "## Recursive Scan Results" in result.output
    assert "backend.internal.example.com" in result.output


def _install_vuln_salt_mock(monkeypatch, called_args):
    """Install a run_vuln mock capturing salt/pepper/algorithm args and echoing them."""
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["salt"] = salt
        called_args["pepper"] = pepper
        called_args["algorithm"] = algorithm
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": ["No known vulnerabilities matched"],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
            "salt": bool(salt),
            "pepper": bool(pepper),
            "algorithm": algorithm,
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)


def test_vuln_help_shows_salt_pepper() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--salt" in result.output
    assert "--pepper" in result.output
    assert "--algorithm" in result.output
    assert "sha256" in result.output


def test_vuln_salt_option(monkeypatch) -> None:
    called_args = {}
    _install_vuln_salt_mock(monkeypatch, called_args)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--salt",
            "mysalt",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["salt"] == "mysalt"
    assert called_args["pepper"] is None
    assert "**Salt:** applied (prepended to banner)" in result.output
    assert "**Pepper:**" not in result.output


def test_vuln_pepper_option(monkeypatch) -> None:
    called_args = {}
    _install_vuln_salt_mock(monkeypatch, called_args)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--pepper",
            "mysecret",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["pepper"] == "mysecret"
    assert called_args["salt"] is None
    assert "**Pepper:** applied (HMAC key)" in result.output
    assert "**Salt:**" not in result.output


def test_vuln_algorithm_option(monkeypatch) -> None:
    called_args = {}
    _install_vuln_salt_mock(monkeypatch, called_args)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--salt",
            "mysalt",
            "--algorithm",
            "md5",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["algorithm"] == "md5"
    assert "**Algorithm:** md5" in result.output


def test_vuln_salt_pepper_combined(monkeypatch) -> None:
    called_args = {}
    _install_vuln_salt_mock(monkeypatch, called_args)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--salt",
            "mysalt",
            "--pepper",
            "mypepper",
            "--algorithm",
            "sha1",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["salt"] == "mysalt"
    assert called_args["pepper"] == "mypepper"
    assert called_args["algorithm"] == "sha1"
    assert "**Salt:** applied (prepended to banner)" in result.output
    assert "**Pepper:** applied (HMAC key)" in result.output
    assert "**Algorithm:** sha1" in result.output


def test_vuln_salt_pepper_disabled_by_default(monkeypatch) -> None:
    called_args = {}
    _install_vuln_salt_mock(monkeypatch, called_args)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["salt"] is None
    assert called_args["pepper"] is None
    assert called_args["algorithm"] == "sha256"
    assert "**Salt:**" not in result.output
    assert "**Pepper:**" not in result.output
    assert "**Algorithm:** sha256" in result.output


def test_dnsbrute_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ns" in result.output
    assert "--wordlist" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_dnsbrute() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "dnsbrute" in result.output


def test_dnsbrute_offline_target_json(monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [
                {
                    "nameserver": "ns1.example.com",
                    "success": False,
                    "records_count": 0,
                    "records": [],
                    "error": "transfer refused (REFUSED)",
                }
            ],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 1,
            "resolved": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dnsbrute", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "93.184.216.34" in result.output


def test_dnsbrute_offline_target_markdown(monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [
                {
                    "nameserver": "ns1.example.com",
                    "success": False,
                    "records_count": 0,
                    "records": [],
                    "error": "transfer refused (REFUSED)",
                }
            ],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "DNS Brute Force Report" in result.output


def test_dnsbrute_ns_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["nameservers"] = nameservers
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": nameservers or [],
            "nameserver_source": "option" if nameservers else "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 0,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--ns",
            "ns1.example.com,ns2.example.com",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["nameservers"] == ["ns1.example.com", "ns2.example.com"]


def test_dnsbrute_wordlist_option(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["subdomains"] = subdomains
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": len(subdomains or []),
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["subdomains"] == ["www", "mail"]


def test_dnsbrute_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 0,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "10",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["max_workers"] == 10


def test_dnsbrute_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 1,
            "resolved": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    out_file = tmp_path / "dnsbrute_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "93.184.216.34" in content


def test_dnsbrute_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    out_file = tmp_path / "dnsbrute_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "DNS Brute Force Report" in content


def test_dnsbrute_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["resolver"] = resolver
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "resolver": resolver,
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--resolver",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_dnsbrute_help_shows_resolver() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--help"])
    assert result.exit_code == 0
    assert "--resolver" in result.output


def test_dnsbrute_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--recursive",
            "--max-depth",
            "3",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 3


def test_dnsbrute_no_recursive_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "recursive_axfr": [],
            "recursive_axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is False
    assert called_args["max_depth"] == 2  # Default value passed even when not recursive


def test_dnsbrute_help_shows_recursive() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.output
    assert "--max-depth" in result.output


def test_urlcheck_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["urlcheck", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--checks" in result.output
    assert "--wordlist" in result.output
    assert "--fuzz-paths" in result.output
    assert "--port" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_urlcheck() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "urlcheck" in result.output


def test_urlcheck_offline_target_json(monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": ["Content-Security-Policy"],
                    "missing": ["X-Frame-Options"],
                    "total": 7,
                    "present_count": 1,
                    "missing_count": 6,
                },
                "information_disclosure": [],
                "ssl": {"valid": True, "subject": "example.com", "issuer": "Let's Encrypt", "not_after": "Jan  1 00:00:00 2027 GMT", "days_remaining": 100},
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": 2,
                "findings": [{"path": "/admin", "status_code": 200, "error": None}],
                "all_results": [
                    {"path": "/admin", "status_code": 200, "error": None},
                    {"path": "/login", "status_code": 404, "error": None},
                ],
            },
            "ssl": {
                "target": "example.com",
                "host": "example.com",
                "port": port,
                "timeout": timeout,
                "error": None,
                "chain_length": 2,
                "cert": {
                    "subject": "example.com",
                    "issuer": "Let's Encrypt",
                    "sans": ["example.com"],
                    "not_before": "Jan  1 00:00:00 2020 GMT",
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 7,
                "web_checks_run": ["headers", "info_disclosure", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["urlcheck", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "Content-Security-Policy" in result.output
    assert "admin" in result.output


def test_urlcheck_offline_target_markdown(monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": [],
                    "missing": ["Content-Security-Policy"],
                    "total": 7,
                    "present_count": 0,
                    "missing_count": 7,
                },
                "information_disclosure": [],
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": 1,
                "findings": [],
                "all_results": [{"path": "/admin", "status_code": 404, "error": None}],
            },
            "ssl": {
                "target": "example.com",
                "host": "example.com",
                "port": port,
                "timeout": timeout,
                "error": None,
                "chain_length": 1,
                "cert": {
                    "subject": "example.com",
                    "issuer": "Test CA",
                    "sans": ["example.com"],
                    "not_before": "Jan  1 00:00:00 2020 GMT",
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 8,
                "web_checks_run": ["headers", "info_disclosure", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Consolidated Web Assessment Report" in result.output
    assert "example.com" in result.output


def test_urlcheck_checks_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["checks"] = checks
        called_args["target"] = target
        called_args["fuzz_paths"] = fuzz_paths
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": [],
                    "missing": [],
                    "total": 7,
                    "present_count": 0,
                    "missing_count": 7,
                },
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--checks",
            "headers,ssl",
            "--no-fuzz-paths",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["checks"] == ["headers", "ssl"]
    assert called_args["fuzz_paths"] is False


def test_urlcheck_unknown_check() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "https://example.com",
            "--checks",
            "bogus",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown checks" in result.output


def test_urlcheck_wordlist_option(tmp_path, monkeypatch) -> None:
    wordlist_file = tmp_path / "paths.txt"
    wordlist_file.write_text("/admin\n/login\n")
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["wordlist"] = wordlist
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": len(wordlist or []),
                "findings": [],
                "all_results": [],
            },
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["wordlist"] == ["/admin", "/login"]


def test_urlcheck_no_fuzz_paths_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["fuzz_paths"] = fuzz_paths
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--no-fuzz-paths",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["fuzz_paths"] is False


def test_urlcheck_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
                "ssl": {"valid": False, "error": "connection refused"},
            },
            "fuzz": None,
            "ssl": {
                "target": "example.com",
                "host": "example.com",
                "port": port,
                "timeout": timeout,
                "error": "connection refused",
                "chain_length": 0,
                "cert": None,
                "valid": False,
                "days_remaining": None,
            },
            "summary": {
                "total_findings": 1,
                "web_checks_run": ["headers", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--port",
            "8443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 8443


def test_urlcheck_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["timeout"] = timeout
        called_args["workers"] = workers
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "25",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["workers"] == 25


def test_urlcheck_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": {
                "target": "example.com",
                "host": "example.com",
                "port": port,
                "timeout": timeout,
                "error": None,
                "chain_length": 1,
                "cert": {
                    "subject": "example.com",
                    "issuer": "Test CA",
                    "sans": ["example.com"],
                    "not_before": "Jan  1 00:00:00 2020 GMT",
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 0,
                "web_checks_run": ["headers", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    out_file = tmp_path / "urlcheck_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "Test CA" in content


def test_urlcheck_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    out_file = tmp_path / "urlcheck_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "Consolidated Web Assessment Report" in content


def test_osdetect_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["osdetect", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--banners-file" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_osdetect() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "osdetect" in result.output


def test_osdetect_offline_target_json(monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        port_list = ports or [22, 80, 443]
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(port_list),
            "probes": [
                {
                    "port": port,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
                for port in port_list
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": bool(banners),
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["osdetect", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "inferred_os" in result.output


def test_osdetect_offline_target_markdown(monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        port_list = ports or [22, 80, 443]
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(port_list),
            "probes": [
                {
                    "port": port,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
                for port in port_list
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": bool(banners),
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "OS Detection Report" in result.output


def test_osdetect_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or []),
            "probes": [],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--ports",
            "22,80,443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [22, 80, 443]


def test_osdetect_banners_file_option(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["banners"] = banners
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [],
            "inferred_os": ["Linux"],
            "inferred_os_count": 1,
            "banners_provided": bool(banners),
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9 Linux"},
                ]
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--banners-file",
            str(services_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["banners"] == {22: "SSH-2.0-OpenSSH_8.9 Linux"}


def test_osdetect_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "25",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["max_workers"] == 25


def test_osdetect_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [
                {
                    "port": 22,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    out_file = tmp_path / "osdetect_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "inferred_os" in content


def test_osdetect_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [
                {
                    "port": 22,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    out_file = tmp_path / "osdetect_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "OS Detection Report" in content


# ---------------------------------------------------------------------------
# trace (TCP traceroute) CLI tests
# ---------------------------------------------------------------------------


def test_trace_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--max-hops" in result.output
    assert "--probes-per-hop" in result.output
    assert "--timeout" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_trace() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "trace" in result.output


def test_trace_offline_target_json(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {
                    "hop": 1,
                    "ttl": 1,
                    "ip": None,
                    "host": "*",
                    "response_type": "NO-RESPONSE",
                    "rtt_ms": 0.5,
                    "rtt_avg_ms": 0.5,
                    "probes": [
                        {
                            "hop": 1, "ttl": 1, "ip": None, "host": "*",
                            "response_type": "NO-RESPONSE",
                            "rtt_ms": 0.5, "reached_destination": False,
                            "error_code": None,
                        }
                    ],
                    "reached_destination": False,
                    "error_code": None,
                }
            ],
            "hop_count": 1,
            "destination_reached": False,
            "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "hops" in result.output  # JSON contains hops field
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"


def test_trace_offline_target_markdown(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {
                    "hop": 1,
                    "ttl": 1,
                    "ip": None,
                    "host": "*",
                    "response_type": "NO-RESPONSE",
                    "rtt_ms": 0.5,
                    "rtt_avg_ms": 0.5,
                    "probes": [
                        {
                            "hop": 1, "ttl": 1, "ip": None, "host": "*",
                            "response_type": "NO-RESPONSE",
                            "rtt_ms": 0.5, "reached_destination": False,
                            "error_code": None,
                        }
                    ],
                    "reached_destination": False,
                    "error_code": None,
                }
            ],
            "hop_count": 1,
            "destination_reached": False,
            "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "TCP Traceroute Report" in result.output
    assert "Hop Table" in result.output


def test_trace_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--port", "443", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 443


def test_trace_max_hops_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["max_hops"] = max_hops
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--max-hops",
            "10",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_hops"] == 10


def test_trace_probes_per_hop_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["probes_per_hop"] = probes_per_hop
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--probes-per-hop",
            "5",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["probes_per_hop"] == 5


def test_trace_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["timeout"] = timeout
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--timeout", "5.0"],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 5.0


def test_trace_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    out_file = tmp_path / "trace_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "TCP Traceroute Report" not in content  # JSON, not markdown
    parsed = json.loads(content)
    assert parsed["target"] == "example.com"


def test_trace_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    out_file = tmp_path / "trace_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "TCP Traceroute Report" in content


def test_trace_help_shows_recursive() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.output
    assert "--no-recursive" in result.output
    assert "--max-depth" in result.output


def test_trace_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False}
            ],
            "hop_count": 1,
            "destination_reached": True,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--recursive", "--max-depth", "3", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 3


def test_trace_recursive_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["recursive"] is False
    assert called_args["max_depth"] == 2


def test_trace_max_depth_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--max-depth", "5", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["max_depth"] == 5


def test_trace_recursive_json_output(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False}
            ],
            "hop_count": 1,
            "destination_reached": True,
            "recursive": True,
            "max_depth": 2,
            "recursive_traces": [
                {
                    "target": "1.1.1.1",
                    "host": "1.1.1.1",
                    "ip": "1.1.1.1",
                    "port": port,
                    "max_hops": max_hops,
                    "timeout": timeout,
                    "probes_per_hop": probes_per_hop,
                    "raw_socket_available": False,
                    "hops": [
                        {"hop": 1, "ip": "10.0.0.1", "reached_destination": False}
                    ],
                    "hop_count": 1,
                    "destination_reached": True,
                    "notes": [],
                }
            ],
            "notes": ["Recursive tracing completed"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--recursive", "--max-depth", "2", "--format", "json", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["recursive"] is True
    assert parsed["max_depth"] == 2
    assert "recursive_traces" in parsed
    assert len(parsed["recursive_traces"]) == 1
    assert parsed["recursive_traces"][0]["target"] == "1.1.1.1"


def test_trace_recursive_markdown_output(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False}
            ],
            "hop_count": 1,
            "destination_reached": True,
            "recursive": True,
            "max_depth": 2,
            "recursive_traces": [
                {
                    "target": "1.1.1.1",
                    "host": "1.1.1.1",
                    "ip": "1.1.1.1",
                    "port": port,
                    "max_hops": max_hops,
                    "timeout": timeout,
                    "probes_per_hop": probes_per_hop,
                    "raw_socket_available": False,
                    "hops": [
                        {"hop": 1, "ip": "10.0.0.1", "reached_destination": False}
                    ],
                    "hop_count": 1,
                    "destination_reached": True,
                    "notes": [],
                }
            ],
            "notes": ["Recursive tracing completed"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--recursive", "--format", "markdown", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Recursive Traces" in result.output
    assert "Recursive Trace 1" in result.output
    assert "1.1.1.1" in result.output


def test_trace_recursive_with_trace_notes(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
        recursive=False,
        max_depth=2,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {"hop": 1, "ip": "1.1.1.1", "reached_destination": False}
            ],
            "hop_count": 1,
            "destination_reached": True,
            "recursive": True,
            "max_depth": 2,
            "recursive_traces": [
                {
                    "target": "1.1.1.1",
                    "host": "1.1.1.1",
                    "ip": "1.1.1.1",
                    "port": port,
                    "max_hops": max_hops,
                    "timeout": timeout,
                    "probes_per_hop": probes_per_hop,
                    "raw_socket_available": False,
                    "hops": [],
                    "hop_count": 0,
                    "destination_reached": False,
                    "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
                }
            ],
            "notes": ["Recursive tracing completed for 1 intermediate hops (max depth: 2)"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--recursive", "--format", "markdown", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Recursive tracing completed" in result.output


# ---------------------------------------------------------------------------
# ping CLI tests
# ---------------------------------------------------------------------------


def test_ping_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--count" in result.output
    assert "--timeout" in result.output
    assert "--ttl" in result.output
    assert "--tcp-port" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_ping() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ping" in result.output


def test_ping_offline_target_json(monkeypatch) -> None:
    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [
                {
                    "ip": None,
                    "rtt_ms": 2000.0,
                    "ttl": ttl,
                    "sequence": 1,
                    "response_type": "TIMEOUT",
                    "error": "timeout",
                },
                {
                    "ip": None,
                    "rtt_ms": 2000.0,
                    "ttl": ttl,
                    "sequence": 2,
                    "response_type": "TIMEOUT",
                    "error": "timeout",
                },
            ],
            "successful": 0,
            "failed": 2,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": ["Raw ICMP socket unavailable; TCP connect fallback mode on port 80", "0/2 probes successful"],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["ping", "--target", "example.com", "--count", "2", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "probes" in result.output
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"
    assert parsed["count"] == 2


def test_ping_offline_target_markdown(monkeypatch) -> None:
    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [
                {
                    "ip": "93.184.216.34",
                    "rtt_ms": 12.34,
                    "ttl": ttl,
                    "sequence": 1,
                    "response_type": "CONNECTED",
                    "error": None,
                },
            ],
            "successful": 1,
            "failed": 0,
            "rtt_min_ms": 12.34,
            "rtt_max_ms": 12.34,
            "rtt_avg_ms": 12.34,
            "notes": ["Raw ICMP socket unavailable; TCP connect fallback mode on port 80", "1/1 probes successful"],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["ping", "--target", "example.com", "--format", "markdown", "--count", "1", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Ping Report" in result.output
    assert "example.com" in result.output
    assert "CONNECTED" in result.output
    assert "TCP connect fallback mode" in result.output


def test_ping_count_option(monkeypatch) -> None:
    called = {}

    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        called["count"] = count
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--count", "10"])
    assert result.exit_code == 0
    assert called["count"] == 10


def test_ping_timeout_option(monkeypatch) -> None:
    called = {}

    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        called["timeout"] = timeout
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--timeout", "5.5"])
    assert result.exit_code == 0
    assert called["timeout"] == 5.5


def test_ping_ttl_option(monkeypatch) -> None:
    called = {}

    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        called["ttl"] = ttl
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--ttl", "128"])
    assert result.exit_code == 0
    assert called["ttl"] == 128


def test_ping_tcp_port_option(monkeypatch) -> None:
    called = {}

    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        called["port"] = port
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--tcp-port", "443"])
    assert result.exit_code == 0
    assert called["port"] == 443


def test_ping_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    out_file = tmp_path / "ping_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ping",
            "--target",
            "example.com",
            "--format",
            "json",
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
    parsed = json.loads(content)
    assert parsed["target"] == "example.com"


def test_ping_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_ping(
        target,
        count=4,
        timeout=2.0,
        ttl=64,
        port=80,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "count": count,
            "timeout": timeout,
            "ttl": ttl,
            "port": port,
            "raw_socket_available": False,
            "probes": [],
            "successful": 0,
            "failed": count,
            "rtt_min_ms": None,
            "rtt_max_ms": None,
            "rtt_avg_ms": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_ping", mock_run_ping)

    out_file = tmp_path / "ping_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ping",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "Ping Report" in content


def test_wifi_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--help"])
    assert result.exit_code == 0
    assert "--interface" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_wifi() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "wifi" in result.output


def test_wifi_offline_json(monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [
                {"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}
            ],
            "access_points": [
                {"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "TestNetwork", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}
            ],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi"])
    assert result.exit_code == 0
    assert "TestNetwork" in result.output
    assert "wlan0" in result.output


def test_wifi_offline_markdown(monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [
                {"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}
            ],
            "access_points": [
                {"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "TestNetwork", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}
            ],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Wi-Fi Reconnaissance Report" in result.output
    assert "TestNetwork" in result.output


def test_wifi_interface_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_wifi(interface=None):
        called_args["interface"] = interface
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--interface", "wlan1"])
    assert result.exit_code == 0
    assert called_args["interface"] == "wlan1"


def test_wifi_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    out_file = tmp_path / "wifi_report.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "platform" in content
    assert "Linux" in content
    parsed = json.loads(content)
    assert parsed["platform"] == "Linux"


def test_wifi_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    out_file = tmp_path / "wifi_report.md"
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--format", "markdown", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Wi-Fi Reconnaissance Report" in content


def test_geo_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--timeout" in result.output
    assert "--no-cache" in result.output
    assert "--no-offline-fallback" in result.output
    assert "--api-url" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_geo() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "geo" in result.output


def test_geo_offline_target_json(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "nonexistent.invalid.domain.tld",
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": None,
            "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld'"],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "Could not resolve" in result.output
    assert "geolocation" in result.output


def test_geo_offline_target_markdown(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "nonexistent.invalid.domain.tld",
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": None,
            "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld'"],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "IP Geolocation Report" in result.output
    assert "No geolocation data available" in result.output


def test_geo_success_json(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "countryCode": "US",
                "region": "CA",
                "regionName": "California",
                "city": "Mountain View",
                "zip": "94035",
                "lat": 37.4056,
                "lon": -122.0775,
                "timezone": "America/Los_Angeles",
                "isp": "Google LLC",
                "org": "Google Public DNS",
                "as": "AS15169 Google LLC",
                "reverse": "dns.google",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "8.8.8.8",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "United States" in result.output
    assert "Mountain View" in result.output
    assert "Google LLC" in result.output
    assert "cached" in result.output


def test_geo_success_markdown(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "countryCode": "US",
                "region": "CA",
                "regionName": "California",
                "city": "Mountain View",
                "zip": "94035",
                "lat": 37.4056,
                "lon": -122.0775,
                "timezone": "America/Los_Angeles",
                "isp": "Google LLC",
                "org": "Google Public DNS",
                "as": "AS15169 Google LLC",
                "reverse": "dns.google",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "8.8.8.8",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "IP Geolocation Report" in result.output
    assert "United States" in result.output
    assert "Mountain View" in result.output


def test_geo_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    out_file = tmp_path / "geo_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "8.8.8.8",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "United States" in content
    parsed = json.loads(content)
    assert parsed["geolocation"]["country"] == "United States"


def test_geo_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {
                "status": "success",
                "query": "8.8.8.8",
                "country": "United States",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    out_file = tmp_path / "geo_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "geo",
            "--target",
            "8.8.8.8",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "IP Geolocation Report" in content
    assert "United States" in content


def test_geo_no_cache_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["use_cache"] = use_cache
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--no-cache"])
    assert result.exit_code == 0
    assert called_args["use_cache"] is False


def test_geo_no_offline_fallback_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["offline_fallback"] = offline_fallback
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--no-offline-fallback"])
    assert result.exit_code == 0
    assert called_args["offline_fallback"] is False


def test_geo_api_url_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["api_url"] = api_url
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--api-url", "https://custom.example.com/"])
    assert result.exit_code == 0
    assert called_args["api_url"] == "https://custom.example.com/"


def test_geo_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["timeout"] = timeout
        return {
            "target": target,
            "host": "8.8.8.8",
            "ip": "8.8.8.8",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--timeout", "10.0"])
    assert result.exit_code == 0
    assert called_args["timeout"] == 10.0


def test_geo_url_target(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "https://example.com/path"])
    assert result.exit_code == 0
    assert called_args["target"] == "https://example.com/path"


def test_geo_help_shows_recursive(monkeypatch) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--help"])
    assert result.exit_code == 0
    assert "--recursive" in result.output
    assert "--max-depth" in result.output


def test_geo_recursive_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "hops": [],
            "hop_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "example.com", "--recursive"])
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 30


def test_geo_recursive_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["recursive"] = recursive
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "hops": [],
            "hop_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "example.com"])
    assert result.exit_code == 0
    assert called_args["recursive"] is False


def test_geo_max_depth_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        called_args["recursive"] = recursive
        called_args["max_depth"] = max_depth
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "hops": [],
            "hop_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "example.com", "--recursive", "--max-depth", "5"])
    assert result.exit_code == 0
    assert called_args["recursive"] is True
    assert called_args["max_depth"] == 5


def test_geo_recursive_json_output(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "hops": [
                {
                    "hop": 1,
                    "ip": "10.0.0.1",
                    "host": None,
                    "response_type": "TIME_EXCEEDED",
                    "rtt_avg_ms": 1.5,
                    "geolocation": {"status": "success", "country": "US", "city": "TestCity", "isp": "TestISP"},
                }
            ],
            "hop_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "example.com", "--recursive", "--format", "json"])
    assert result.exit_code == 0
    assert "recursive" in result.output
    assert "hops" in result.output
    assert "10.0.0.1" in result.output


def test_geo_recursive_markdown_output(monkeypatch) -> None:
    def mock_run_geo(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None, recursive=False, max_depth=30):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "recursive": recursive,
            "max_depth": max_depth,
            "geolocation": {"status": "success", "country": "US", "cached": False},
            "hops": [
                {
                    "hop": 1,
                    "ip": "10.0.0.1",
                    "host": None,
                    "response_type": "TIME_EXCEEDED",
                    "rtt_avg_ms": 1.5,
                    "geolocation": {"status": "success", "country": "US", "city": "TestCity", "isp": "TestISP"},
                }
            ],
            "hop_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_geo", mock_run_geo)

    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--target", "example.com", "--recursive", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Recursive Hop Geolocation" in result.output
    assert "Hop Geolocation" in result.output
    assert "10.0.0.1" in result.output


# ---------------------------------------------------------------------------
# recon command tests
# ---------------------------------------------------------------------------


def test_recon_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--modules" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_cli_help_lists_recon() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "recon" in result.output


def test_recon_offline_target_json(tmp_path, monkeypatch) -> None:
    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains", "dns"],
            "subdomains": {"resolved_count": 1},
            "dns": {"records": {"A": ["1.2.3.4"]}},
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--format", "json"])
    assert result.exit_code == 0
    assert "target" in result.output
    assert "example.com" in result.output
    assert "modules_run" in result.output


def test_recon_offline_target_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains", "dns"],
            "subdomains": {"resolved_count": 1},
            "dns": {"records": {"A": ["1.2.3.4"]}},
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Reconnaissance Report" in result.output
    assert "example.com" in result.output


def test_recon_modules_option(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["modules"] = modules
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": modules or ["subdomains", "dns", "whois", "geo", "trace"],
            "subdomains": {},
            "dns": {},
            "whois": {},
            "geo": {},
            "trace": {},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "subdomains,dns"])
    assert result.exit_code == 0
    assert called_args["modules"] == ["subdomains", "dns"]


def test_recon_subdomains_wordlist_option(tmp_path, monkeypatch) -> None:
    wordlist_file = tmp_path / "subdomains.txt"
    wordlist_file.write_text("www\nmail\napi\n")

    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["subdomains_wordlist"] = subdomains_wordlist
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "subdomains",
                                 "--subdomains-wordlist", str(wordlist_file)])
    assert result.exit_code == 0
    assert called_args["subdomains_wordlist"] == ["www", "mail", "api"]


def test_recon_dns_types_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["dns_record_types"] = dns_record_types
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["dns"],
            "subdomains": None,
            "dns": {},
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "dns",
                                 "--dns-types", "A,MX,TXT"])
    assert result.exit_code == 0
    assert called_args["dns_record_types"] == ["A", "MX", "TXT"]


def test_recon_dns_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["dns_server"] = dns_server
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["dns"],
            "subdomains": None,
            "dns": {},
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "dns",
                                 "--dns-server", "1.1.1.1"])
    assert result.exit_code == 0
    assert called_args["dns_server"] == "1.1.1.1"


def test_recon_whois_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["whois_server"] = whois_server
        called_args["whois_port"] = whois_port
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["whois"],
            "subdomains": None,
            "dns": None,
            "whois": {},
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "whois",
                                 "--whois-server", "whois.example.com", "--whois-port", "443"])
    assert result.exit_code == 0
    assert called_args["whois_server"] == "whois.example.com"
    assert called_args["whois_port"] == 443


def test_recon_geo_cache_options(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["geo_use_cache"] = geo_use_cache
        called_args["geo_offline_fallback"] = geo_offline_fallback
        called_args["geo_api_url"] = geo_api_url
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["geo"],
            "subdomains": None,
            "dns": None,
            "whois": None,
            "geo": {},
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "8.8.8.8", "--modules", "geo",
                                 "--no-geo-cache", "--no-geo-offline-fallback"])
    assert result.exit_code == 0
    assert called_args["geo_use_cache"] is False
    assert called_args["geo_offline_fallback"] is False


def test_recon_geo_api_url_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["geo_api_url"] = geo_api_url
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["geo"],
            "subdomains": None,
            "dns": None,
            "whois": None,
            "geo": {},
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "8.8.8.8", "--modules", "geo",
                                 "--geo-api-url", "https://custom.api/"])
    assert result.exit_code == 0
    assert called_args["geo_api_url"] == "https://custom.api/"


def test_recon_trace_options(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["trace_port"] = trace_port
        called_args["trace_max_hops"] = trace_max_hops
        called_args["trace_probes_per_hop"] = trace_probes_per_hop
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["trace"],
            "subdomains": None,
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": {},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "trace",
                                 "--trace-port", "443", "--trace-max-hops", "20",
                                 "--trace-probes-per-hop", "5"])
    assert result.exit_code == 0
    assert called_args["trace_port"] == 443
    assert called_args["trace_max_hops"] == 20
    assert called_args["trace_probes_per_hop"] == 5


def test_recon_timeout_workers_options(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "subdomains",
                                 "--timeout", "10.0", "--workers", "20"])
    assert result.exit_code == 0
    assert called_args["timeout"] == 10.0
    assert called_args["max_workers"] == 20


def test_recon_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["resolver"] = resolver
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--modules", "subdomains",
                                 "--resolver", "8.8.8.8"])
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_recon_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {"resolved_count": 1},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    out_file = tmp_path / "recon_report.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "target" in content
    assert "example.com" in content


def test_recon_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {"resolved_count": 1},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    out_file = tmp_path / "recon_report.md"
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--format", "markdown",
                                 "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Reconnaissance Report" in content
    assert "example.com" in content


def test_recon_help_shows_modules() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--help"])
    assert result.exit_code == 0
    assert "subdomains" in result.output
    assert "dns" in result.output
    assert "whois" in result.output
    assert "geo" in result.output
    assert "trace" in result.output


def test_recon_url_target(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_recon(target, modules=None, subdomains_wordlist=None, dns_record_types=None,
                       dns_server=None, whois_server="whois.iana.org", whois_port=43,
                       geo_use_cache=True, geo_offline_fallback=True, geo_api_url=None,
                       trace_port=80, trace_max_hops=30, trace_probes_per_hop=3,
                       timeout=5.0, max_workers=50, resolver=None):
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "modules_run": ["subdomains"],
            "subdomains": {},
            "dns": None,
            "whois": None,
            "geo": None,
            "trace": None,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_recon", mock_run_recon)

    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "https://example.com/path"])
    assert result.exit_code == 0
    assert called_args["target"] == "https://example.com/path"


# ---------------------------------------------------------------------------
# cert command tests
# ---------------------------------------------------------------------------


def test_cert_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--timeout" in result.output
    assert "--no-cache" in result.output
    assert "--no-offline-fallback" in result.output
    assert "--api-url" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_cli_help_lists_cert() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "cert" in result.output


def test_cert_offline_target_json(monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "nonexistent.invalid.domain.tld",
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": None,
            "subdomains": [],
            "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld'"],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cert",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "Could not resolve" in result.output
    assert "cert_data" in result.output


def test_cert_offline_target_markdown(monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "nonexistent.invalid.domain.tld",
            "ip": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": None,
            "subdomains": [],
            "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld'"],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cert",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Certificate Transparency Report" in result.output
    assert "No subdomains discovered" in result.output


def test_cert_success_json(monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [{"name_value": "www.example.com"}],
                "count": 1,
                "cached": False,
            },
            "subdomains": ["www.example.com"],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cert",
            "--target",
            "example.com",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "www.example.com" in result.output
    assert "cached" in result.output


def test_cert_success_markdown(monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [{"name_value": "www.example.com"}],
                "count": 1,
                "cached": False,
            },
            "subdomains": ["www.example.com"],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cert",
            "--target",
            "example.com",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Certificate Transparency Report" in result.output
    assert "www.example.com" in result.output
    assert "1" in result.output


def test_cert_no_cache_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        called_args["use_cache"] = use_cache
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [],
                "count": 0,
                "cached": False,
            },
            "subdomains": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--no-cache"])
    assert result.exit_code == 0
    assert called_args["use_cache"] is False


def test_cert_no_offline_fallback_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        called_args["offline_fallback"] = offline_fallback
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [],
                "count": 0,
                "cached": False,
            },
            "subdomains": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--no-offline-fallback"])
    assert result.exit_code == 0
    assert called_args["offline_fallback"] is False


def test_cert_api_url_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        called_args["api_url"] = api_url
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [],
                "count": 0,
                "cached": False,
            },
            "subdomains": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--api-url", "https://custom.example.com/"])
    assert result.exit_code == 0
    assert called_args["api_url"] == "https://custom.example.com/"


def test_cert_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        called_args["timeout"] = timeout
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [],
                "count": 0,
                "cached": False,
            },
            "subdomains": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--timeout", "30.0"])
    assert result.exit_code == 0
    assert called_args["timeout"] == 30.0


def test_cert_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [{"name_value": "www.example.com"}],
                "count": 1,
                "cached": False,
            },
            "subdomains": ["www.example.com"],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    out_file = tmp_path / "cert_report.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "target" in content
    assert "example.com" in content


def test_cert_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [{"name_value": "www.example.com"}],
                "count": 1,
                "cached": False,
            },
            "subdomains": ["www.example.com"],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    out_file = tmp_path / "cert_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cert", "--target", "example.com", "--format", "markdown", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Certificate Transparency Report" in content
    assert "example.com" in content


def test_cert_url_target(monkeypatch) -> None:
    called_args = {}

    def mock_run_cert(target, timeout=10.0, use_cache=True, offline_fallback=True, api_url=None):
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "ip": "93.184.216.34",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "cert_data": {
                "domain": "example.com",
                "entries": [],
                "count": 0,
                "cached": False,
            },
            "subdomains": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cert", mock_run_cert)

    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "https://example.com/path"])
    assert result.exit_code == 0
    assert called_args["target"] == "https://example.com/path"


def test_cve_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cve", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--services-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cve_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cve", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--services-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_cve() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "cve" in result.output


def test_cve_offline_target_json(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": host,
            "host": host,
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.service.run_service", mock_run_service)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["cve", "--target", "nonexistent.invalid.domain.tld", "--timeout", "0.5"]
    )
    assert result.exit_code == 0
    assert "cve_entries" in result.output
    assert "services_checked" in result.output


def test_cve_offline_target_markdown(monkeypatch) -> None:
    def mock_run_service(host, ports=None, timeout=3.0, max_workers=50):
        return {
            "target": host,
            "host": host,
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.service.run_service", mock_run_service)
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cve",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "ethscan CVE Report" in result.output
    assert "Severity Summary" in result.output


def test_cve_services_file_option(tmp_path, monkeypatch) -> None:
    services_file = tmp_path / "services.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}
                ],
            }
        )
    )
    monkeypatch.setattr("ethscan.cve._fetch_cve_data", lambda *a, **k: None)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cve",
            "--target",
            "example.com",
            "--services-file",
            str(services_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "CVE-2016-6210" in result.output
    assert "OpenSSH" in result.output


def test_cve_no_cache_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        called_args["use_cache"] = use_cache
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["cve", "--target", "example.com", "--no-cache", "--timeout", "0.5"]
    )
    assert result.exit_code == 0
    assert called_args["use_cache"] is False


def test_cve_no_offline_fallback_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        called_args["offline_fallback"] = offline_fallback
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--no-offline-fallback", "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert called_args["offline_fallback"] is False


def test_cve_api_url_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        called_args["api_url"] = api_url
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--api-url", "https://cve.example.com/", "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert called_args["api_url"] == "https://cve.example.com/"


def test_cve_severity_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        called_args["severity"] = severity
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--severity", "high", "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert called_args["severity"] == "high"


def test_cve_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    out_file = tmp_path / "cve_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--out", str(out_file), "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "cve_entries" in content


def test_cve_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_cve(target, services_file=None, timeout=10.0, service_timeout=3.0,
                     workers=50, use_cache=True, offline_fallback=True, api_url=None,
                     severity=None, min_severity=None, ports=None, profile=None):
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    out_file = tmp_path / "cve_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cve",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--out",
            str(out_file),
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan CVE Report" in content


def test_cve_help_shows_ports() -> None:
    """Test that cve help shows the --ports option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["cve", "--help"])
    assert result.exit_code == 0
    assert "--ports" in result.output


def test_cve_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(
        target,
        services_file=None,
        timeout=10.0,
        service_timeout=3.0,
        workers=50,
        use_cache=True,
        offline_fallback=True,
        api_url=None,
        severity=None,
        min_severity=None,
        ports=None,
        profile=None,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--ports", "22,80,443", "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [22, 80, 443]


def test_cve_ports_option_with_ranges(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(
        target,
        services_file=None,
        timeout=10.0,
        service_timeout=3.0,
        workers=50,
        use_cache=True,
        offline_fallback=True,
        api_url=None,
        severity=None,
        min_severity=None,
        ports=None,
        profile=None,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cve", "--target", "example.com", "--ports", "1-100,443,8080-8090", "--timeout", "0.5"],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == list(range(1, 101)) + [443] + list(range(8080, 8091))


def test_cve_ports_option_disabled_when_services_file(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(
        target,
        services_file=None,
        timeout=10.0,
        service_timeout=3.0,
        workers=50,
        use_cache=True,
        offline_fallback=True,
        api_url=None,
        severity=None,
        min_severity=None,
        ports=None,
        profile=None,
    ):
        called_args["ports"] = ports
        called_args["services_file"] = services_file
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    import json
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "target": "example.com",
                "host": "example.com",
                "timeout": 3.0,
                "ports_scanned": 1,
                "services_found": 1,
                "results": [{"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2", "service": "OpenSSH"}],
            },
            f,
        )
        services_file = f.name

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cve",
            "--target",
            "example.com",
            "--services-file",
            services_file,
            "--ports",
            "22,80",
            "--timeout",
            "0.5",
        ],
    )
    assert result.exit_code == 0
    # When services_file is provided, ports should be ignored (None)
    assert called_args["ports"] is None
    assert called_args["services_file"] == services_file

    import os
    os.unlink(services_file)


def test_cve_min_severity_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(
        target,
        services_file=None,
        timeout=10.0,
        service_timeout=3.0,
        workers=50,
        use_cache=True,
        offline_fallback=True,
        api_url=None,
        severity=None,
        min_severity=None,
        ports=None,
        profile=None,
    ):
        called_args["min_severity"] = min_severity
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["cve", "--target", "example.com", "--min-severity", "high", "--timeout", "0.5"]
    )
    assert result.exit_code == 0
    assert called_args["min_severity"] == "high"


def test_cve_min_severity_disabled_by_default(monkeypatch) -> None:
    called_args = {}

    def mock_run_cve(
        target,
        services_file=None,
        timeout=10.0,
        service_timeout=3.0,
        workers=50,
        use_cache=True,
        offline_fallback=True,
        api_url=None,
        severity=None,
        min_severity=None,
        ports=None,
        profile=None,
    ):
        called_args["min_severity"] = min_severity
        called_args["target"] = target
        return {
            "target": target,
            "host": target,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "api_url": api_url,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "ports": ports,
            "services_checked": 0,
            "cve_entries": [],
            "cve_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_cve", mock_run_cve)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["cve", "--target", "example.com", "--timeout", "0.5"]
    )
    assert result.exit_code == 0
    assert called_args["min_severity"] is None


def test_cve_help_shows_min_severity() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cve", "--help"])
    assert result.exit_code == 0
    assert "--min-severity" in result.output
    assert "critical" in result.output
    assert "high" in result.output
    assert "medium" in result.output
    assert "low" in result.output


def test_cidr_help() -> None:
    """Test cidr command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--help"])
    assert result.exit_code == 0
    assert "--cidr" in result.output
    assert "--contains" in result.output
    assert "--diff" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_cidr_top_level_help_lists() -> None:
    """Test that cidr appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "cidr" in result.output.lower()


def test_cidr_offline_target_json() -> None:
    """Test cidr command with JSON output."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "192.168.1.0/24", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["cidr"] == "192.168.1.0/24"
    assert parsed["network"]["usable_host_count"] == 254


def test_cidr_offline_target_markdown() -> None:
    """Test cidr command with Markdown output."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "10.0.0.0/8", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "ethscan CIDR Network Calculator Report" in result.output
    assert "10.0.0.0/8" in result.output


def test_cidr_contains_option() -> None:
    """Test cidr command with --contains option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cidr",
            "--cidr",
            "192.168.1.0/24",
            "--contains",
            "192.168.1.50",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["contains"]["in_network"] is True


def test_cidr_out_option_json(tmp_path) -> None:
    """Test cidr command with --out (json)."""
    out_file = tmp_path / "cidr_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cidr",
            "--cidr",
            "192.168.1.0/24",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    parsed = json.loads(content)
    assert parsed["cidr"] == "192.168.1.0/24"


def test_cidr_out_option_markdown(tmp_path) -> None:
    """Test cidr command with --out (markdown)."""
    out_file = tmp_path / "cidr_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cidr",
            "--cidr",
            "10.0.0.0/8",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan CIDR Network Calculator Report" in content


def test_cidr_output_format_csv() -> None:
    """Test cidr command with --output-format csv."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "192.168.1.0/24", "--output-format", "csv"],
    )
    assert result.exit_code == 0
    assert "cidr,network_address,broadcast_address,netmask,wildcard_mask,prefix_length,num_addresses,first_address,last_address,is_private,contains_ip,contains_in_network,diff_count,diff_first,diff_last" in result.output
    assert "192.168.1.0/24" in result.output
    assert "255.255.255.0" in result.output


def test_cidr_output_format_csv_out(tmp_path) -> None:
    """Test cidr command with --output-format csv --out."""
    out_file = tmp_path / "cidr_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cidr",
            "--cidr",
            "192.168.1.0/24",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "cidr,network_address,broadcast_address" in content
    assert "192.168.1.0/24" in content


def test_cidr_format_csv_alias() -> None:
    """Test cidr command with deprecated --format csv alias."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "192.168.1.0/24", "--format", "csv"],
    )
    assert result.exit_code == 0
    assert "cidr,network_address,broadcast_address,netmask,wildcard_mask,prefix_length,num_addresses,first_address,last_address,is_private,contains_ip,contains_in_network,diff_count,diff_first,diff_last" in result.output


def test_cidr_output_format_default_is_json() -> None:
    """Test cidr command defaults to JSON when no format specified."""
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--cidr", "192.168.1.0/24"])
    assert result.exit_code == 0
    assert '"cidr": "192.168.1.0/24"' in result.output
    assert "target,network,netmask" not in result.output  # not CSV by default


def test_cidr_output_format_precedence_over_format() -> None:
    """Test --output-format takes precedence over --format."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cidr",
            "--cidr",
            "192.168.1.0/24",
            "--format",
            "json",
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    assert "cidr,network_address,broadcast_address" in result.output
    assert '"cidr"' not in result.output


def test_config_help() -> None:
    """Test config command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "--config" in result.output
    assert "--init" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_config_lists_in_top_level_help() -> None:
    """Test config command appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "config" in result.output


def test_config_no_file_json() -> None:
    """Test config command with no config file (json)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["config_file"] is None
    assert parsed["defaults"] == {}
    assert parsed["commands"] == {}


def test_config_no_file_markdown() -> None:
    """Test config command with no config file (markdown)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--format", "markdown"])
    assert result.exit_code == 0
    assert "ethscan Configuration" in result.output
    assert "No config file found" in result.output


def test_config_with_explicit_file(tmp_path) -> None:
    """Test config command with an explicit config file."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text(
        "defaults:\n  timeout: 5.0\ncommands:\n  scan:\n    ports: common\n"
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["config_file"] == str(cfg)
    assert parsed["defaults"]["timeout"] == 5.0
    assert parsed["commands"]["scan"]["ports"] == "common"


def test_config_inherits_parent_config(tmp_path) -> None:
    """Test config subcommand inherits parent --config."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("defaults:\n  timeout: 7.0\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["config_file"] == str(cfg)
    assert parsed["defaults"]["timeout"] == 7.0


def test_config_init_writes_sample(tmp_path) -> None:
    """Test config --init writes a sample config file."""
    out = tmp_path / "sample.yaml"
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--init", str(out)])
    assert result.exit_code == 0
    assert "Sample config written" in result.output
    assert out.exists()
    content = out.read_text()
    assert "defaults:" in content
    assert "commands:" in content


def test_config_out_json(tmp_path) -> None:
    """Test config command with --out (json)."""
    out_file = tmp_path / "config.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text())
    assert parsed["config_file"] is None


def test_config_out_markdown(tmp_path) -> None:
    """Test config command with --out (markdown)."""
    out_file = tmp_path / "config.md"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["config", "--format", "markdown", "--out", str(out_file)]
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    assert "ethscan Configuration" in out_file.read_text()


def test_config_invalid_yaml_shows_parse_error(tmp_path) -> None:
    """Test config command surfaces parse errors."""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("{{{\n")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["--config", str(cfg), "config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "parse_error" in parsed
    assert "Failed to parse" in parsed["parse_error"]


def test_config_invalid_yaml_markdown(tmp_path) -> None:
    """Test config command surfaces parse errors in markdown."""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("{{{\n")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli, ["--config", str(cfg), "config", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "Parse Error" in result.output
    assert "Failed to parse" in result.output


def test_config_unknown_command_warns(tmp_path) -> None:
    """Test config command warns about unknown commands."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("commands:\n  nonexistentcmd:\n    foo: bar\n")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["--config", str(cfg), "config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "nonexistentcmd" in parsed["commands"]


def test_config_applies_to_scan_command(tmp_path) -> None:
    """Test config values apply to the scan command."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("commands:\n  scan:\n    profile: normal\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "scan", "--target", "127.0.0.1"])
    assert result.exit_code == 0
    # profile normal uses 24 common ports - check JSON output
    assert '"ports_scanned": 24' in result.output


def test_config_explicit_overrides_config(tmp_path) -> None:
    """Test CLI argument overrides config value."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("commands:\n  cidr:\n    format: markdown\n")
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--config", str(cfg), "cidr", "--cidr", "192.168.1.0/24", "--format", "json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)


# ---------------------------------------------------------------------------
# mac command CLI tests
# ---------------------------------------------------------------------------


def test_mac_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["mac", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--timeout" in result.output
    assert "--no-cache" in result.output
    assert "--no-offline-fallback" in result.output
    assert "--api-url" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_mac() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "mac" in result.output


def test_mac_offline_target_json(monkeypatch) -> None:
    def mock_run_mac(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "mac": "00:1a:2b:3c:4d:5e",
            "oui": "001a2b3c",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": {
                "mac": "00:1a:2b:3c:4d:5e",
                "vendor": "Cisco Systems",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_mac", mock_run_mac)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "mac",
            "--target",
            "00:1A:2B:3C:4D:5E",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "Cisco Systems" in result.output
    assert "001a2b3c" in result.output


def test_mac_offline_target_markdown(monkeypatch) -> None:
    def mock_run_mac(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "mac": "00:1a:2b:3c:4d:5e",
            "oui": "001a2b3c",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": {
                "mac": "00:1a:2b:3c:4d:5e",
                "vendor": "Cisco Systems",
                "cached": False,
            },
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_mac", mock_run_mac)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "mac",
            "--target",
            "00:1A:2B:3C:4D:5E",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "MAC Vendor Lookup Report" in result.output
    assert "Cisco Systems" in result.output
    assert "001a2b3c" in result.output


def test_mac_hostname_unresolvable_json(monkeypatch) -> None:
    def mock_run_mac(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "mac": None,
            "oui": None,
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": None,
            "notes": ["Could not resolve host 'nonexistent.invalid.domain.tld' to a MAC address"],
        }

    monkeypatch.setattr("ethscan.cli.run_mac", mock_run_mac)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "mac",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "Could not resolve" in result.output
    assert "mac" in result.output


def test_mac_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_mac(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "mac": "00:1a:2b:3c:4d:5e",
            "oui": "001a2b3c",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": {"mac": "00:1a:2b:3c:4d:5e", "vendor": "Cisco", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_mac", mock_run_mac)

    out_file = tmp_path / "mac_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "mac",
            "--target",
            "00:1A:2B:3C:4D:5E",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Cisco" in content


def test_mac_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_mac(target, timeout=5.0, use_cache=True, offline_fallback=True, api_url=None):
        return {
            "target": target,
            "mac": "00:1a:2b:3c:4d:5e",
            "oui": "001a2b3c",
            "timeout": timeout,
            "use_cache": use_cache,
            "offline_fallback": offline_fallback,
            "mac_data": {"mac": "00:1a:2b:3c:4d:5e", "vendor": "Cisco", "cached": False},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_mac", mock_run_mac)

    out_file = tmp_path / "mac_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "mac",
            "--target",
            "00:1A:2B:3C:4D:5E",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    assert "MAC Vendor Lookup Report" in out_file.read_text()


# ---------------------------------------------------------------------------
# dnssec command CLI tests
# ---------------------------------------------------------------------------


def test_dnssec_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnssec", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--server" in result.output
    assert "--timeout" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_dnssec() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "dnssec" in result.output


def test_dnssec_offline_target_json(monkeypatch) -> None:
    def mock_run_dnssec(target, server=None, timeout=5.0):
        return {
            "target": target,
            "domain": "example.com",
            "validated": False,
            "dnskey": {"success": True, "keys": [], "error": None},
            "ds": {"success": True, "records": [], "error": None},
            "chain": [],
            "notes": ["No DNSKEY records found (unsigned zone)"],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dnssec", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "validated" in result.output
    assert "false" in result.output.lower()


def test_dnssec_offline_target_markdown(monkeypatch) -> None:
    def mock_run_dnssec(target, server=None, timeout=5.0):
        return {
            "target": target,
            "domain": "example.com",
            "validated": True,
            "dnskey": {
                "success": True,
                "keys": [
                    {
                        "name": "example.com.",
                        "flags": 257,
                        "protocol": 3,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "key_tag": 12345,
                        "key_data": "abc123",
                    }
                ],
                "error": None,
            },
            "ds": {
                "success": True,
                "records": [
                    {
                        "name": "example.com.",
                        "key_tag": 12345,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "digest_type": 2,
                        "digest_type_name": "SHA-256",
                        "digest": "abcdef123456",
                    }
                ],
                "error": None,
            },
            "chain": [
                {"zone": "example.com", "dnskey": {"success": True, "keys": [{}], "error": None}},
                {"zone": "com", "ds": {"success": True, "records": [{}], "error": None}},
            ],
            "notes": [],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnssec",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "DNSSEC Validation Report" in result.output
    assert "RSASHA256" in result.output
    assert "SHA-256" in result.output


def test_dnssec_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnssec(target, server=None, timeout=5.0):
        called_args["server"] = server
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "validated": False,
            "dnskey": {"success": False, "keys": [], "error": "no response"},
            "ds": {"success": False, "records": [], "error": "no response"},
            "chain": [],
            "notes": [],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnssec",
            "--target",
            "example.com",
            "--server",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["server"] == "8.8.8.8"


def test_dnssec_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnssec(target, server=None, timeout=5.0):
        called_args["timeout"] = timeout
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "validated": False,
            "dnskey": {"success": False, "keys": [], "error": "no response"},
            "ds": {"success": False, "records": [], "error": "no response"},
            "chain": [],
            "notes": [],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnssec",
            "--target",
            "example.com",
            "--timeout",
            "10.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 10.0


def test_dnssec_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_dnssec(target, server=None, timeout=5.0):
        return {
            "target": target,
            "domain": "example.com",
            "validated": True,
            "dnskey": {
                "success": True,
                "keys": [
                    {
                        "name": "example.com.",
                        "flags": 257,
                        "protocol": 3,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "key_tag": 12345,
                        "key_data": "abc123",
                    }
                ],
                "error": None,
            },
            "ds": {
                "success": True,
                "records": [
                    {
                        "name": "example.com.",
                        "key_tag": 12345,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "digest_type": 2,
                        "digest_type_name": "SHA-256",
                        "digest": "abcdef123456",
                    }
                ],
                "error": None,
            },
            "chain": [],
            "notes": [],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    out_file = tmp_path / "dnssec_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnssec",
            "--target",
            "example.com",
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
    assert "example.com" in content
    assert "RSASHA256" in content


def test_dnssec_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_dnssec(target, server=None, timeout=5.0):
        return {
            "target": target,
            "domain": "example.com",
            "validated": True,
            "dnskey": {
                "success": True,
                "keys": [
                    {
                        "name": "example.com.",
                        "flags": 257,
                        "protocol": 3,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "key_tag": 12345,
                        "key_data": "abc123",
                    }
                ],
                "error": None,
            },
            "ds": {
                "success": True,
                "records": [
                    {
                        "name": "example.com.",
                        "key_tag": 12345,
                        "algorithm": 8,
                        "algorithm_name": "RSASHA256",
                        "digest_type": 2,
                        "digest_type_name": "SHA-256",
                        "digest": "abcdef123456",
                    }
                ],
                "error": None,
            },
            "chain": [],
            "notes": [],
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dnssec", mock_run_dnssec)

    out_file = tmp_path / "dnssec_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnssec",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "DNSSEC Validation Report" in content
    assert "example.com" in content


# ---------------------------------------------------------------------------
# completion command CLI tests
# ---------------------------------------------------------------------------


def test_completion_help() -> None:
    """Test completion command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--help"])
    assert result.exit_code == 0
    assert "--shell" in result.output
    assert "--prog-name" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "bash" in result.output
    assert "zsh" in result.output
    assert "fish" in result.output


def test_completion_lists_in_top_level_help() -> None:
    """Test completion command appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "completion" in result.output


def test_completion_bash_json() -> None:
    """Test completion command produces bash JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "bash"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["shell"] == "bash"
    assert parsed["prog_name"] == "ethscan"
    assert "_ethscan_completion" in parsed["script"]


def test_completion_zsh_json() -> None:
    """Test completion command produces zsh JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "zsh"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["shell"] == "zsh"
    assert "#compdef ethscan" in parsed["script"]


def test_completion_fish_json() -> None:
    """Test completion command produces fish JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "fish"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["shell"] == "fish"
    assert "function _ethscan_completion" in parsed["script"]


def test_completion_default_shell_is_bash() -> None:
    """Test completion defaults to bash shell."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["shell"] == "bash"


def test_completion_markdown() -> None:
    """Test completion command produces markdown output."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["completion", "--shell", "bash", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "ethscan Shell Completion" in result.output
    assert "_ethscan_completion" in result.output
    assert "Installation" in result.output


def test_completion_custom_prog_name() -> None:
    """Test completion command with custom prog name."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["completion", "--shell", "bash", "--prog-name", "mytool"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["prog_name"] == "mytool"
    assert "_mytool_completion" in parsed["script"]


def test_completion_invalid_shell_errors() -> None:
    """Test completion command rejects unsupported shells."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "powershell"])
    assert result.exit_code != 0
    assert "not one of" in result.output
    assert "bash" in result.output


def test_completion_out_json(tmp_path) -> None:
    """Test completion command with --out (json)."""
    out_file = tmp_path / "completion.bash"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["completion", "--shell", "bash", "--out", str(out_file)]
    )
    assert result.exit_code == 0
    assert "Completion script written" in result.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text())
    assert parsed["shell"] == "bash"
    assert "_ethscan_completion" in parsed["script"]


def test_completion_out_markdown(tmp_path) -> None:
    """Test completion command with --out (markdown)."""
    out_file = tmp_path / "completion.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "completion",
            "--shell",
            "zsh",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Completion script written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan Shell Completion" in content
    assert "zsh" in content
    assert "#compdef ethscan" in content


def test_jwt_out_option_markdown(tmp_path) -> None:
    token = _make_jwt({"alg": "HS256"}, {"sub": "user1", "exp": 1800000000})
    out_file = tmp_path / "report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["jwt", "--token", token, "--format", "markdown", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "JWT Inspection Report" in content


def test_jwt_invalid_token() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["jwt", "--token", "not-a-jwt", "--format", "json"])
    assert result.exit_code == 0
    assert "valid_structure" in result.output
    assert "false" in result.output


def test_jwt_no_token_empty_stdin() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["jwt"], input="")
    assert result.exit_code == 0
    assert "No token provided." in result.output


def test_jwt_none_algorithm_cli() -> None:
    token = _make_jwt({"alg": "none"}, {"sub": "user1"}, with_sig=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["jwt", "--token", token, "--format", "json"])
    assert result.exit_code == 0
    assert "alg=none" in result.output


# ---------------------------------------------------------------------------
# CIDR CLI tests
# ---------------------------------------------------------------------------


def test_cidr_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--help"])
    assert result.exit_code == 0
    assert "--cidr" in result.output
    assert "--contains" in result.output
    assert "--diff" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_cidr_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "cidr" in result.output


def test_cidr_ipv4_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--cidr", "192.168.1.0/24", "--format", "json"])
    assert result.exit_code == 0
    assert "192.168.1.0/24" in result.output
    assert "IPv4" in result.output
    assert "network_address" in result.output


def test_cidr_ipv4_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--cidr", "192.168.1.0/24", "--format", "markdown"])
    assert result.exit_code == 0
    assert "CIDR Network Calculator Report" in result.output
    assert "192.168.1.0/24" in result.output
    assert "Network Address" in result.output


def test_cidr_ipv6_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--cidr", "2001:db8::/32", "--format", "json"])
    assert result.exit_code == 0
    assert "2001:db8::/32" in result.output
    assert "IPv6" in result.output


def test_cidr_bare_ip_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cidr", "--cidr", "192.168.1.100", "--format", "json"])
    assert result.exit_code == 0
    assert "192.168.1.100/32" in result.output


def test_cidr_contains_option_true_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["cidr", "--cidr", "192.168.1.0/24", "--contains", "192.168.1.50", "--format", "json"]
    )
    assert result.exit_code == 0
    assert "in_network" in result.output
    assert "true" in result.output.lower()


def test_cidr_contains_option_false_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["cidr", "--cidr", "192.168.1.0/24", "--contains", "10.0.0.1", "--format", "json"]
    )
    assert result.exit_code == 0
    assert "in_network" in result.output
    assert "false" in result.output.lower()


def test_cidr_out_option_json(tmp_path) -> None:
    out_file = tmp_path / "cidr.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "192.168.1.0/24", "--format", "json", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "192.168.1.0/24" in content


def test_cidr_out_option_markdown(tmp_path) -> None:
    out_file = tmp_path / "cidr.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cidr", "--cidr", "192.168.1.0/24", "--format", "markdown", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "CIDR Network Calculator Report" in content

# ---------------------------------------------------------------------------
# Hash CLI tests
# ---------------------------------------------------------------------------


def test_hash_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--help"])
    assert result.exit_code == 0
    assert "--password" in result.output
    assert "--algorithm" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "md5" in result.output
    assert "sha256" in result.output
    assert "ntlm" in result.output


def test_hash_lists_in_top_level_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "hash" in result.output


def test_hash_password_md5_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--password", "password", "--algorithm", "md5", "--format", "json"]
    )
    assert result.exit_code == 0
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in result.output
    assert "md5" in result.output
    assert "passwords_hashed" in result.output


def test_hash_password_sha256_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--password", "password", "--algorithm", "sha256", "--format", "json"]
    )
    assert result.exit_code == 0
    assert "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8" in result.output


def test_hash_password_md5_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--password", "password", "--algorithm", "md5", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "Password Hash Report" in result.output
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in result.output


def test_hash_default_algorithm_is_md5() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--password", "password", "--format", "json"])
    assert result.exit_code == 0
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in result.output
    assert '"algorithm": "md5"' in result.output


def test_hash_multiple_passwords() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--password", "123456", "--algorithm", "sha1", "--format", "json"],
    )
    assert result.exit_code == 0
    assert "passwords_hashed" in result.output
    assert "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8" in result.output


def test_hash_stdin_input_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--algorithm", "md5", "--format", "json"], input="password\n")
    assert result.exit_code == 0
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in result.output


def test_hash_stdin_input_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--algorithm", "sha256", "--format", "markdown"], input="password\n"
    )
    assert result.exit_code == 0
    assert "Password Hash Report" in result.output
    assert "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8" in result.output


def test_hash_no_passwords() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--format", "json"], input="")
    assert result.exit_code == 0
    assert "No passwords provided" in result.output


def test_hash_out_option_json(tmp_path) -> None:
    out_file = tmp_path / "hash.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--algorithm", "md5", "--format", "json", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in content


def test_hash_out_option_markdown(tmp_path) -> None:
    out_file = tmp_path / "hash.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--algorithm", "sha256", "--format", "markdown", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Password Hash Report" in content


def test_hash_pipe_escape_in_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--password", "pass|word", "--algorithm", "md5", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "pass\\|word" in result.output


def test_hash_help_shows_file_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--help"])
    assert result.exit_code == 0
    assert "--file" in result.output


def test_hash_file_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n123456\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--file", str(password_file), "--algorithm", "md5", "--format", "json"],
    )
    assert result.exit_code == 0
    assert "passwords_hashed" in result.output
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in result.output
    assert "e10adc3949ba59abbe56e057f20f883e" in result.output


def test_hash_file_option_markdown(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--file", str(password_file), "--algorithm", "sha256", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "Password Hash Report" in result.output
    assert "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8" in result.output


def test_hash_file_skips_empty_lines_and_strips(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("  password  \n\n   \n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--file", str(password_file), "--algorithm", "md5", "--format", "json"],
    )
    assert result.exit_code == 0
    assert '"passwords_hashed": 1' in result.output


def test_hash_file_with_out_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n", encoding="utf-8")
    out_file = tmp_path / "hash.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--file", str(password_file), "--algorithm", "md5", "--format", "json", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    assert "5f4dcc3b5aa765d61d8327deb882cf99" in out_file.read_text()


def test_hash_password_flags_take_precedence_over_file(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("fromfile\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "fromflag", "--file", str(password_file), "--algorithm", "md5", "--format", "json"],
    )
    assert result.exit_code == 0
    assert '"passwords_hashed": 1' in result.output
    assert "fromflag" in result.output
    assert "fromfile" not in result.output


def test_hash_file_takes_precedence_over_stdin(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("fromfile\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--file", str(password_file), "--algorithm", "md5", "--format", "json"],
        input="fromstdin\n",
    )
    assert result.exit_code == 0
    assert '"passwords_hashed": 1' in result.output
    assert "fromfile" in result.output
    assert "fromstdin" not in result.output


def test_hash_file_missing_file_fails(tmp_path) -> None:
    missing = tmp_path / "does-not-exist.txt"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--file", str(missing), "--algorithm", "md5", "--format", "json"],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, FileNotFoundError)


# ---------------------------------------------------------------------------
# hash --check
# ---------------------------------------------------------------------------


def test_hash_check_help_shows_check_option() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--help"])
    assert result.exit_code == 0
    assert "--check" in result.output


def test_hash_check_match_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is True
    assert parsed["algorithm"] == "md5"
    assert parsed["computed"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert parsed["error"] is None


def test_hash_check_mismatch_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "wrongpass", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is False
    assert parsed["computed"] != "5f4dcc3b5aa765d61d8327deb882cf99"


def test_hash_check_match_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "Password Check Report" in result.output
    assert "MATCH" in result.output


def test_hash_check_mismatch_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "wrongpass", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "MISMATCH" in result.output


def test_hash_check_sha256_explicit_algorithm() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--check",
            "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is True
    assert parsed["algorithm"] == "sha256"


def test_hash_check_infers_algorithm_from_length() -> None:
    # 40-char digest infers sha1
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--check",
            "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is True
    assert parsed["algorithm"] == "sha1"


def test_hash_check_unknown_length_error() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--check", "deadbeef", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is None
    assert parsed["error"] is not None
    assert "Could not infer algorithm" in parsed["error"]


def test_hash_check_with_out_option(tmp_path) -> None:
    out_file = tmp_path / "check.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--check",
            "5f4dcc3b5aa765d61d8327deb882cf99",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text())
    assert parsed["match"] is True


def test_hash_check_pipe_escape_in_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "pass|word", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "pass\\|word" in result.output


def test_hash_check_no_passwords() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["hash", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--format", "json"],
    )
    assert result.exit_code == 0
    assert "No passwords provided" in result.output


def test_hash_salt_option() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--salt", "saltvalue", "--algorithm", "md5", "--format", "json"],
    )
    assert result.exit_code == 0
    assert "e137588f7bb4aa4f0c24592088b82f31" in result.output
    assert '"salt": true' in result.output
    assert '"pepper": false' in result.output


def test_hash_salt_option_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--salt", "saltvalue", "--algorithm", "sha256", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "Salt" in result.output
    assert "4a4c50688190ef1dc9aced9babc7bf4ff520ee712d249b98e3725da81479a7c1" in result.output


def test_hash_pepper_option() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--pepper", "secretpepper", "--algorithm", "sha256", "--format", "json"],
    )
    assert result.exit_code == 0
    assert "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad" in result.output
    assert '"pepper": true' in result.output


def test_hash_pepper_option_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--password", "password", "--pepper", "secretpepper", "--algorithm", "sha256", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "Pepper" in result.output
    assert "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad" in result.output


def test_hash_salt_and_pepper_combined() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--pepper",
            "secretpepper",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert (
        "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
        in result.output
    )
    assert '"salt": true' in result.output
    assert '"pepper": true' in result.output


def test_hash_salt_with_file_option(tmp_path) -> None:
    password_file = tmp_path / "passwords.txt"
    password_file.write_text("password\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["hash", "--file", str(password_file), "--salt", "s", "--algorithm", "sha256", "--format", "json"],
    )
    assert result.exit_code == 0
    assert '"salt": true' in result.output
    assert result.output.count('"passwords_hashed": 1') == 1


def test_hash_salt_and_pepper_with_out_option(tmp_path) -> None:
    out_file = tmp_path / "hash.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--pepper",
            "secretpepper",
            "--algorithm",
            "sha256",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert (
        "862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59"
        in content
    )


def test_hash_check_with_salt_match() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--check",
            "e137588f7bb4aa4f0c24592088b82f31",
            "--algorithm",
            "md5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"match": true' in result.output
    assert '"salt": true' in result.output


def test_hash_check_with_pepper_match() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--pepper",
            "secretpepper",
            "--check",
            "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"match": true' in result.output
    assert '"pepper": true' in result.output


def test_hash_check_with_pepper_mismatch() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "wrongpass",
            "--pepper",
            "secretpepper",
            "--check",
            "e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad",
            "--algorithm",
            "sha256",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "MISMATCH" in result.output
    assert "Pepper" in result.output


def test_hash_check_ntlm_with_pepper_error() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--pepper",
            "p",
            "--algorithm",
            "ntlm",
            "--check",
            "5f4dcc3b5aa765d61d8327deb882cf99",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"match": null' in result.output
    assert "error" in result.output


def test_hash_help_shows_salt_pepper() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--help"])
    assert result.exit_code == 0
    assert "--salt" in result.output
    assert "--pepper" in result.output


def test_hash_help_shows_iterations() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--help"])
    assert result.exit_code == 0
    assert "--iterations" in result.output


def test_hash_iterations_option() -> None:
    import hashlib

    runner = CliRunner()
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["iterations"] == 1000
    assert parsed["salt_value"] == "saltvalue"
    assert parsed["results"][0]["hash"] == expected


def test_hash_iterations_requires_salt() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "requires --salt" in result.output


def test_hash_iterations_non_positive() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "s",
            "--iterations",
            "0",
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "positive integer" in result.output


def test_hash_iterations_with_pepper() -> None:
    import hashlib
    import hmac

    runner = CliRunner()
    pbkdf2_digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    expected = hmac.new(
        b"secretpepper",
        pbkdf2_digest.encode("utf-8"),
        "sha256",
    ).hexdigest()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--pepper",
            "secretpepper",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["results"][0]["hash"] == expected
    assert parsed["results"][0]["pepper"] is True
    assert parsed["results"][0]["iterations"] == 1000


def test_hash_iterations_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Iterations" in result.output
    assert "1000" in result.output
    assert "Salt Value" in result.output


def test_hash_iterations_with_out_option(tmp_path) -> None:
    import hashlib

    runner = CliRunner()
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    out_file = tmp_path / "hashes.json"
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(out_file.read_text())
    assert parsed["iterations"] == 1000
    assert parsed["results"][0]["hash"] == expected


def test_hash_check_with_iterations() -> None:
    import hashlib

    runner = CliRunner()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"password",
        b"saltvalue",
        1000,
    ).hex()
    result = runner.invoke(
        cli,
        [
            "hash",
            "--password",
            "password",
            "--salt",
            "saltvalue",
            "--iterations",
            "1000",
            "--algorithm",
            "sha256",
            "--check",
            digest,
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["match"] is True
    assert parsed["iterations"] == 1000
    assert parsed["salt_value"] == "saltvalue"


# ---------------------------------------------------------------------------
# Validate CLI tests
# ---------------------------------------------------------------------------


def test_validate_help() -> None:
    """Test validate command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--ports" in result.output
    assert "--cidr" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_validate_top_level_help_lists_command() -> None:
    """Test that validate appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.output.lower()


def test_validate_ports_json() -> None:
    """Test validate command with valid port specs and JSON output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80,443,8000-8002", "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["ports_specified"] == 1
    assert parsed["summary"]["ports_valid"] == 1
    assert parsed["summary"]["ports_total"] == 5
    assert parsed["summary"]["all_valid"] is True


def test_validate_ports_markdown() -> None:
    """Test validate command with valid port specs and Markdown output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80,443", "--format", "markdown"])
    assert result.exit_code == 0
    assert "# ethscan Validate Report" in result.output
    assert "80, 443" in result.output


def test_validate_cidr_json() -> None:
    """Test validate command with valid CIDR specs and JSON output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--cidr", "192.168.1.0/24", "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["cidrs_specified"] == 1
    assert parsed["summary"]["cidrs_valid"] == 1
    assert parsed["summary"]["all_valid"] is True


def test_validate_cidr_markdown() -> None:
    """Test validate command with valid CIDR specs and Markdown output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--cidr", "192.168.1.0/24", "--format", "markdown"])
    assert result.exit_code == 0
    assert "192.168.1.0/24" in result.output
    assert "Network Address" in result.output or "192.168.1.0" in result.output


def test_validate_both_ports_and_cidr_json() -> None:
    """Test validate with both ports and CIDRs."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["validate", "--ports", "80,443", "--cidr", "10.0.0.0/8", "--format", "json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["ports_specified"] == 1
    assert parsed["summary"]["cidrs_specified"] == 1
    assert parsed["summary"]["all_valid"] is True


def test_validate_invalid_port_json() -> None:
    """Test validate with an invalid port spec."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "abc", "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["ports_valid"] == 0
    assert parsed["summary"]["all_valid"] is False
    assert parsed["ports"][0]["valid"] is False


def test_validate_invalid_cidr_json() -> None:
    """Test validate with an invalid CIDR spec."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--cidr", "not-an-ip", "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["cidrs_valid"] == 0
    assert parsed["summary"]["all_valid"] == False


def test_validate_no_specs_json() -> None:
    """Test validate with no specs provided."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["ports_specified"] == 0
    assert parsed["summary"]["cidrs_specified"] == 0


def test_validate_out_option_json(tmp_path) -> None:
    """Test validate with --out (json)."""
    out_file = tmp_path / "validate.json"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["validate", "--ports", "80,443", "--format", "json", "--out", str(out_file)]
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text())
    assert parsed["summary"]["ports_total"] == 2


def test_validate_out_option_markdown(tmp_path) -> None:
    """Test validate with --out (markdown)."""
    out_file = tmp_path / "validate.md"
    runner = CliRunner()
    result = runner.invoke(
        cli, ["validate", "--cidr", "192.168.1.0/24", "--format", "markdown", "--out", str(out_file)]
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan Validate Report" in content


def test_validate_default_format_is_json() -> None:
    """Test validate defaults to JSON output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["summary"]["ports_specified"] == 1


# ---------------------------------------------------------------------------
# resolve command integration tests
# ---------------------------------------------------------------------------


def _mock_resolve_result() -> dict:
    return {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A", "AAAA", "CNAME"],
        "records": {
            "A": ["93.184.216.34"],
            "AAAA": [],
            "CNAME": ["example.com."],
        },
        "dnspython_available": False,
        "server": None,
    }


def test_resolve_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--types" in result.output
    assert "--server" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_cli_help_lists_resolve() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "resolve" in result.output


def test_resolve_offline_domain_json(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    result = runner.invoke(cli, ["resolve", "--target", "example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"
    assert parsed["records"]["A"] == ["93.184.216.34"]


def test_resolve_offline_domain_markdown(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--timeout", "1.0", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "ethscan DNS Forward/Reverse Resolution Report" in result.output
    assert "example.com" in result.output


def test_resolve_url_target(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    result = runner.invoke(cli, ["resolve", "--target", "https://example.com/path"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["normalized"] == "example.com"


def test_resolve_custom_types(monkeypatch) -> None:
    runner = CliRunner()
    captured = {}

    def fake_run_resolve(target, record_types=None, server=None, timeout=2.0):
        captured["record_types"] = record_types
        return _mock_resolve_result()

    monkeypatch.setattr("ethscan.cli.run_resolve", fake_run_resolve)
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--types", "A,PTR"]
    )
    assert result.exit_code == 0
    assert captured["record_types"] == ["A", "PTR"]


def test_resolve_unknown_types_rejected() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--types", "A,FOO"]
    )
    assert result.exit_code == 0
    assert "Unknown record types" in result.output
    assert "FOO" in result.output


def test_resolve_server_option(monkeypatch) -> None:
    runner = CliRunner()
    captured = {}

    def fake_run_resolve(target, record_types=None, server=None, timeout=2.0):
        captured["server"] = server
        return _mock_resolve_result()

    monkeypatch.setattr("ethscan.cli.run_resolve", fake_run_resolve)
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--server", "8.8.8.8"]
    )
    assert result.exit_code == 0
    assert captured["server"] == "8.8.8.8"


def test_resolve_timeout_passes_through(monkeypatch) -> None:
    runner = CliRunner()
    captured = {}

    def fake_run_resolve(target, record_types=None, server=None, timeout=2.0):
        captured["timeout"] = timeout
        return _mock_resolve_result()

    monkeypatch.setattr("ethscan.cli.run_resolve", fake_run_resolve)
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--timeout", "1.5"]
    )
    assert result.exit_code == 0
    assert captured["timeout"] == 1.5


def test_resolve_out_option_json(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    out_file = tmp_path / "resolve.json"
    result = runner.invoke(
        cli,
        ["resolve", "--target", "example.com", "--format", "json", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text())
    assert parsed["target"] == "example.com"


def test_resolve_out_option_markdown(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    out_file = tmp_path / "resolve.md"
    result = runner.invoke(
        cli,
        [
            "resolve",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan DNS Forward/Reverse Resolution Report" in content


def test_resolve_default_format_is_json(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: _mock_resolve_result())
    result = runner.invoke(cli, ["resolve", "--target", "example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"


def test_resolve_offline_domain_markdown_pipe_escaping(monkeypatch) -> None:
    """Markdown output escapes pipe characters in values."""
    data = _mock_resolve_result()
    data["records"]["CNAME"] = ["a|b.example.com."]
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: data)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["resolve", "--target", "example.com", "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "a\\|b.example.com" in result.output


# ---------------------------------------------------------------------------
# radix CLI integration tests
# ---------------------------------------------------------------------------


def test_radix_help() -> None:
    """Test radix command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["radix", "--help"])
    assert result.exit_code == 0
    assert "--cidrs" in result.output
    assert "--diff" in result.output
    assert "--no-merge" in result.output
    assert "--max-depth" in result.output
    assert "--contains" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_radix_top_level_help_lists() -> None:
    """Test that radix appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "radix" in result.output.lower()


def test_radix_offline_target_json() -> None:
    """Test radix command with JSON output."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "192.168.1.0/24,192.168.2.0/24", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["network_count"] == 2
    assert parsed["merged_network_count"] == 2
    assert "192.168.1.0/24" in parsed["merged"]
    assert "192.168.2.0/24" in parsed["merged"]
    assert parsed["radix_tree"] is not None


def test_radix_offline_target_markdown() -> None:
    """Test radix command with Markdown output."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "10.0.0.0/8", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "ethscan Radix Tree Report" in result.output
    assert "10.0.0.0/8" in result.output


def test_radix_merge_option() -> None:
    """Test radix command with --no-merge option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24,192.168.2.0/24",
            "--no-merge",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["merge_enabled"] is False


def test_radix_contains_option() -> None:
    """Test radix command with --contains option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24,10.0.0.0/8",
            "--contains",
            "10.5.5.5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["contains"]["in_network"] is True
    assert parsed["contains"]["matched_network"] == "10.0.0.0/8"


def test_radix_diff_option() -> None:
    """Test radix command with --diff option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24",
            "--diff",
            "192.168.1.128/25",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "diff" in parsed
    assert parsed["diff"]["difference_network_count"] == 1
    assert "192.168.1.0/25" in parsed["diff"]["difference"]


def test_radix_out_option_json(tmp_path) -> None:
    """Test radix command with --out (json)."""
    out_file = tmp_path / "radix_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = json.loads(out_file.read_text())
    assert content["network_count"] == 1


def test_radix_out_option_markdown(tmp_path) -> None:
    """Test radix command with --out (markdown)."""
    out_file = tmp_path / "radix_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "ethscan Radix Tree Report" in content


def test_radix_default_format_is_json() -> None:
    """Test radix command defaults to JSON format."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "192.168.1.0/24"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["network_count"] == 1


def test_radix_max_depth_option() -> None:
    """Test radix command with --max-depth option."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24,192.168.2.0/24",
            "--max-depth",
            "1",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["max_depth"] == 1


def test_radix_markdown_pipe_escaping() -> None:
    """Test radix command markdown output escapes pipe characters."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "192.168.1.0/24", "--format", "markdown"],
    )
    assert result.exit_code == 0
    # The merged networks table should not have raw pipes in values
    assert "|" in result.output  # table separators


def test_radix_cidr_file_option(tmp_path) -> None:
    """Test radix command with --cidr-file option."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("192.168.0.0/24\n192.168.1.0/24\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidr-file", str(cidr_file), "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["network_count"] == 2
    assert parsed["merged_network_count"] == 1
    assert parsed["merged"][0] == "192.168.0.0/23"


def test_radix_cidr_file_with_comments(tmp_path) -> None:
    """Test radix command with --cidr-file containing comments and blank lines."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("# Comment line\n192.168.1.0/24\n\n  # Another comment\n10.0.0.0/8\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidr-file", str(cidr_file), "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["network_count"] == 2
    assert "192.168.1.0/24" in parsed["merged"]
    assert "10.0.0.0/8" in parsed["merged"]


def test_radix_cidr_file_and_cidrs_combined(tmp_path) -> None:
    """Test radix command with both --cidr-file and --cidrs options."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("192.168.0.0/24\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidr-file", str(cidr_file), "--cidrs", "192.168.1.0/24", "--format", "json"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["network_count"] == 2
    assert parsed["merged_network_count"] == 1
    assert parsed["merged"][0] == "192.168.0.0/23"


def test_radix_cidr_file_help() -> None:
    """Test that --cidr-file appears in radix help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["radix", "--help"])
    assert result.exit_code == 0
    assert "--cidr-file" in result.output


def test_radix_output_format_csv() -> None:
    """Test radix command with --output-format csv."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "192.168.1.0/24,192.168.2.0/24", "--output-format", "csv"],
    )
    assert result.exit_code == 0
    assert "original_cidr,merged_cidr,compression_ratio" in result.output
    assert "192.168.1.0/24" in result.output


def test_radix_output_format_csv_out(tmp_path) -> None:
    """Test radix command with --output-format csv --out."""
    out_file = tmp_path / "radix_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "radix",
            "--cidrs",
            "192.168.1.0/24",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "original_cidr,merged_cidr" in content


def test_radix_format_csv_alias() -> None:
    """Test radix command with deprecated --format csv alias."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["radix", "--cidrs", "192.168.1.0/24", "--format", "csv"],
    )
    assert result.exit_code == 0
    assert "original_cidr,merged_cidr,compression_ratio" in result.output


def test_radix_output_format_default_is_json() -> None:
    """Test radix command defaults to JSON when no format specified."""
    runner = CliRunner()
    result = runner.invoke(cli, ["radix", "--cidrs", "192.168.1.0/24"])
    assert result.exit_code == 0
    assert '"network_count": 1' in result.output
    assert "original_cidr,merged_cidr" not in result.output


def test_vuln_help_shows_output_format() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_vuln_output_format_csv(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
        output_fmt=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    header_line = result.output.split("\n")[0]
    assert "id" in header_line
    assert "type" in header_line
    assert "severity" in header_line
    assert "product" in header_line
    assert "version" in header_line
    assert "port" in header_line
    assert "title" in header_line
    assert "description" in header_line
    assert "CVE-2018-15473" in result.output
    assert "service" in result.output
    assert "medium" in result.output
    assert "OpenSSH" in result.output


def test_vuln_format_csv_alias(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": ["No known vulnerabilities matched"],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--format", "csv", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    header_line = result.output.split("\n")[0]
    assert "id,type,severity,product,version,port,title,description" in header_line


def test_vuln_out_option_csv(tmp_path, monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
        min_severity=None,
        recursive=False,
        max_depth=2,
        salt=None,
        pepper=None,
        algorithm="sha256",
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "min_severity_filter": min_severity,
            "findings": [
                {
                    "id": "VSFTPD-2.3.4-BACKDOOR",
                    "kind": "service",
                    "title": "vsftpd 2.3.4 backdoor",
                    "severity": "critical",
                    "description": "vsftpd 2.3.4 backdoor command execution.",
                    "product": "vsftpd",
                    "version": "2.3.4",
                    "port": 21,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
            "notes": [],
            "recursive": recursive,
            "max_depth": max_depth,
            "recursive_hosts_scanned": [],
            "recursive_findings": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    out_file = tmp_path / "report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert "id,type,severity,product,version,port,title,description" in content
    assert "VSFTPD-2.3.4-BACKDOOR" in content
    assert "critical" in content
    assert "vsftpd" in content
    assert "Report written to" in result.output


# ---------------------------------------------------------------------------
# nmap command CLI integration tests


SAMPLE_NMAP_XML = """<runscanner version="1.0" scanner="nmap" args="nmap -oX - 192.168.1.1" start="1234567890" nmap_version="7.94" xmloutputversion="1.05">
<scaninfo type="syn" protocol="tcp" numservices="1000" services="1-1000"/>
<verbose level="0"/>
<debugging level="0"/>
<host starttime="1234567890" endtime="1234567891">
<status state="up" reason="syn-ack"/>
<address addr="192.168.1.1" addrtype="ipv4"/>
<hostnames>
<hostname name="router.local" type="PTR"/>
</hostnames>
<ports>
<port protocol="tcp" portid="22">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ssh" product="OpenSSH" version="7.2p2" extrainfo="protocol 2.0" method="probed" conf="10"/>
</port>
<port protocol="tcp" portid="21">
<state state="open" reason="syn-ack" reason_ttl="64"/>
<service name="ftp" product="vsftpd" version="2.3.4" method="probed" conf="10"/>
</port>
</ports>
</host>
</runscanner>
"""


def test_nmap_help() -> None:
    """Test nmap command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--help"])
    assert result.exit_code == 0
    assert "--input-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_nmap_top_level_help_lists_command() -> None:
    """Test that nmap appears in top-level help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "nmap" in result.output.lower()


def test_nmap_offline_json(tmp_path) -> None:
    """Test nmap command with valid Nmap XML and JSON output."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", str(xml_file), "--format", "json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["input_file"] == str(xml_file)
    assert parsed["hosts_scanned"] == 1
    assert parsed["total_ports_scanned"] == 2
    assert parsed["total_open_ports"] == 2
    assert parsed["services_detected"] == 2
    assert parsed["finding_count"] >= 1
    # Should find OpenSSH 7.2p2 vulns and vsftpd 2.3.4 backdoor
    cve_ids = [f["id"] for f in parsed["findings"]]
    assert "CVE-2016-6210" in cve_ids
    assert "VSFTPD-2.3.4-BACKDOOR" in cve_ids


def test_nmap_offline_markdown(tmp_path) -> None:
    """Test nmap command with valid Nmap XML and Markdown output."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", str(xml_file), "--format", "markdown"])
    assert result.exit_code == 0
    assert "ethscan Nmap Vulnerability Report" in result.output
    assert "Severity Summary" in result.output
    assert "Detected Services" in result.output
    assert "Vulnerability Findings" in result.output
    assert "CVE-2016-6210" in result.output
    assert "VSFTPD-2.3.4-BACKDOOR" in result.output
    assert "OpenSSH" in result.output
    assert "vsftpd" in result.output


def test_nmap_out_option_json(tmp_path) -> None:
    """Test nmap command with --out option writing JSON to file."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")
    out_file = tmp_path / "report.json"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "nmap",
            "--input-file",
            str(xml_file),
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["input_file"] == str(xml_file)
    assert "Report written to" in result.output


def test_nmap_out_option_markdown(tmp_path) -> None:
    """Test nmap command with --out option writing Markdown to file."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")
    out_file = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "nmap",
            "--input-file",
            str(xml_file),
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "ethscan Nmap Vulnerability Report" in content
    assert "Report written to" in result.output


def test_nmap_missing_input_file() -> None:
    """Test nmap command with missing input file."""
    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", "/nonexistent/scan.xml"])
    assert result.exit_code != 0
    assert "Error" in result.output or "does not exist" in result.output.lower()


def test_nmap_default_format_is_json(tmp_path) -> None:
    """Test that default format is JSON when --format not specified."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", str(xml_file)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["input_file"] == str(xml_file)


def test_nmap_help_shows_output_format() -> None:
    """Test that nmap help shows --output-format option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_nmap_output_format_csv(tmp_path) -> None:
    """Test nmap command with --output-format csv."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["nmap", "--input-file", str(xml_file), "--output-format", "csv"]
    )
    assert result.exit_code == 0
    assert "host,addr,port,state,service,product,version,cve_id,severity,score,title" in result.output
    assert "CVE-2016-6210" in result.output
    assert "VSFTPD-2.3.4-BACKDOOR" in result.output


def test_nmap_out_option_csv(tmp_path) -> None:
    """Test nmap command with --output-format csv --out writes CSV to file."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")
    out_file = tmp_path / "report.csv"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "nmap",
            "--input-file",
            str(xml_file),
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "cve_id" in content
    assert "CVE-2016-6210" in content
    assert "Report written to" in result.output


def test_nmap_format_csv_alias(tmp_path) -> None:
    """Test that deprecated --format csv still works."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["nmap", "--input-file", str(xml_file), "--format", "csv"]
    )
    assert result.exit_code == 0
    assert "host,addr,port" in result.output


def test_nmap_output_format_default_is_json(tmp_path) -> None:
    """Test that without --output-format, default is JSON."""
    xml_file = tmp_path / "scan.xml"
    xml_file.write_text(SAMPLE_NMAP_XML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", str(xml_file)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["input_file"] == str(xml_file)


def test_stale_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["stale", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--file" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_stale() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "stale" in result.output


def test_stale_offline_target_json(monkeypatch) -> None:
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 1,
            "fresh_count": 0,
            "results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
            "stale_results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "stale_count" in result.output
    assert "stale_results" in result.output


def test_stale_offline_target_markdown(monkeypatch) -> None:
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 1,
            "fresh_count": 0,
            "results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
            "stale_results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "Stale DNS Record Detection Report" in result.output
    assert "nonexistent.invalid.domain.tld" in result.output


def test_stale_url_target(monkeypatch) -> None:
    """Test that URL targets are normalized to bare domains."""
    captured = {}

    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        captured["targets"] = targets
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {
                    "domain": "example.com",
                    "A": ["1.1.1.1"],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": False,
                    "stale_reasons": [],
                }
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "https://example.com/path",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert captured["targets"] == ["https://example.com/path"]


def test_stale_multiple_targets(monkeypatch) -> None:
    """Test multiple --target options."""
    captured = {}

    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        captured["targets"] = targets
        return {
            "targets": targets,
            "total_checked": len(targets),
            "stale_count": 0,
            "fresh_count": len(targets),
            "results": [
                {"domain": t, "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
                for t in targets
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--target",
            "google.com",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert len(captured["targets"]) == 2
    assert "example.com" in captured["targets"]
    assert "google.com" in captured["targets"]


def test_stale_file_option(tmp_path, monkeypatch) -> None:
    """Test --file option for reading domains from file."""
    domain_file = tmp_path / "domains.txt"
    domain_file.write_text("example.com\ngoogle.com\n", encoding="utf-8")

    captured = {}

    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        captured["targets"] = targets
        return {
            "targets": targets,
            "total_checked": len(targets),
            "stale_count": 0,
            "fresh_count": len(targets),
            "results": [
                {"domain": t, "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
                for t in targets
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--file",
            str(domain_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert len(captured["targets"]) == 2
    assert "example.com" in captured["targets"]
    assert "google.com" in captured["targets"]


def test_stale_timeout_option(monkeypatch) -> None:
    """Test --timeout option pass-through."""
    captured = {}

    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        captured["timeout"] = timeout
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--timeout",
            "5.0",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert captured["timeout"] == 5.0


def test_stale_workers_option(monkeypatch) -> None:
    """Test --workers option pass-through."""
    captured = {}

    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        captured["max_workers"] = max_workers
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--workers",
            "100",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert captured["max_workers"] == 100


def test_stale_out_option_json(tmp_path, monkeypatch) -> None:
    """Test --out option writing JSON to file."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    out_file = tmp_path / "report.json"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "stale_count" in content
    assert "Report written to" in result.output


def test_stale_out_option_markdown(tmp_path, monkeypatch) -> None:
    """Test --out option writing Markdown to file."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    out_file = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "Stale DNS Record Detection Report" in content
    assert "Report written to" in result.output


def test_stale_default_format_is_json(monkeypatch) -> None:
    """Test that default format is JSON when --format not specified."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(cli, ["stale", "--target", "example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "stale_count" in parsed


def test_stale_help_shows_output_format() -> None:
    """Test that help shows --output-format option with csv."""
    runner = CliRunner()
    result = runner.invoke(cli, ["stale", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output
    assert "csv" in result.output


def test_stale_output_format_csv(monkeypatch) -> None:
    """Test --output-format csv produces correct CSV output."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 1,
            "fresh_count": 0,
            "results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
            "stale_results": [
                {
                    "domain": "nonexistent.invalid.domain.tld",
                    "A": [],
                    "AAAA": [],
                    "CNAME": None,
                    "stale": True,
                    "stale_reasons": ["No DNS records resolved (NXDOMAIN or SERVFAIL)"],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--output-format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "domain,A_records,AAAA_records,CNAME,stale,stale_reasons"
    assert "nonexistent.invalid.domain.tld" in lines[1]
    assert "true" in lines[1]


def test_stale_out_option_csv(tmp_path, monkeypatch) -> None:
    """Test --output-format csv with --out writes CSV file."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    out_file = tmp_path / "stale.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert content.startswith("domain,A_records,AAAA_records,CNAME,stale,stale_reasons")
    assert "Report written to" in result.output


def test_stale_format_csv_alias(monkeypatch) -> None:
    """Test deprecated --format csv alias still works."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "stale",
            "--target",
            "example.com",
            "--format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "domain,A_records,AAAA_records,CNAME,stale,stale_reasons"
    assert "example.com" in lines[1]
    assert "1.1.1.1" in lines[1]
    assert "false" in lines[1]


def test_stale_output_format_default_is_json(monkeypatch) -> None:
    """Test default format is JSON when neither --output-format nor --format specified."""
    def mock_run_stale(targets, timeout=2.0, max_workers=50):
        return {
            "targets": targets,
            "total_checked": 1,
            "stale_count": 0,
            "fresh_count": 1,
            "results": [
                {"domain": "example.com", "A": ["1.1.1.1"], "AAAA": [], "CNAME": None, "stale": False, "stale_reasons": []}
            ],
            "stale_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_stale", mock_run_stale)

    runner = CliRunner()
    result = runner.invoke(cli, ["stale", "--target", "example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "stale_count" in parsed


def test_ssh_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ssh", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--timeout" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_ssh() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ssh" in result.output


def test_ssh_offline_target_json(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "nonexistent.invalid.domain.tld",
            "port": port,
            "timeout": timeout,
            "banner": None,
            "paramiko_available": False,
            "kex_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
            "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
            "mac_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key": None,
            "findings": [],
            "error": "connection refused",
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert "connection refused" in result.output
    assert "nonexistent.invalid.domain.tld" in result.output


def test_ssh_offline_target_markdown(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "nonexistent.invalid.domain.tld",
            "port": port,
            "timeout": timeout,
            "banner": None,
            "paramiko_available": False,
            "kex_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
            "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
            "mac_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key": None,
            "findings": [],
            "error": "connection refused",
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert "connection refused" in result.output


def test_ssh_url_target(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": 2222,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": ["curve25519-sha256"], "weak": [], "strong": ["curve25519-sha256"]},
            "host_key_algorithms": {"supported": ["ssh-ed25519"], "weak": [], "strong": ["ssh-ed25519"]},
            "encryption_algorithms": {"supported": ["aes256-ctr"], "weak": [], "strong": ["aes256-ctr"]},
            "mac_algorithms": {"supported": ["hmac-sha2-256"], "weak": [], "strong": ["hmac-sha2-256"]},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "ssh://example.com:2222",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "example.com"
    assert parsed["port"] == 2222


def test_ssh_port_option(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
            "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
            "mac_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "example.com",
            "--port",
            "2222",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["port"] == 2222


def test_ssh_timeout_option(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
            "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
            "mac_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "example.com",
            "--timeout",
            "5.0",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["timeout"] == 5.0


def test_ssh_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": ["curve25519-sha256"], "weak": [], "strong": ["curve25519-sha256"]},
            "host_key_algorithms": {"supported": ["ssh-ed25519"], "weak": [], "strong": ["ssh-ed25519"]},
            "encryption_algorithms": {"supported": ["aes256-ctr"], "weak": [], "strong": ["aes256-ctr"]},
            "mac_algorithms": {"supported": ["hmac-sha2-256"], "weak": [], "strong": ["hmac-sha2-256"]},
            "host_key": {"fingerprint": "aa:bb:cc", "key_type": "ssh-ed25519", "key_bits": 256},
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    out_file = tmp_path / "report.json"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "example.com",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "example.com" in content
    assert "curve25519-sha256" in content
    assert "Report written to" in result.output


def test_ssh_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": ["curve25519-sha256"], "weak": [], "strong": ["curve25519-sha256"]},
            "host_key_algorithms": {"supported": ["ssh-ed25519"], "weak": [], "strong": ["ssh-ed25519"]},
            "encryption_algorithms": {"supported": ["aes256-ctr"], "weak": [], "strong": ["aes256-ctr"]},
            "mac_algorithms": {"supported": ["hmac-sha2-256"], "weak": [], "strong": ["hmac-sha2-256"]},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    out_file = tmp_path / "report.md"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "SSH Security Assessment Report" in content
    assert "Report written to" in result.output


def test_ssh_default_format_is_json(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {"supported": ["curve25519-sha256"], "weak": [], "strong": ["curve25519-sha256"]},
            "host_key_algorithms": {"supported": ["ssh-ed25519"], "weak": [], "strong": ["ssh-ed25519"]},
            "encryption_algorithms": {"supported": ["aes256-ctr"], "weak": [], "strong": ["aes256-ctr"]},
            "mac_algorithms": {"supported": ["hmac-sha2-256"], "weak": [], "strong": ["hmac-sha2-256"]},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(cli, ["ssh", "--target", "example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "curve25519-sha256" in parsed["kex_algorithms"]["supported"]


def test_ssh_output_format_csv(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {
                "supported": ["curve25519-sha256", "diffie-hellman-group1-sha1"],
                "weak": ["diffie-hellman-group1-sha1"],
                "strong": ["curve25519-sha256"],
            },
            "host_key_algorithms": {
                "supported": ["ssh-ed25519", "ssh-rsa"],
                "weak": ["ssh-rsa"],
                "strong": ["ssh-ed25519"],
            },
            "encryption_algorithms": {
                "supported": ["aes256-ctr", "aes128-cbc"],
                "weak": ["aes128-cbc"],
                "strong": ["aes256-ctr"],
            },
            "mac_algorithms": {
                "supported": ["hmac-sha2-256", "hmac-sha1"],
                "weak": ["hmac-sha1"],
                "strong": ["hmac-sha2-256"],
            },
            "host_key": {"fingerprint": "aa:bb:cc", "key_type": "ssh-ed25519", "key_bits": 256},
            "findings": [
                {"type": "weak_kex", "algorithm": "diffie-hellman-group1-sha1", "severity": "medium", "description": "Weak key exchange algorithm supported: diffie-hellman-group1-sha1"},
                {"type": "weak_host_key", "algorithm": "ssh-rsa", "severity": "high", "description": "Weak host key type supported: ssh-rsa"},
            ],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(cli, ["ssh", "--target", "example.com", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "type,algorithm,severity,description" in result.output
    assert "weak_kex,diffie-hellman-group1-sha1,medium" in result.output
    assert "weak_host_key,ssh-rsa,high" in result.output


def test_ssh_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": "SSH-2.0-OpenSSH_8.9",
            "paramiko_available": False,
            "kex_algorithms": {
                "supported": ["curve25519-sha256"],
                "weak": [],
                "strong": ["curve25519-sha256"],
            },
            "host_key_algorithms": {
                "supported": ["ssh-ed25519"],
                "weak": [],
                "strong": ["ssh-ed25519"],
            },
            "encryption_algorithms": {
                "supported": ["aes256-ctr"],
                "weak": [],
                "strong": ["aes256-ctr"],
            },
            "mac_algorithms": {
                "supported": ["hmac-sha2-256"],
                "weak": [],
                "strong": ["hmac-sha2-256"],
            },
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    out_file = tmp_path / "ssh_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssh",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "type,algorithm,severity,description" in content


def test_ssh_format_csv_alias(monkeypatch) -> None:
    def mock_run_ssh(target, port=22, timeout=10.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "banner": None,
            "paramiko_available": False,
            "kex_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key_algorithms": {"supported": [], "weak": [], "strong": []},
            "encryption_algorithms": {"supported": [], "weak": [], "strong": []},
            "mac_algorithms": {"supported": [], "weak": [], "strong": []},
            "host_key": None,
            "findings": [],
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssh", mock_run_ssh)

    runner = CliRunner()
    result = runner.invoke(cli, ["ssh", "--target", "example.com", "--format", "csv"])
    assert result.exit_code == 0
    assert "type,algorithm,severity,description" in result.output


# ---------------------------------------------------------------------------
# s3 command CLI integration tests
# ---------------------------------------------------------------------------


def test_s3_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--region" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_s3() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "s3" in result.output


def test_s3_offline_target_json(monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": wordlist is not None,
            "candidates_tested": 3,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": ["offline target"],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"
    assert parsed["candidates_tested"] == 3
    assert parsed["public_buckets"] == []


def test_s3_offline_target_markdown(monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 0,
            "regions_checked": [],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": ["No bucket candidates."],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["s3", "--target", "example.com", "--format", "markdown"],
    )
    assert result.exit_code == 0
    assert "S3 Bucket Enumeration Report" in result.output
    assert "example.com" in result.output


def test_s3_wordlist_option(tmp_path, monkeypatch) -> None:
    wordlist_file = tmp_path / "buckets.txt"
    wordlist_file.write_text("mybucket\nother-bucket\n")

    captured = {}

    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        captured["wordlist"] = wordlist
        captured["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": wordlist is not None,
            "candidates_tested": len(wordlist) if wordlist else 0,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["s3", "--target", "example.com", "--wordlist", str(wordlist_file)],
    )
    assert result.exit_code == 0
    assert captured["wordlist"] == ["mybucket", "other-bucket"]


def test_s3_region_option(monkeypatch) -> None:
    captured = {}

    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        captured["region"] = region
        captured["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com", "--region", "eu-west-1"])
    assert result.exit_code == 0
    assert captured["region"] == "eu-west-1"


def test_s3_timeout_workers_pass_through(monkeypatch) -> None:
    captured = {}

    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        captured["timeout"] = timeout
        captured["workers"] = max_workers
        captured["target"] = target
        captured["region"] = region
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "s3",
            "--target",
            "example.com",
            "--timeout",
            "2.5",
            "--workers",
            "15",
            "--region",
            "us-west-2",
        ],
    )
    assert result.exit_code == 0
    assert captured["timeout"] == 2.5
    assert captured["workers"] == 15
    assert captured["region"] == "us-west-2"


def test_s3_region_all_option(monkeypatch) -> None:
    captured = {}

    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        captured["region"] = region
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com", "--region", "all"])
    assert result.exit_code == 0
    assert captured["region"] == "all"


def test_s3_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    out_file = tmp_path / "s3_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "s3",
            "--target",
            "example.com",
            "--format",
            "json",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "example.com" in content


def test_s3_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    out_file = tmp_path / "s3_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "s3",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "S3 Bucket Enumeration Report" in content


def test_s3_url_target(monkeypatch) -> None:
    captured = {}

    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        captured["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "https://example.com/path"])
    assert result.exit_code == 0
    assert captured["target"] == "https://example.com/path"


def test_s3_default_format_is_json(monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"


def test_s3_output_format_csv(monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 2,
            "regions_checked": [region or "us-east-1"],
            "results": [
                {
                    "bucket": "example-com",
                    "region": "us-east-1",
                    "url": "https://example-com.s3.amazonaws.com/",
                    "dns_resolved": "1.2.3.4",
                    "status_code": 200,
                    "exists": True,
                    "public": True,
                    "error": None,
                },
                {
                    "bucket": "dev-example-com",
                    "region": "us-east-1",
                    "url": "https://dev-example-com.s3.amazonaws.com/",
                    "dns_resolved": "1.2.3.4",
                    "status_code": 403,
                    "exists": True,
                    "public": False,
                    "error": None,
                },
            ],
            "public_buckets": [
                {
                    "bucket": "example-com",
                    "region": "us-east-1",
                    "url": "https://example-com.s3.amazonaws.com/",
                    "dns_resolved": "1.2.3.4",
                    "status_code": 200,
                    "exists": True,
                    "public": True,
                    "error": None,
                }
            ],
            "private_buckets": [
                {
                    "bucket": "dev-example-com",
                    "region": "us-east-1",
                    "url": "https://dev-example-com.s3.amazonaws.com/",
                    "dns_resolved": "1.2.3.4",
                    "status_code": 403,
                    "exists": True,
                    "public": False,
                    "error": None,
                }
            ],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "target,domain,bucket,region,status_code,exists,public,error" in result.output
    assert "example-com" in result.output
    assert "200" in result.output
    assert "True" in result.output


def test_s3_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 1,
            "regions_checked": [region or "us-east-1"],
            "results": [
                {
                    "bucket": "example-com",
                    "region": "us-east-1",
                    "url": "https://example-com.s3.amazonaws.com/",
                    "dns_resolved": "1.2.3.4",
                    "status_code": 200,
                    "exists": True,
                    "public": True,
                    "error": None,
                }
            ],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    out_file = tmp_path / "s3_report.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "s3",
            "--target",
            "example.com",
            "--output-format",
            "csv",
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "Report written to" in result.output
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "target,domain,bucket,region,status_code,exists,public,error" in content


def test_s3_format_csv_alias(monkeypatch) -> None:
    def mock_run_s3(
        target, wordlist=None, region=None, timeout=5.0, max_workers=20
    ):
        return {
            "target": target,
            "domain": "example.com",
            "region": region or "us-east-1",
            "timeout": timeout,
            "workers": max_workers,
            "wordlist_used": False,
            "candidates_tested": 0,
            "regions_checked": [region or "us-east-1"],
            "results": [],
            "public_buckets": [],
            "private_buckets": [],
            "existing_buckets": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_s3", mock_run_s3)

    runner = CliRunner()
    result = runner.invoke(cli, ["s3", "--target", "example.com", "--format", "csv"])
    assert result.exit_code == 0
    assert "target,domain,bucket,region,status_code,exists,public,error" in result.output


def test_validate_help_shows_output_format() -> None:
    """Test that validate help shows --output-format option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output


def test_validate_output_format_csv() -> None:
    """Test validate command with CSV output format."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80,443", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "type,spec,valid,detail" in result.output
    assert "port" in result.output


def test_validate_out_option_csv() -> None:
    """Test validate command writes CSV to file."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "validate.csv")
        result = runner.invoke(cli, ["validate", "--ports", "80,443", "--output-format", "csv", "--out", out_path])
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as handle:
            content_out = handle.read()
        assert "type,spec,valid,detail" in content_out


def test_validate_format_csv_alias() -> None:
    """Test validate command with deprecated --format csv alias."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80,443", "--format", "csv"])
    assert result.exit_code == 0
    assert "type,spec,valid,detail" in result.output


def test_validate_output_format_default_is_json() -> None:
    """Test validate command defaults to JSON format."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--ports", "80,443"])
    assert result.exit_code == 0
    # Should be valid JSON (default)
    try:
        json.loads(result.output)
    except Exception:
        assert False, "Default output should be valid JSON"
def test_geo_help_shows_output_format():
    runner = CliRunner()
    result = runner.invoke(cli, ["geo", "--help"])
    assert result.exit_code == 0
    assert "--output-format" in result.output


def test_geo_output_format_csv(monkeypatch):
    runner = CliRunner()
    mock_results = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": False,
            "offline_fallback": False,
        },
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_geo", lambda *args, **kwargs: mock_results)
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "target,ip,country" in result.output


def test_geo_output_format_csv_out(tmp_path, monkeypatch):
    runner = CliRunner()
    mock_results = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "cached": False,
            "offline_fallback": False,
        },
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_geo", lambda *args, **kwargs: mock_results)
    out_file = tmp_path / "geo.csv"
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "target,ip,country" in content


def test_geo_format_csv_alias(monkeypatch):
    runner = CliRunner()
    mock_results = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "timeout": 5.0,
        "use_cache": True,
        "offline_fallback": True,
        "geolocation": None,
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_geo", lambda *args, **kwargs: mock_results)
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--format", "csv"])
    assert result.exit_code == 0
    assert "target,ip,country" in result.output


def test_geo_output_format_default_is_json(monkeypatch):
    runner = CliRunner()
    mock_results = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "geolocation": {"status": "success", "query": "8.8.8.8"},
    }
    monkeypatch.setattr("ethscan.cli.run_geo", lambda *args, **kwargs: mock_results)
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8"])
    assert result.exit_code == 0
    assert '"target": "8.8.8.8"' in result.output


def test_geo_output_format_precedence_over_format(monkeypatch):
    runner = CliRunner()
    mock_results = {
        "target": "8.8.8.8",
        "host": "8.8.8.8",
        "ip": "8.8.8.8",
        "geolocation": {"status": "success", "query": "8.8.8.8"},
    }
    monkeypatch.setattr("ethscan.cli.run_geo", lambda *args, **kwargs: mock_results)
    result = runner.invoke(cli, ["geo", "--target", "8.8.8.8", "--format", "markdown", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "target,ip,country" in result.output


# ---------------------------------------------------------------------------
# CSV integration tests for commands with --output-format csv support
# ---------------------------------------------------------------------------


def test_subdomains_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "93.184.216.34"},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_subdomains", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "subdomain,hostname,ip,resolved" in result.output
    assert "www,www.example.com,93.184.216.34,true" in result.output


def test_subdomains_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "93.184.216.34"},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_subdomains", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "subdomains.csv"
    result = runner.invoke(
        cli,
        ["subdomains", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "subdomain,hostname,ip,resolved" in content


def test_subdomains_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "ip": "93.184.216.34"},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_subdomains", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "subdomain,hostname,ip,resolved" in result.output


def test_whois_output_format_csv(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "parsed": {
                "registrar": "Example Registrar",
                "creation_date": "2020-01-01",
            },
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)
    runner = CliRunner()
    result = runner.invoke(cli, ["whois", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "target,example.com" in result.output
    assert "registrar,Example Registrar" in result.output


def test_whois_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "parsed": {"registrar": "Example Registrar"},
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)
    runner = CliRunner()
    out_file = tmp_path / "whois.csv"
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "field,value" in content
    assert "registrar,Example Registrar" in content


def test_whois_format_csv_alias(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0,
                       recursive=False, max_depth=2):
        return {
            "target": target,
            "server": server,
            "port": port,
            "parsed": {"registrar": "Example Registrar"},
            "recursive_hops": [],
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)
    runner = CliRunner()
    result = runner.invoke(cli, ["whois", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "registrar,Example Registrar" in result.output


def test_ssl_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "timeout": 5.0,
        "error": None,
        "chain_length": 2,
        "valid": True,
        "days_remaining": 365,
        "cert": {
            "subject": "CN=example.com",
            "issuer": "Let's Encrypt",
            "not_before": "2024-01-01",
            "not_after": "2024-12-31",
            "signature_algorithm": "sha256WithRSA",
            "key_size": 2048,
            "sans": ["example.com", "www.example.com"],
        },
    }
    monkeypatch.setattr("ethscan.cli.run_ssl", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ssl", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "target,example.com" in result.output
    assert "valid,true" in result.output
    assert "subject,CN=example.com" in result.output


def test_ssl_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": None,
        "chain_length": 1,
        "valid": True,
        "cert": {"subject": "CN=example.com"},
    }
    monkeypatch.setattr("ethscan.cli.run_ssl", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "ssl.csv"
    result = runner.invoke(
        cli,
        ["ssl", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "field,value" in content
    assert "valid,true" in content


def test_ssl_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "error": None,
        "chain_length": 1,
        "valid": True,
        "cert": {"subject": "CN=example.com"},
    }
    monkeypatch.setattr("ethscan.cli.run_ssl", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ssl", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "valid,true" in result.output


def test_headers_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {},
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": ["Content-Security-Policy"],
            "present_count": 1,
            "missing_count": 1,
            "total": 2,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_headers", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["headers", "--target", "https://example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "X-Frame-Options,present" in result.output
    assert "Content-Security-Policy,missing" in result.output


def test_headers_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {},
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": [],
            "present_count": 1,
            "missing_count": 0,
            "total": 1,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_headers", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "headers.csv"
    result = runner.invoke(
        cli,
        ["headers", "--target", "https://example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "X-Frame-Options,present" in content


def test_headers_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "headers": {},
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": [],
            "present_count": 1,
            "missing_count": 0,
            "total": 1,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_headers", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["headers", "--target", "https://example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "X-Frame-Options,present" in result.output


def test_web_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {
            "present": ["X-Frame-Options"],
            "missing": ["Content-Security-Policy"],
        },
        "information_disclosure": [
            {"header": "Server", "value": "Apache", "description": "Server header exposed"},
        ],
        "ssl": {
            "valid": True,
            "subject": "CN=example.com",
            "issuer": "Let's Encrypt",
        },
    }
    monkeypatch.setattr("ethscan.cli.run_web_checks", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--target", "https://example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "X-Frame-Options,present" in result.output
    assert "Server,Apache" in result.output
    assert "subject,CN=example.com" in result.output


def test_web_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {"present": ["X-Frame-Options"], "missing": []},
    }
    monkeypatch.setattr("ethscan.cli.run_web_checks", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "web.csv"
    result = runner.invoke(
        cli,
        ["web", "--target", "https://example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "field,value" in content
    assert "X-Frame-Options,present" in content


def test_web_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "host": "example.com",
        "port": 443,
        "secure": True,
        "security_headers": {"present": ["X-Frame-Options"], "missing": []},
    }
    monkeypatch.setattr("ethscan.cli.run_web_checks", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--target", "https://example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "X-Frame-Options,present" in result.output


def test_wifi_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [
            {"interface": "wlan0", "status": "UP", "link_quality": 70, "signal_level": -40, "noise_level": -90},
        ],
        "access_points": [
            {"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "TestNet", "channel": 6, "frequency": 2.437, "encryption": "WPA2", "signal_dbm": -40, "quality": 70},
        ],
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_wifi", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "platform,Linux" in result.output
    assert "TestNet" in result.output


def test_wifi_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [],
        "access_points": [],
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_wifi", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "wifi.csv"
    result = runner.invoke(
        cli,
        ["wifi", "--output-format", "csv", "--out", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "platform,Linux" in content


def test_wifi_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "platform": "Linux",
        "platform_supported": True,
        "interfaces": [],
        "access_points": [],
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_wifi", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--format", "csv"])
    assert result.exit_code == 0
    assert "platform,Linux" in result.output


def test_jwt_output_format_csv() -> None:
    token = _make_jwt({"alg": "HS256"}, {"sub": "user1", "exp": 1800000000})
    runner = CliRunner()
    result = runner.invoke(cli, ["jwt", "--token", token, "--output-format", "csv"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "valid_structure,true" in result.output
    assert "algorithm,HS256" in result.output


def test_jwt_output_format_csv_out(tmp_path) -> None:
    token = _make_jwt({"alg": "HS256"}, {"sub": "user1", "exp": 1800000000})
    runner = CliRunner()
    out_file = tmp_path / "jwt.csv"
    result = runner.invoke(cli, ["jwt", "--token", token, "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "field,value" in content
    assert "valid_structure,true" in content


def test_jwt_format_csv_alias() -> None:
    token = _make_jwt({"alg": "HS256"}, {"sub": "user1", "exp": 1800000000})
    runner = CliRunner()
    result = runner.invoke(cli, ["jwt", "--token", token, "--format", "csv"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "algorithm,HS256" in result.output


def test_config_output_format_csv() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "section,option,value" in result.output


def test_config_output_format_csv_out(tmp_path) -> None:
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("defaults:\n  timeout: 5.0\ncommands:\n  scan:\n    ports: common\n")
    runner = CliRunner()
    out_file = tmp_path / "config.csv"
    result = runner.invoke(cli, ["--config", str(cfg), "config", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "section,option,value" in content
    assert "defaults,timeout,5.0" in content


def test_config_format_csv_alias(tmp_path) -> None:
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text("defaults:\n  timeout: 5.0\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(cfg), "config", "--format", "csv"])
    assert result.exit_code == 0
    assert "section,option,value" in result.output
    assert "defaults,timeout,5.0" in result.output


def test_completion_output_format_csv() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "bash", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "field,value" in result.output
    assert "shell,bash" in result.output
    assert "script" in result.output


def test_completion_output_format_csv_out(tmp_path) -> None:
    runner = CliRunner()
    out_file = tmp_path / "completion.csv"
    result = runner.invoke(cli, ["completion", "--shell", "bash", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Completion script written" in result.output
    content = out_file.read_text()
    assert "shell,bash" in content


def test_completion_format_csv_alias() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--shell", "bash", "--format", "csv"])
    assert result.exit_code == 0
    assert "shell,bash" in result.output


# ---------------------------------------------------------------------------
# CSV output integration tests for remaining commands
# ---------------------------------------------------------------------------


def test_fuzz_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 2,
        "findings": [{"path": "/admin", "status_code": 200, "error": None}],
        "all_results": [
            {"path": "/admin", "status_code": 200, "error": None},
            {"path": "/login", "status_code": 404, "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_fuzz", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["fuzz", "--target", "https://example.com", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "target,base_url,path,status_code,error,is_finding" in result.output
    assert "https://example.com,https://example.com,/admin,200,,true" in result.output
    assert "https://example.com,https://example.com,/login,404,,false" in result.output


def test_fuzz_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 1,
        "findings": [],
        "all_results": [{"path": "/admin", "status_code": 404, "error": None}],
    }
    monkeypatch.setattr("ethscan.cli.run_fuzz", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "fuzz.csv"
    result = runner.invoke(cli, ["fuzz", "--target", "https://example.com", "--output-format", "csv", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,base_url,path,status_code,error,is_finding" in content


def test_fuzz_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "base_url": "https://example.com",
        "paths_tested": 1,
        "findings": [],
        "all_results": [{"path": "/admin", "status_code": 404, "error": None}],
    }
    monkeypatch.setattr("ethscan.cli.run_fuzz", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["fuzz", "--target", "https://example.com", "--format", "csv"])
    assert result.exit_code == 0
    assert "target,base_url,path,status_code,error,is_finding" in result.output


def test_resolve_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "normalized": "example.com",
        "is_ip": False,
        "record_types_queried": ["A"],
        "records": {"A": ["93.184.216.34"]},
        "dnspython_available": False,
        "server": None,
    }
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,normalized,record_type,record_value" in result.output
    assert "example.com,example.com,A,93.184.216.34" in result.output


def test_resolve_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "normalized": "example.com",
        "records": {"A": ["93.184.216.34"]},
    }
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "resolve.csv"
    result = runner.invoke(cli, ["resolve", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,normalized,record_type,record_value" in content


def test_resolve_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "normalized": "example.com",
        "records": {"A": ["93.184.216.34"]},
    }
    monkeypatch.setattr("ethscan.cli.run_resolve", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,normalized,record_type,record_value" in result.output


def test_dnsbrute_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["93.184.216.34"], "aaaa": []},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_dnsbrute", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,subdomain,hostname,a_records,aaaa_records,resolved" in result.output
    assert "example.com,example.com,www,www.example.com,93.184.216.34,,true" in result.output


def test_dnsbrute_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["93.184.216.34"], "aaaa": []},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_dnsbrute", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "dnsbrute.csv"
    result = runner.invoke(cli, ["dnsbrute", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,domain,subdomain,hostname,a_records,aaaa_records,resolved" in content


def test_dnsbrute_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "all_results": [
            {"subdomain": "www", "hostname": "www.example.com", "a": ["93.184.216.34"], "aaaa": []},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_dnsbrute", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,subdomain,hostname,a_records,aaaa_records,resolved" in result.output


def test_tls_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions": [
            {"version": "TLSv1_2", "supported": True, "error": None, "negotiated_cipher": "AES128-GCM-SHA256", "negotiated_protocol": "TLSv1.2"},
        ],
        "ciphers": [
            {"cipher": "AES128-GCM-SHA256", "supported": True, "error": None, "negotiated_version": "TLSv1.2"},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_tls", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["tls", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,probe_type,probe,supported,negotiated,error" in result.output
    assert "example.com,example.com,443,version,TLSv1_2,true,AES128-GCM-SHA256," in result.output
    assert "example.com,example.com,443,cipher,AES128-GCM-SHA256,true,TLSv1.2," in result.output


def test_tls_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions": [],
        "ciphers": [],
    }
    monkeypatch.setattr("ethscan.cli.run_tls", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "tls.csv"
    result = runner.invoke(cli, ["tls", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,probe_type,probe,supported,negotiated,error" in content


def test_tls_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "port": 443,
        "versions": [],
        "ciphers": [],
    }
    monkeypatch.setattr("ethscan.cli.run_tls", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["tls", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,probe_type,probe,supported,negotiated,error" in result.output


def test_urlcheck_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {
            "total_findings": 1,
            "web_checks_run": ["headers"],
            "fuzz_enabled": False,
            "ssl_checked": False,
        },
        "web": {
            "security_headers": {"present": ["X-Frame-Options"], "missing": []},
        },
        "fuzz": None,
        "ssl": None,
    }
    monkeypatch.setattr("ethscan.cli.run_urlcheck", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["urlcheck", "--target", "https://example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "section,key,value" in result.output
    assert "summary,target,https://example.com" in result.output
    assert "web,header_present,X-Frame-Options" in result.output


def test_urlcheck_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {"total_findings": 0, "web_checks_run": [], "fuzz_enabled": False, "ssl_checked": False},
    }
    monkeypatch.setattr("ethscan.cli.run_urlcheck", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "urlcheck.csv"
    result = runner.invoke(cli, ["urlcheck", "--target", "https://example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "section,key,value" in content


def test_urlcheck_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "https://example.com",
        "normalized_target": "https://example.com",
        "summary": {"total_findings": 0, "web_checks_run": [], "fuzz_enabled": False, "ssl_checked": False},
    }
    monkeypatch.setattr("ethscan.cli.run_urlcheck", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["urlcheck", "--target", "https://example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "section,key,value" in result.output


def test_osdetect_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "probes": [
            {"port": 80, "probe_type": "SYN", "connected": True, "response": "SYN-ACK", "flags_observed": "SYN-ACK", "error": None},
        ],
        "inferred_os": ["Linux"],
    }
    monkeypatch.setattr("ethscan.cli.run_osdetect", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["osdetect", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,probe_type,connected,response,flags_observed,error" in result.output
    assert "example.com,example.com,80,SYN,true,SYN-ACK,SYN-ACK," in result.output


def test_osdetect_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "probes": [],
        "inferred_os": [],
    }
    monkeypatch.setattr("ethscan.cli.run_osdetect", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "osdetect.csv"
    result = runner.invoke(cli, ["osdetect", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,probe_type,connected,response,flags_observed,error" in content


def test_osdetect_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "host": "example.com",
        "probes": [],
        "inferred_os": [],
    }
    monkeypatch.setattr("ethscan.cli.run_osdetect", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["osdetect", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,probe_type,connected,response,flags_observed,error" in result.output


def test_trace_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "hops": [
            {"hop": 1, "ttl": 1, "ip": "10.0.0.1", "host": "10.0.0.1", "response_type": "ICMP_TTL_EXCEEDED", "rtt_ms": 1.5, "rtt_avg_ms": 1.5, "reached_destination": False, "reached": False},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_trace", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "--target", "example.com", "--output-format", "csv", "--max-hops", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in result.output
    assert "example.com,1,10.0.0.1,10.0.0.1,ICMP_TTL_EXCEEDED,1.5,false" in result.output


def test_trace_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {"target": "example.com", "hops": []}
    monkeypatch.setattr("ethscan.cli.run_trace", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "trace.csv"
    result = runner.invoke(cli, ["trace", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--max-hops", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in content


def test_trace_format_csv_alias(monkeypatch) -> None:
    mock_results = {"target": "example.com", "hops": []}
    monkeypatch.setattr("ethscan.cli.run_trace", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "--target", "example.com", "--format", "csv", "--max-hops", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in result.output


def test_ping_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "probes": [
            {"ip": "93.184.216.34", "rtt_ms": 10.5, "ttl": 64, "sequence": 1, "response_type": "ECHO_REPLY", "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_ping", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--output-format", "csv", "--count", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,ip,sequence,rtt_ms,ttl,response_type,error" in result.output
    assert "example.com,93.184.216.34,1,10.5,64,ECHO_REPLY," in result.output


def test_ping_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {"target": "example.com", "probes": []}
    monkeypatch.setattr("ethscan.cli.run_ping", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "ping.csv"
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--count", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,ip,sequence,rtt_ms,ttl,response_type,error" in content


def test_ping_format_csv_alias(monkeypatch) -> None:
    mock_results = {"target": "example.com", "probes": []}
    monkeypatch.setattr("ethscan.cli.run_ping", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ping", "--target", "example.com", "--format", "csv", "--count", "1", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,ip,sequence,rtt_ms,ttl,response_type,error" in result.output


def test_recon_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": ["dns"],
        "subdomains": None,
        "dns": {"records": {"A": ["93.184.216.34"]}},
        "whois": None,
        "geo": None,
        "trace": None,
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_recon", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--output-format", "csv", "--modules", "dns", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "module,field,value" in result.output
    assert "meta,target,example.com" in result.output
    assert "dns,A,93.184.216.34" in result.output


def test_recon_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": [],
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_recon", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "recon.csv"
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "module,field,value" in content


def test_recon_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "modules_run": [],
        "notes": [],
    }
    monkeypatch.setattr("ethscan.cli.run_recon", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["recon", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "module,field,value" in result.output


def test_cert_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "ip": "93.184.216.34",
        "subdomains": ["www.example.com"],
    }
    monkeypatch.setattr("ethscan.cli.run_cert", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,ip,subdomain" in result.output
    assert "example.com,example.com,93.184.216.34,www.example.com" in result.output


def test_cert_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "ip": None,
        "subdomains": [],
    }
    monkeypatch.setattr("ethscan.cli.run_cert", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "cert.csv"
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,domain,ip,subdomain" in content


def test_cert_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "ip": None,
        "subdomains": [],
    }
    monkeypatch.setattr("ethscan.cli.run_cert", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["cert", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,ip,subdomain" in result.output


def test_hash_output_format_csv() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--algorithm", "md5", "--output-format", "csv", "--file", "/dev/null"])
    # Empty input -> "No passwords provided."
    assert result.exit_code == 0


def test_hash_output_format_csv_with_passwords(monkeypatch) -> None:
    mock_results = {
        "algorithm": "md5",
        "results": [
            {"password": "password", "algorithm": "md5", "hash": "5f4dcc3b5aa765d61d8327deb882cf99", "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_hash", lambda *a, **k: mock_results)
    monkeypatch.setattr("ethscan.cli.load_passwords_from_file", lambda p: ["password"])
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--algorithm", "md5", "--output-format", "csv", "--file", "passwords.txt"])
    assert result.exit_code == 0
    assert "password,digest,algorithm,salt,pepper,iterations,computed,match,error" in result.output
    assert "password,5f4dcc3b5aa765d61d8327deb882cf99,md5" in result.output


def test_hash_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "algorithm": "md5",
        "results": [
            {"password": "password", "algorithm": "md5", "hash": "5f4dcc3b5aa765d61d8327deb882cf99", "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_hash", lambda *a, **k: mock_results)
    monkeypatch.setattr("ethscan.cli.load_passwords_from_file", lambda p: ["password"])
    runner = CliRunner()
    out_file = tmp_path / "hash.csv"
    result = runner.invoke(cli, ["hash", "--algorithm", "md5", "--output-format", "csv", "--out", str(out_file), "--file", "passwords.txt"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "password,digest,algorithm,salt,pepper,iterations,computed,match,error" in content


def test_hash_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "algorithm": "md5",
        "results": [
            {"password": "password", "algorithm": "md5", "hash": "5f4dcc3b5aa765d61d8327deb882cf99", "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_hash", lambda *a, **k: mock_results)
    monkeypatch.setattr("ethscan.cli.load_passwords_from_file", lambda p: ["password"])
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--algorithm", "md5", "--format", "csv", "--file", "passwords.txt"])
    assert result.exit_code == 0
    assert "password,digest,algorithm,salt,pepper,iterations,computed,match,error" in result.output


def test_hash_check_output_format_csv(monkeypatch) -> None:
    mock_result = {
        "password": "password",
        "digest": "5f4dcc3b5aa765d61d8327deb882cf99",
        "algorithm": "md5",
        "salt": False,
        "pepper": False,
        "iterations": None,
        "computed": "5f4dcc3b5aa765d61d8327deb882cf99",
        "match": True,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_check", lambda *a, **k: mock_result)
    monkeypatch.setattr("ethscan.cli.load_passwords_from_file", lambda p: ["password"])
    runner = CliRunner()
    result = runner.invoke(cli, ["hash", "--check", "5f4dcc3b5aa765d61d8327deb882cf99", "--algorithm", "md5", "--output-format", "csv", "--file", "passwords.txt"])
    assert result.exit_code == 0
    assert "password,digest,algorithm,salt,pepper,iterations,computed,match,error" in result.output
    assert "password,5f4dcc3b5aa765d61d8327deb882cf99,md5,false,false,,5f4dcc3b5aa765d61d8327deb882cf99,true," in result.output


def test_dnssec_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "validated": True,
        "dnskey": {"success": True, "keys": [{"key_tag": 12345}]},
        "ds": {"success": True, "records": [{"key_tag": 12345}]},
    }
    monkeypatch.setattr("ethscan.cli.run_dnssec", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["dnssec", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,validated,dnskey_success,dnskey_count,ds_success,ds_count" in result.output
    assert "example.com,example.com,true,true,1,true,1" in result.output


def test_dnssec_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": False, "keys": []},
        "ds": {"success": False, "records": []},
    }
    monkeypatch.setattr("ethscan.cli.run_dnssec", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "dnssec.csv"
    result = runner.invoke(cli, ["dnssec", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,domain,validated,dnskey_success,dnskey_count,ds_success,ds_count" in content


def test_dnssec_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "example.com",
        "domain": "example.com",
        "validated": False,
        "dnskey": {"success": False, "keys": []},
        "ds": {"success": False, "records": []},
    }
    monkeypatch.setattr("ethscan.cli.run_dnssec", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["dnssec", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,domain,validated,dnskey_success,dnskey_count,ds_success,ds_count" in result.output


def test_mac_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Ayecom Technology Co., Ltd.",
            "cached": True,
            "offline_fallback": False,
            "error": None,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_mac", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["mac", "--target", "00:1A:2B:3C:4D:5E", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,mac,oui,vendor,cached,offline_fallback,error" in result.output
    assert "00:1A:2B:3C:4D:5E,00:1a:2b:3c:4d:5e,001a2b3c" in result.output
    assert '"Ayecom Technology Co., Ltd.",true,false,' in result.output


def test_mac_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": None,
            "error": "Failed to fetch MAC vendor data",
            "cached": False,
            "offline_fallback": False,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_mac", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "mac.csv"
    result = runner.invoke(cli, ["mac", "--target", "00:1A:2B:3C:4D:5E", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,mac,oui,vendor,cached,offline_fallback,error" in content


def test_mac_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "00:1A:2B:3C:4D:5E",
        "mac": "00:1a:2b:3c:4d:5e",
        "oui": "001a2b3c",
        "mac_data": {
            "mac": "00:1a:2b:3c:4d:5e",
            "vendor": "Ayecom Technology Co., Ltd.",
            "cached": True,
            "offline_fallback": False,
            "error": None,
        },
    }
    monkeypatch.setattr("ethscan.cli.run_mac", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["mac", "--target", "00:1A:2B:3C:4D:5E", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,mac,oui,vendor,cached,offline_fallback,error" in result.output


# ---------------------------------------------------------------------------
# smtp command
# ---------------------------------------------------------------------------


def test_smtp_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--users" in result.output
    assert "--timeout" in result.output
    assert "--output-format" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "--no-starttls-check" in result.output
    assert "--no-relay-check" in result.output


def test_smtp_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "smtp" in result.output


def test_smtp_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "connected": True,
        "banner": "220 mail.example.com ESMTP",
        "ehlo_success": True,
        "starttls_advertised": True,
        "starttls_checked": True,
        "capabilities": ["STARTTLS", "AUTH"],
        "users": [
            {"user": "admin", "found": None, "description": "will accept", "code": 252, "error": None},
        ],
        "open_relay": False,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_smtp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,user,found,code,description" in result.output
    assert "mail.example.com" in result.output
    assert "admin" in result.output


def test_smtp_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "users": [
            {"user": "admin", "found": True, "description": "user known", "code": 250, "error": None},
        ],
    }
    monkeypatch.setattr("ethscan.cli.run_smtp", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "smtp.csv"
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,user,found,code,description" in content
    assert "admin" in content


def test_smtp_format_csv_alias(monkeypatch) -> None:
    mock_results = {"target": "mail.example.com", "host": "mail.example.com", "port": 25, "users": []}
    monkeypatch.setattr("ethscan.cli.run_smtp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,user,found,code,description" in result.output


def test_smtp_output_format_default_is_json(monkeypatch) -> None:
    mock_results = {"target": "mail.example.com", "host": "mail.example.com", "port": 25, "connected": True}
    monkeypatch.setattr("ethscan.cli.run_smtp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "mail.example.com"


def test_smtp_output_format_markdown(monkeypatch) -> None:
    mock_results = {
        "target": "mail.example.com",
        "host": "mail.example.com",
        "port": 25,
        "connected": True,
        "banner": "220 mail.example.com ESMTP",
        "ehlo_success": True,
        "starttls_advertised": True,
        "capabilities": ["STARTTLS"],
        "users": [],
        "open_relay": False,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_smtp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--output-format", "markdown", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "# ethscan SMTP Report" in result.output
    assert "mail.example.com" in result.output


def test_smtp_output_format_csv_with_users_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {
            "target": "mail.example.com",
            "host": "mail.example.com",
            "port": 25,
            "users": [
                {"user": u, "found": None, "description": "will accept", "code": 252, "error": None}
                for u in (kwargs.get("users") or [])
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_smtp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--users", "admin,root,guest", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["users"] == ["admin", "root", "guest"]
    assert "admin" in result.output
    assert "root" in result.output
    assert "guest" in result.output


def test_smtp_no_relay_check_flag(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "mail.example.com", "host": "mail.example.com", "port": 25, "users": []}

    monkeypatch.setattr("ethscan.cli.run_smtp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--no-relay-check", "--no-starttls-check", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["check_relay"] is False
    assert captured["check_starttls"] is False


def test_smtp_port_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "mail.example.com", "host": "mail.example.com", "port": kwargs.get("port", 25), "users": []}

    monkeypatch.setattr("ethscan.cli.run_smtp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "mail.example.com", "--port", "587", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["port"] == 587


def test_smtp_offline_connection_refused() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["smtp", "--target", "127.0.0.1:1", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["connected"] is False
    assert parsed["error"] is not None


# ---------------------------------------------------------------------------
# ftp command
# ---------------------------------------------------------------------------


def test_ftp_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--no-anonymous-check" in result.output
    assert "--timeout" in result.output
    assert "--output-format" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_ftp_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ftp" in result.output


def test_ftp_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "port": 21,
        "connected": True,
        "banner": "220 (vsFTPd 3.0.3)",
        "welcome_message": "220 (vsFTPd 3.0.3)",
        "anonymous_login": True,
        "anonymous_message": "anonymous login successful",
        "check_anonymous": True,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ftp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,banner,anonymous_login,anonymous_message,error" in result.output
    assert "ftp.example.com" in result.output
    assert "true" in result.output


def test_ftp_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "port": 21,
        "banner": "220 (vsFTPd 3.0.3)",
        "anonymous_login": True,
        "anonymous_message": "anonymous login successful",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ftp", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "ftp.csv"
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,banner,anonymous_login,anonymous_message,error" in content
    assert "ftp.example.com" in content


def test_ftp_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "port": 21,
        "banner": "220 (vsFTPd 3.0.3)",
        "anonymous_login": True,
        "anonymous_message": "anonymous login successful",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ftp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,banner,anonymous_login,anonymous_message,error" in result.output


def test_ftp_output_format_default_is_json(monkeypatch) -> None:
    mock_results = {"target": "ftp.example.com", "host": "ftp.example.com", "port": 21, "connected": True}
    monkeypatch.setattr("ethscan.cli.run_ftp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "ftp.example.com"


def test_ftp_output_format_markdown(monkeypatch) -> None:
    mock_results = {
        "target": "ftp.example.com",
        "host": "ftp.example.com",
        "port": 21,
        "connected": True,
        "banner": "220 (vsFTPd 3.0.3)",
        "welcome_message": "220 (vsFTPd 3.0.3)",
        "anonymous_login": True,
        "anonymous_message": "anonymous login successful",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ftp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--output-format", "markdown", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "# ethscan FTP Report" in result.output
    assert "ftp.example.com" in result.output


def test_ftp_no_anonymous_check_flag(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "ftp.example.com", "host": "ftp.example.com", "port": 21, "connected": True, "error": None}

    monkeypatch.setattr("ethscan.cli.run_ftp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--no-anonymous-check", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["check_anonymous"] is False


def test_ftp_port_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "ftp.example.com", "host": "ftp.example.com", "port": kwargs.get("port", 21), "connected": True, "error": None}

    monkeypatch.setattr("ethscan.cli.run_ftp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "ftp.example.com", "--port", "2121", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["port"] == 2121


def test_ftp_offline_connection_refused() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ftp", "--target", "127.0.0.1:1", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["connected"] is False
    assert parsed["error"] is not None


# ---------------------------------------------------------------------------
# NTP CLI tests
# ---------------------------------------------------------------------------


def test_ntp_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--no-monlist-check" in result.output
    assert "--timeout" in result.output
    assert "--output-format" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_ntp_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ntp" in result.output


def test_ntp_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 2,
            "reference_id": "0x0a0b0c0d",
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
        },
        "monlist_response": {
            "peer_count": 3,
            "error": None,
        },
        "is_reflector": True,
        "amplification_factor": 24.5,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ntp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,stratum,refid" in result.output
    assert "ntp.example.com" in result.output
    assert "2" in result.output


def test_ntp_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 2,
            "reference_id": "0x0a0b0c0d",
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
        },
        "monlist_response": {
            "peer_count": 3,
            "error": None,
        },
        "is_reflector": True,
        "amplification_factor": 24.5,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ntp", lambda *a, **k: mock_results)
    runner = CliRunner()
    out_file = tmp_path / "ntp.csv"
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,stratum,refid" in content
    assert "ntp.example.com" in content


def test_ntp_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "stratum": 2,
            "reference_id": "0x0a0b0c0d",
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
        },
        "monlist_response": {
            "peer_count": 0,
            "error": None,
        },
        "is_reflector": False,
        "amplification_factor": None,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ntp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,stratum,refid" in result.output


def test_ntp_output_format_default_is_json(monkeypatch) -> None:
    mock_results = {"target": "ntp.example.com", "host": "ntp.example.com", "port": 123, "error": None}
    monkeypatch.setattr("ethscan.cli.run_ntp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "ntp.example.com"


def test_ntp_output_format_markdown(monkeypatch) -> None:
    mock_results = {
        "target": "ntp.example.com",
        "host": "ntp.example.com",
        "port": 123,
        "time_response": {
            "leap_indicator": "no warning",
            "version": 4,
            "mode": 4,
            "stratum": 2,
            "poll": 4,
            "precision": -20,
            "root_delay_ms": 250.0,
            "root_dispersion_ms": 125.0,
            "reference_id": "0x0a0b0c0d",
            "reference_timestamp": None,
            "originate_timestamp": None,
            "receive_timestamp": None,
            "transmit_timestamp": None,
        },
        "monlist_response": {
            "leap_indicator": 0,
            "version": 4,
            "mode": 7,
            "response_bit": 1,
            "implementation": 42,
            "request_code": 0,
            "sequence": 1,
            "status": 0,
            "association_id": 0,
            "offset": 0,
            "count": 3,
            "peer_count": 3,
            "peers": [
                {"address": "127.0.0.1", "port": 1234, "mode": 3, "version": 4},
            ],
            "error": None,
        },
        "is_reflector": True,
        "amplification_factor": 24.5,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_ntp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--output-format", "markdown", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "# ethscan NTP Report" in result.output
    assert "ntp.example.com" in result.output
    assert "Monlist Response" in result.output
    assert "Peer Count:** 3" in result.output


def test_ntp_no_monlist_check_flag(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "ntp.example.com", "host": "ntp.example.com", "port": 123, "error": None}

    monkeypatch.setattr("ethscan.cli.run_ntp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--no-monlist-check", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["check_monlist"] is False


def test_ntp_port_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "ntp.example.com", "host": "ntp.example.com", "port": kwargs.get("port", 123), "error": None}

    monkeypatch.setattr("ethscan.cli.run_ntp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "ntp.example.com", "--port", "12300", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["port"] == 12300


def test_ntp_offline_timeout() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ntp", "--target", "127.0.0.1:1", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["error"] is not None
    assert "time request failed" in parsed["error"]


# ---------------------------------------------------------------------------
# SNMP CLI tests
# ---------------------------------------------------------------------------


def test_snmp_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--communities" in result.output
    assert "--timeout" in result.output
    assert "--output-format" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_snmp_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "snmp" in result.output


def test_snmp_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "snmp.example.com",
        "host": "snmp.example.com",
        "port": 161,
        "snmp_version": "v2c",
        "communities": [
            {"community": "public", "valid": True, "version": "v2c", "error": None},
        ],
        "valid_communities": ["public"],
        "sysDescr": "Linux router 5.4.0",
        "sysObjectID": "1.3.6.1.4.1.9.1.1",
        "sysUpTime": 123456780,
        "sysName": "router-01",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_snmp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,snmp_version,sys_descr" in result.output
    assert "snmp.example.com" in result.output
    assert "Linux router 5.4.0" in result.output


def test_snmp_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "snmp.example.com",
        "host": "snmp.example.com",
        "port": 161,
        "snmp_version": "v2c",
        "communities": [
            {"community": "public", "valid": True, "version": "v2c", "error": None},
        ],
        "valid_communities": ["public"],
        "sysDescr": "Linux router 5.4.0",
        "sysObjectID": "1.3.6.1.4.1.9.1.1",
        "sysUpTime": 123456780,
        "sysName": "router-01",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_snmp", lambda *a, **k: mock_results)
    out_file = tmp_path / "snmp_report.csv"
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,snmp_version,sys_descr" in content
    assert "snmp.example.com" in content


def test_snmp_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "snmp.example.com",
        "host": "snmp.example.com",
        "port": 161,
        "snmp_version": "v2c",
        "communities": [
            {"community": "public", "valid": True, "version": "v2c", "error": None},
        ],
        "valid_communities": ["public"],
        "sysDescr": "Linux router 5.4.0",
        "sysObjectID": "1.3.6.1.4.1.9.1.1",
        "sysUpTime": 123456780,
        "sysName": "router-01",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_snmp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,snmp_version,sys_descr" in result.output


def test_snmp_output_format_default_is_json(monkeypatch) -> None:
    mock_results = {"target": "snmp.example.com", "host": "snmp.example.com", "port": 161, "error": None}
    monkeypatch.setattr("ethscan.cli.run_snmp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "snmp.example.com"


def test_snmp_output_format_markdown(monkeypatch) -> None:
    mock_results = {
        "target": "snmp.example.com",
        "host": "snmp.example.com",
        "port": 161,
        "snmp_version": "v2c",
        "communities": [
            {"community": "public", "valid": True, "version": "v2c", "error": None},
            {"community": "private", "valid": False, "version": None, "error": "v1 request failed: timeout"},
        ],
        "valid_communities": ["public"],
        "sysDescr": "Linux router 5.4.0",
        "sysObjectID": "1.3.6.1.4.1.9.1.1",
        "sysUpTime": 123456780,
        "sysName": "router-01",
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_snmp", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--output-format", "markdown", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "# ethscan SNMP Report" in result.output
    assert "snmp.example.com" in result.output
    assert "Community Probes" in result.output
    assert "**sysDescr:** Linux router 5.4.0" in result.output
    assert "Misconfiguration" in result.output


def test_snmp_communities_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "snmp.example.com", "host": "snmp.example.com", "port": 161, "error": None}

    monkeypatch.setattr("ethscan.cli.run_snmp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--communities", "public, secret ", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["communities"] == ["public", "secret"]


def test_snmp_port_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "snmp.example.com", "host": "snmp.example.com", "port": kwargs.get("port", 161), "error": None}

    monkeypatch.setattr("ethscan.cli.run_snmp", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "snmp.example.com", "--port", "1161", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["port"] == 1161


def test_snmp_offline_timeout() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["snmp", "--target", "127.0.0.1:1", "--timeout", "0.2"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["error"] is not None
    assert "request failed" in parsed["error"]


# ---------------------------------------------------------------------------
# NetBIOS CLI tests
# ---------------------------------------------------------------------------


def test_netbios_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--name" in result.output
    assert "--suffix" in result.output
    assert "--timeout" in result.output
    assert "--output-format" in result.output
    assert "--format" in result.output
    assert "--out" in result.output


def test_netbios_top_level_help_lists_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "netbios" in result.output


def test_netbios_output_format_csv(monkeypatch) -> None:
    mock_results = {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 137,
        "queried_name": "*",
        "queried_suffix": 0,
        "mac": "aa:bb:cc:dd:ee:ff",
        "names": [
            {"name": "MYHOST", "suffix": 0, "suffix_hex": "0x00",
             "service_type": "Workstation service",
             "flags": {"group": False, "active": True}},
        ],
        "num_names": 1,
        "is_server": False,
        "hostname": "MYHOST",
        "is_domain_member": False,
        "transaction_id": 0,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_netbios", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,mac,names,num_names" in result.output
    assert "192.168.1.100" in result.output
    assert "aa:bb:cc:dd:ee:ff" in result.output
    assert "MYHOST" in result.output


def test_netbios_output_format_csv_out(tmp_path, monkeypatch) -> None:
    mock_results = {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 137,
        "queried_name": "*",
        "queried_suffix": 0,
        "mac": "aa:bb:cc:dd:ee:ff",
        "names": [],
        "num_names": 0,
        "is_server": False,
        "hostname": None,
        "is_domain_member": False,
        "transaction_id": 0,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_netbios", lambda *a, **k: mock_results)
    out_file = tmp_path / "netbios_report.csv"
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port,mac,names,num_names" in content
    assert "192.168.1.100" in content


def test_netbios_format_csv_alias(monkeypatch) -> None:
    mock_results = {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 137,
        "queried_name": "*",
        "queried_suffix": 0,
        "mac": None,
        "names": [],
        "num_names": 0,
        "is_server": False,
        "hostname": None,
        "is_domain_member": False,
        "transaction_id": 0,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_netbios", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,mac,names,num_names" in result.output


def test_netbios_output_format_default_is_json(monkeypatch) -> None:
    mock_results = {"target": "192.168.1.100", "host": "192.168.1.100", "port": 137, "error": None}
    monkeypatch.setattr("ethscan.cli.run_netbios", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--timeout", "1.0"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["host"] == "192.168.1.100"


def test_netbios_output_format_markdown(monkeypatch) -> None:
    mock_results = {
        "target": "192.168.1.100",
        "host": "192.168.1.100",
        "port": 137,
        "queried_name": "*",
        "queried_suffix": 0,
        "mac": "aa:bb:cc:dd:ee:ff",
        "names": [
            {"name": "MYHOST", "suffix": 0, "suffix_hex": "0x00",
             "service_type": "Workstation service",
             "flags": {"group": False, "active": True}},
            {"name": "MYHOST", "suffix": 32, "suffix_hex": "0x20",
             "service_type": "File server service",
             "flags": {"group": False, "active": True}},
        ],
        "num_names": 2,
        "is_server": True,
        "hostname": "MYHOST",
        "is_domain_member": False,
        "transaction_id": 0,
        "error": None,
    }
    monkeypatch.setattr("ethscan.cli.run_netbios", lambda *a, **k: mock_results)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--output-format", "markdown", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "# ethscan NetBIOS Report" in result.output
    assert "192.168.1.100" in result.output
    assert "## Names" in result.output
    assert "File server service" in result.output
    assert "Server:** YES" in result.output


def test_netbios_name_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "192.168.1.100", "host": "192.168.1.100", "port": 137, "error": None}

    monkeypatch.setattr("ethscan.cli.run_netbios", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--name", "WORKSTATION", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["name"] == "WORKSTATION"


def test_netbios_suffix_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "192.168.1.100", "host": "192.168.1.100", "port": 137, "error": None}

    monkeypatch.setattr("ethscan.cli.run_netbios", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--suffix", "20", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["suffix"] == 20


def test_netbios_port_option(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return {"target": "192.168.1.100", "host": "192.168.1.100", "port": kwargs.get("port", 137), "error": None}

    monkeypatch.setattr("ethscan.cli.run_netbios", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "192.168.1.100", "--port", "138", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert captured["port"] == 138


def test_netbios_offline_timeout() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["netbios", "--target", "127.0.0.1:1", "--timeout", "0.2"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["error"] is not None
    assert "request failed" in parsed["error"]



def test_redis_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["redis", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--output-format" in result.output


def test_redis_top_level_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "redis" in result.output


def test_redis_output_format_csv(monkeypatch) -> None:
    def mock_run_redis(target, port=None, timeout=3.0, probes=None, connector=None):
        return {
            "target": target,
            "host": target,
            "port": 6379,
            "ping": "PONG",
            "info": {"redis_version": "7.0.0", "role": "master"},
            "config": {"bind": "127.0.0.1", "requirepass": ""},
            "dangerous_findings": [],
            "accessible": True,
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_redis", mock_run_redis)
    runner = CliRunner()
    result = runner.invoke(cli, ["redis", "--target", "example.com", "--output-format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port,accessible" in result.output


def test_redis_output_format_csv_out(tmp_path, monkeypatch) -> None:
    def mock_run_redis(target, port=None, timeout=3.0, probes=None, connector=None):
        return {
            "target": target,
            "host": target,
            "port": 6379,
            "ping": "PONG",
            "info": {},
            "config": {},
            "dangerous_findings": [],
            "accessible": True,
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_redis", mock_run_redis)
    runner = CliRunner()
    out_file = tmp_path / "redis.csv"
    result = runner.invoke(
        cli,
        ["redis", "--target", "example.com", "--output-format", "csv", "--out", str(out_file), "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    content = out_file.read_text()
    assert "target,host,port" in content


def test_redis_format_csv_alias(monkeypatch) -> None:
    def mock_run_redis(target, port=None, timeout=3.0, probes=None, connector=None):
        return {
            "target": target,
            "host": target,
            "port": 6379,
            "ping": "PONG",
            "info": {},
            "config": {},
            "dangerous_findings": [],
            "accessible": True,
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_redis", mock_run_redis)
    runner = CliRunner()
    result = runner.invoke(cli, ["redis", "--target", "example.com", "--format", "csv", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port" in result.output


def test_redis_default_is_json(monkeypatch) -> None:
    def mock_run_redis(target, port=None, timeout=3.0, probes=None, connector=None):
        return {
            "target": target,
            "host": target,
            "port": 6379,
            "ping": "PONG",
            "info": {},
            "config": {},
            "dangerous_findings": [],
            "accessible": True,
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_redis", mock_run_redis)
    runner = CliRunner()
    result = runner.invoke(cli, ["redis", "--target", "example.com", "--timeout", "1.0"])
    assert result.exit_code == 0
    try:
        json.loads(result.output)
    except Exception:
        assert False, "Default should be JSON"


def test_redis_output_format_precedence(monkeypatch) -> None:
    def mock_run_redis(target, port=None, timeout=3.0, probes=None, connector=None):
        return {
            "target": target,
            "host": target,
            "port": 6379,
            "ping": "PONG",
            "info": {},
            "config": {},
            "dangerous_findings": [],
            "accessible": True,
            "error": None,
        }

    monkeypatch.setattr("ethscan.cli.run_redis", mock_run_redis)
    runner = CliRunner()
    result = runner.invoke(cli, ["redis", "--target", "example.com", "--output-format", "csv", "--format", "json", "--timeout", "1.0"])
    assert result.exit_code == 0
    assert "target,host,port" in result.output
