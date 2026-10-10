"""Tests for the ethscan report command."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from ethscan.cli import cli


def test_report_json_output() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "passwords.txt"
        audit_file.write_text("password\n123456\ncorrect-Horse-battery-staple-9x!\n")

        result = runner.invoke(
            cli,
            [
                "report",
                "--target",
                "127.0.0.1",
                "--ports",
                "80,443",
                "--timeout",
                "0.1",
                "--workers",
                "10",
                "--audit-file",
                str(audit_file),
                "--format",
                "json",
            ],
        )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "scan" in data
    assert "audit" in data
    assert data["scan"]["target"] == "127.0.0.1"
    assert data["scan"]["ports_scanned"] == 2
    assert "open_ports" in data["scan"]
    assert "details" in data["scan"]
    assert data["audit"]["passwords_audited"] == 3
    assert len(data["audit"]["results"]) == 3
    for result_item in data["audit"]["results"]:
        assert "password" in result_item
        assert "length" in result_item
        assert "entropy" in result_item
        assert "common" in result_item
        assert "patterns" in result_item
        assert "score" in result_item
        assert "verdict" in result_item


def test_report_markdown_output() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "passwords.txt"
        audit_file.write_text("password\n123456\n")

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
            ],
        )

    assert result.exit_code == 0
    assert "# ethscan Report" in result.output
    assert "## Port Scan" in result.output
    assert "## Password Audit" in result.output
    assert "127.0.0.1" in result.output
    assert "password" in result.output


def test_report_writes_to_file() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "passwords.txt"
        audit_file.write_text("password\n")
        out_file = Path(tmpdir) / "report.json"

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
                "json",
                "--out",
                str(out_file),
            ],
        )

        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["scan"]["target"] == "127.0.0.1"
        assert data["audit"]["passwords_audited"] == 1


def test_report_without_audit() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "report",
            "--target",
            "127.0.0.1",
            "--ports",
            "80,443",
            "--timeout",
            "0.1",
            "--workers",
            "10",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["audit"]["passwords_audited"] == 0
    assert data["audit"]["results"] == []


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


def test_report_markdown_writes_to_file() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_file = Path(tmpdir) / "passwords.txt"
        audit_file.write_text("password\n")
        out_file = Path(tmpdir) / "report.md"

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
                "--out",
                str(out_file),
            ],
        )

        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "# ethscan Report" in content
        assert "## Port Scan" in content
        assert "## Password Audit" in content