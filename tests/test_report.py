"""Tests for the ethscan report command."""

import csv
import io
import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from ethscan.cli import cli
from ethscan.report import (
    format_report_csv,
    format_report_json,
    format_report_markdown,
    run_report,
)


def test_run_report_offline() -> None:
    data = run_report("127.0.0.1", "80,443", timeout=0.1, workers=10)
    assert data["scan"]["target"] == "127.0.0.1"
    assert data["scan"]["ports_scanned"] == 2
    assert len(data["scan"]["details"]) == 2
    assert data["audit"]["passwords_audited"] == 0
    assert data["audit"]["results"] == []


def test_run_report_ports_common() -> None:
    data = run_report("127.0.0.1", "common", timeout=0.1, workers=10)
    assert data["scan"]["ports_scanned"] > 0
    assert data["scan"]["ports_scanned"] == len(data["scan"]["details"])


def test_run_report_ports_all() -> None:
    data = run_report("127.0.0.1", "all", timeout=0.01, workers=500)
    assert data["scan"]["ports_scanned"] == 65535


def test_run_report_with_audit_file(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n123456\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file)
    )
    assert data["audit"]["passwords_audited"] == 2
    assert len(data["audit"]["results"]) == 2
    assert data["audit"]["results"][0]["password"] == "password"
    for key in ("length", "entropy", "common", "patterns", "score", "verdict"):
        assert key in data["audit"]["results"][0]


def test_run_report_with_min_length(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("short\nlongenoughpassword\n")
    data = run_report(
        "127.0.0.1",
        "80",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
        min_length=10,
    )
    assert data["audit"]["passwords_audited"] == 2
    assert data["audit"]["min_length"] == 10
    short_result = data["audit"]["results"][0]
    long_result = data["audit"]["results"][1]
    assert short_result["password"] == "short"
    assert short_result["too_short"] is True
    assert long_result["password"] == "longenoughpassword"
    assert long_result["too_short"] is False


def test_run_report_min_length_defaults_to_none() -> None:
    data = run_report("127.0.0.1", "80", timeout=0.1, workers=10)
    assert data["audit"]["min_length"] is None


def test_format_report_json_with_min_length() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": 10,
            "results": [
                {
                    "password": "short",
                    "length": 5,
                    "entropy": 2.0,
                    "common": False,
                    "patterns": False,
                    "too_short": True,
                    "score": 1.0,
                    "verdict": "very weak",
                }
            ],
        },
    }
    parsed = json.loads(format_report_json(data))
    assert parsed["audit"]["min_length"] == 10
    assert parsed["audit"]["results"][0]["too_short"] is True


def test_format_report_markdown_with_min_length() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 2,
            "min_length": 10,
            "results": [
                {
                    "password": "short",
                    "length": 5,
                    "entropy": 2.0,
                    "common": False,
                    "patterns": False,
                    "too_short": True,
                    "score": 1.0,
                    "verdict": "very weak",
                },
                {
                    "password": "longenoughpassword",
                    "length": 16,
                    "entropy": 4.0,
                    "common": False,
                    "patterns": False,
                    "too_short": False,
                    "score": 5.0,
                    "verdict": "weak",
                },
            ],
        },
    }
    output = format_report_markdown(data)
    assert "Min Length" in output
    assert "**Min Length:** 10" in output
    assert "Too Short" in output
    assert "short" in output
    assert "longenoughpassword" in output


def test_format_report_csv_with_min_length() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": 10,
            "results": [
                {
                    "password": "short",
                    "length": 5,
                    "entropy": 2.0,
                    "common": False,
                    "patterns": False,
                    "too_short": True,
                    "score": 1.0,
                    "verdict": "very weak",
                }
            ],
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert rows[1][0] == "audit"
    assert rows[1][3] == "short"
    assert rows[1][8] == "true"  # too_short column


def test_format_report_json() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 1, "open_ports": [], "details": [{"port": 80, "open": False}]},
        "audit": {"passwords_audited": 0, "results": []},
    }
    parsed = json.loads(format_report_json(data))
    assert parsed["scan"]["target"] == "h"


def test_format_report_markdown() -> None:
    data = {
        "scan": {
            "target": "127.0.0.1",
            "ports_scanned": 1,
            "open_ports": [],
            "details": [{"port": 80, "open": False}],
        },
        "audit": {"passwords_audited": 0, "results": []},
    }
    output = format_report_markdown(data)
    assert "# ethscan Report" in output
    assert "## Port Scan" in output
    assert "## Password Audit" in output
    assert "No passwords provided for audit." in output


def test_format_report_markdown_with_audit() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "results": [
                {
                    "password": "password",
                    "length": 8,
                    "entropy": 3.0,
                    "common": True,
                    "patterns": False,
                    "score": 2.0,
                    "verdict": "very weak",
                }
            ],
        },
    }
    output = format_report_markdown(data)
    assert "password" in output
    assert "very weak" in output
    assert "Yes" in output


def test_format_report_csv_header() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {"passwords_audited": 0, "results": []},
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert rows[0] == [
        "section",
        "port",
        "open",
        "password",
        "length",
        "entropy",
        "common",
        "patterns",
        "too_short",
        "score",
        "verdict",
    ]
    assert len(rows) == 1


def test_format_report_csv_scan_and_audit_rows() -> None:
    data = {
        "scan": {
            "target": "h",
            "ports_scanned": 2,
            "open_ports": [80],
            "details": [{"port": 80, "open": True}, {"port": 443, "open": False}],
        },
        "audit": {
            "passwords_audited": 1,
            "results": [
                {
                    "password": "secret",
                    "length": 6,
                    "entropy": 2.5,
                    "common": False,
                    "patterns": True,
                    "too_short": False,
                    "score": 3.0,
                    "verdict": "weak",
                }
            ],
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert len(rows) == 4
    assert rows[1] == ["scan", "80", "true", "", "", "", "", "", "", "", ""]
    assert rows[2] == ["scan", "443", "false", "", "", "", "", "", "", "", ""]
    assert rows[3][0] == "audit"
    assert rows[3][3] == "secret"
    assert rows[3][4] == "6"
    assert rows[3][5] == "2.5"
    assert rows[3][6] == "false"
    assert rows[3][7] == "true"
    assert rows[3][8] == "false"
    assert rows[3][9] == "3.0"
    assert rows[3][10] == "weak"


def test_format_report_csv_escapes_special_characters() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "results": [
                {
                    "password": "pass,word",
                    "length": 9,
                    "entropy": 3.0,
                    "common": False,
                    "patterns": False,
                    "score": 3.0,
                    "verdict": "weak",
                }
            ],
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert rows[1][3] == "pass,word"


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


def test_resolve_ports_and_defaults_no_profile() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "80,443", 1.0, 100, None
    )
    assert port_list == [80, 443]
    assert timeout == 1.0
    assert workers == 100


def test_resolve_ports_and_defaults_profile_fast() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "common", 1.0, 100, "fast"
    )
    assert len(port_list) == 18
    assert timeout == 0.5
    assert workers == 200


def test_resolve_ports_and_defaults_profile_normal() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "common", 1.0, 100, "normal"
    )
    assert len(port_list) == 24
    assert timeout == 1.0
    assert workers == 100


def test_resolve_ports_and_defaults_profile_full() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "common", 1.0, 100, "full"
    )
    assert len(port_list) > 1000
    assert timeout == 2.0
    assert workers == 50


def test_resolve_ports_and_defaults_profile_overrides_ports() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "80,443", 1.0, 100, "fast"
    )
    assert port_list == [80, 443]
    assert timeout == 0.5
    assert workers == 200


def test_resolve_ports_and_defaults_profile_explicit_timeout_workers() -> None:
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "common", 5.0, 50, "fast"
    )
    # Profile overrides the default "common" port selection; explicit
    # timeout/workers win over the profile defaults.
    assert len(port_list) == 18
    assert timeout == 5.0
    assert workers == 50


def test_run_report_profile_fast() -> None:
    data = run_report("127.0.0.1", "common", timeout=0.1, workers=10, profile="fast")
    assert data["scan"]["profile"] == "fast"
    assert data["scan"]["ports_scanned"] == 18


def test_run_report_profile_normal() -> None:
    data = run_report("127.0.0.1", "common", timeout=0.1, workers=10, profile="normal")
    assert data["scan"]["profile"] == "normal"
    assert data["scan"]["ports_scanned"] == 24


def test_run_report_profile_full() -> None:
    data = run_report("127.0.0.1", "common", timeout=0.1, workers=10, profile="full")
    assert data["scan"]["profile"] == "full"
    assert data["scan"]["ports_scanned"] > 1000


def test_run_report_profile_overrides_ports() -> None:
    data = run_report(
        "127.0.0.1", "80,443", timeout=0.1, workers=10, profile="fast"
    )
    assert data["scan"]["profile"] == "fast"
    assert data["scan"]["ports_scanned"] == 2


def test_run_report_profile_with_audit_file(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n")
    data = run_report(
        "127.0.0.1",
        "common",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
        profile="fast",
    )
    assert data["scan"]["profile"] == "fast"
    assert data["audit"]["passwords_audited"] == 1