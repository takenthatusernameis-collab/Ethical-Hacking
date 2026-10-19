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
        "salt",
        "pepper",
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
                    "salt": False,
                    "pepper": False,
                }
            ],
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert len(rows) == 4
    assert rows[1] == ["scan", "80", "true", "", "", "", "", "", "", "", "", "", ""]
    assert rows[2] == ["scan", "443", "false", "", "", "", "", "", "", "", "", "", ""]
    assert rows[3][0] == "audit"
    assert rows[3][3] == "secret"
    assert rows[3][4] == "6"
    assert rows[3][5] == "2.5"
    assert rows[3][6] == "false"
    assert rows[3][7] == "true"
    assert rows[3][8] == "false"
    assert rows[3][9] == "3.0"
    assert rows[3][10] == "weak"
    assert rows[3][11] == "false"
    assert rows[3][12] == "false"


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


def test_resolve_ports_and_defaults_profile_with_all_ports_keyword() -> None:
    """An explicit ``--ports all`` must survive a profile override.

    The profile branch used to forward the raw keyword to
    ``parse_port_range()``, raising ``ValueError: invalid literal for int()
    with base 10: 'all'``.
    """
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "all", 1.0, 100, "fast"
    )
    assert port_list == list(range(1, 65536))
    # The profile still supplies its own timeout/worker defaults.
    assert timeout == 0.5
    assert workers == 200


def test_resolve_ports_and_defaults_profile_ports_keyword_is_case_insensitive() -> None:
    """``COMMON``/``All`` must behave like their lowercase counterparts."""
    from ethscan.report import _resolve_ports_and_defaults

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "COMMON", 1.0, 100, "fast"
    )
    assert len(port_list) == 18
    assert timeout == 0.5
    assert workers == 200

    port_list, timeout, workers = _resolve_ports_and_defaults(
        "All", 1.0, 100, "fast"
    )
    assert port_list == list(range(1, 65536))
    assert timeout == 0.5
    assert workers == 200


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


def test_run_report_open_only_filters_closed_ports(monkeypatch) -> None:
    from ethscan import report as report_module

    def fake_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(p, p in (80, 443)) for p in ports]

    monkeypatch.setattr(report_module, "scan_ports", fake_scan_ports)
    data = run_report("127.0.0.1", "80,443,22,3306", timeout=0.1, workers=10, open_only=True)
    assert data["scan"]["open_only"] is True
    assert len(data["scan"]["details"]) == 2
    assert all(d["open"] is True for d in data["scan"]["details"])
    details_ports = [d["port"] for d in data["scan"]["details"]]
    assert 80 in details_ports
    assert 443 in details_ports
    assert 22 not in details_ports
    assert 3306 not in details_ports


def test_run_report_open_only_default_false(monkeypatch) -> None:
    from ethscan import report as report_module

    def fake_scan_ports(host, ports, timeout=1.0, max_workers=100):
        return [(p, p in (80,)) for p in ports]

    monkeypatch.setattr(report_module, "scan_ports", fake_scan_ports)
    data = run_report("127.0.0.1", "80,443", timeout=0.1, workers=10)
    assert data["scan"]["open_only"] is False
    assert len(data["scan"]["details"]) == 2


def test_format_report_json_open_only() -> None:
    data = {
        "scan": {
            "target": "h",
            "ports_scanned": 1,
            "open_ports": [80],
            "details": [{"port": 80, "open": True}],
            "open_only": True,
        },
        "audit": {"passwords_audited": 0, "results": []},
    }
    parsed = json.loads(format_report_json(data))
    assert parsed["scan"]["open_only"] is True
    assert len(parsed["scan"]["details"]) == 1
    assert all(d["open"] is True for d in parsed["scan"]["details"])


def test_format_report_markdown_open_only() -> None:
    data = {
        "scan": {
            "target": "h",
            "ports_scanned": 2,
            "open_ports": [80],
            "details": [{"port": 80, "open": True}],
            "open_only": True,
        },
        "audit": {"passwords_audited": 0, "results": []},
    }
    output = format_report_markdown(data)
    assert "**Open Only:** Yes" in output
    assert "| 80 | Open |" in output
    assert "443" not in output


def test_format_report_markdown_open_only_false() -> None:
    data = {
        "scan": {
            "target": "h",
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
    output = format_report_markdown(data)
    assert "**Open Only:** No" in output
    assert "| 80 | Open |" in output
    assert "| 443 | Closed |" in output


def test_format_report_csv_open_only() -> None:
    data = {
        "scan": {
            "target": "h",
            "ports_scanned": 2,
            "open_ports": [80],
            "details": [{"port": 80, "open": True}],
            "open_only": True,
        },
        "audit": {"passwords_audited": 0, "results": []},
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    assert len(rows) == 2
    assert rows[1][0] == "scan"
    assert rows[1][1] == "80"
    assert rows[1][2] == "true"


# --- sort option tests ---


def _audit_results():
    return [
        {"password": "a", "length": 1, "entropy": 1.0, "common": False, "patterns": False, "too_short": False, "score": 10.0, "verdict": "strong"},
        {"password": "b", "length": 8, "entropy": 3.0, "common": True, "patterns": False, "too_short": False, "score": 20.0, "verdict": "weak"},
        {"password": "c", "length": 16, "entropy": 4.0, "common": False, "patterns": True, "too_short": False, "score": 30.0, "verdict": "fair"},
    ]


def test_run_report_sort_by_score_desc(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
        sort_by="score", sort_desc=True,
    )
    scores = [r["score"] for r in data["audit"]["results"]]
    assert scores == sorted(scores, reverse=True)
    assert data["audit"]["sort_by"] == "score"
    assert data["audit"]["sort_desc"] is True


def test_run_report_sort_by_score_asc(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
        sort_by="score", sort_desc=False,
    )
    scores = [r["score"] for r in data["audit"]["results"]]
    assert scores == sorted(scores)
    assert data["audit"]["sort_desc"] is False


def test_run_report_sort_by_length_desc(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
        sort_by="length", sort_desc=True,
    )
    lengths = [r["length"] for r in data["audit"]["results"]]
    assert lengths == sorted(lengths, reverse=True)
    assert data["audit"]["sort_by"] == "length"


def test_run_report_sort_by_verdict_desc(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
        sort_by="verdict", sort_desc=True,
    )
    verdicts = [r["verdict"].lower() for r in data["audit"]["results"]]
    assert verdicts == sorted(verdicts, reverse=True)
    assert data["audit"]["sort_by"] == "verdict"


def test_run_report_sort_defaults_to_none(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
    )
    assert data["audit"]["sort_by"] is None
    assert data["audit"]["sort_desc"] is True


def test_run_report_sort_preserves_original_when_invalid(tmp_path) -> None:
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("a\nb\nc\n")
    data = run_report(
        "127.0.0.1", "80", timeout=0.1, workers=10, audit_file=str(audit_file),
        sort_by="bogus",
    )
    assert data["audit"]["sort_by"] == "bogus"
    # Invalid key keeps original order (a, b, c)
    assert [r["password"] for r in data["audit"]["results"]] == ["a", "b", "c"]


def test_format_report_json_with_sort() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 3,
            "min_length": None,
            "sort_by": "score",
            "sort_desc": True,
            "results": sorted(
                _audit_results(),
                key=lambda r: r["score"],
                reverse=True,
            ),
        },
    }
    parsed = json.loads(format_report_json(data))
    assert parsed["audit"]["sort_by"] == "score"
    assert parsed["audit"]["sort_desc"] is True
    assert parsed["audit"]["results"][0]["score"] == 30.0


def test_format_report_markdown_with_sort() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 3,
            "min_length": None,
            "sort_by": "length",
            "sort_desc": False,
            "results": sorted(
                _audit_results(),
                key=lambda r: r["length"],
            ),
        },
    }
    output = format_report_markdown(data)
    assert "**Sorted By:** length (Ascending)" in output
    # Ascending length order: 1, 8, 16 (passwords rendered with repr quotes)
    idx_a = output.index("| 'a' ")
    idx_b = output.index("| 'b' ")
    idx_c = output.index("| 'c' ")
    assert idx_a < idx_b < idx_c


def test_format_report_csv_with_sort() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 3,
            "min_length": None,
            "sort_by": "score",
            "sort_desc": True,
            "results": sorted(
                _audit_results(),
                key=lambda r: r["score"],
                reverse=True,
            ),
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    # Header + 3 audit rows
    assert len(rows) == 4
    # Descending score: 30, 20, 10
    assert rows[1][9] == "30.0"
    assert rows[2][9] == "20.0"
    assert rows[3][9] == "10.0"


def test_run_report_with_salt_and_pepper(tmp_path, monkeypatch) -> None:
    """Test run_report with salt and pepper options."""
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n")

    def mock_scan_ports(host, port_list, timeout=1.0, max_workers=100):
        return [(80, False)]

    monkeypatch.setattr("ethscan.report.scan_ports", mock_scan_ports)

    data = run_report(
        "127.0.0.1",
        "80",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
        salt="mysalt",
        pepper="mysecret",
        algorithm="sha256",
    )
    assert data["audit"]["salt"] is True
    assert data["audit"]["pepper"] is True
    assert data["audit"]["results"][0]["salt"] is True
    assert data["audit"]["results"][0]["pepper"] is True
    # Length should be 64 for SHA-256 hex digest
    assert data["audit"]["results"][0]["length"] == 64


def test_run_report_with_salt_only(tmp_path, monkeypatch) -> None:
    """Test run_report with salt only."""
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n")

    def mock_scan_ports(host, port_list, timeout=1.0, max_workers=100):
        return [(80, False)]

    monkeypatch.setattr("ethscan.report.scan_ports", mock_scan_ports)

    data = run_report(
        "127.0.0.1",
        "80",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
        salt="mysalt",
        algorithm="sha256",
    )
    assert data["audit"]["salt"] is True
    assert data["audit"]["pepper"] is False
    assert data["audit"]["results"][0]["salt"] is True
    assert data["audit"]["results"][0]["pepper"] is False


def test_run_report_with_pepper_only(tmp_path, monkeypatch) -> None:
    """Test run_report with pepper only."""
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n")

    def mock_scan_ports(host, port_list, timeout=1.0, max_workers=100):
        return [(80, False)]

    monkeypatch.setattr("ethscan.report.scan_ports", mock_scan_ports)

    data = run_report(
        "127.0.0.1",
        "80",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
        pepper="mysecret",
        algorithm="sha256",
    )
    assert data["audit"]["salt"] is False
    assert data["audit"]["pepper"] is True
    assert data["audit"]["results"][0]["salt"] is False
    assert data["audit"]["results"][0]["pepper"] is True


def test_run_report_salt_pepper_defaults_to_false(tmp_path, monkeypatch) -> None:
    """Test run_report defaults salt and pepper to False."""
    audit_file = tmp_path / "passwords.txt"
    audit_file.write_text("password\n")

    def mock_scan_ports(host, port_list, timeout=1.0, max_workers=100):
        return [(80, False)]

    monkeypatch.setattr("ethscan.report.scan_ports", mock_scan_ports)

    data = run_report(
        "127.0.0.1",
        "80",
        timeout=0.1,
        workers=10,
        audit_file=str(audit_file),
    )
    assert data["audit"]["salt"] is False
    assert data["audit"]["pepper"] is False
    assert data["audit"]["results"][0]["salt"] is False
    assert data["audit"]["results"][0]["pepper"] is False


def test_format_report_json_with_salt_pepper() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": None,
            "salt": True,
            "pepper": True,
            "results": [
                {
                    "password": "password",
                    "length": 64,
                    "entropy": 4.0,
                    "common": False,
                    "patterns": False,
                    "too_short": False,
                    "score": 10.0,
                    "verdict": "weak",
                    "salt": True,
                    "pepper": True,
                }
            ],
        },
    }
    parsed = json.loads(format_report_json(data))
    assert parsed["audit"]["salt"] is True
    assert parsed["audit"]["pepper"] is True
    assert parsed["audit"]["results"][0]["salt"] is True
    assert parsed["audit"]["results"][0]["pepper"] is True


def test_format_report_markdown_with_salt_pepper() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": None,
            "salt": True,
            "pepper": True,
            "results": [
                {
                    "password": "password",
                    "length": 64,
                    "entropy": 4.0,
                    "common": False,
                    "patterns": False,
                    "too_short": False,
                    "score": 10.0,
                    "verdict": "weak",
                    "salt": True,
                    "pepper": True,
                }
            ],
        },
    }
    output = format_report_markdown(data)
    assert "**Salt:** applied (prepended to password)" in output
    assert "**Pepper:** applied (HMAC key)" in output


def test_format_report_markdown_without_salt_pepper() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": None,
            "salt": False,
            "pepper": False,
            "results": [
                {
                    "password": "password",
                    "length": 8,
                    "entropy": 4.0,
                    "common": False,
                    "patterns": False,
                    "too_short": False,
                    "score": 10.0,
                    "verdict": "weak",
                    "salt": False,
                    "pepper": False,
                }
            ],
        },
    }
    output = format_report_markdown(data)
    assert "**Salt:**" not in output
    assert "**Pepper:**" not in output


def test_format_report_csv_with_salt_pepper() -> None:
    data = {
        "scan": {"target": "h", "ports_scanned": 0, "open_ports": [], "details": []},
        "audit": {
            "passwords_audited": 1,
            "min_length": None,
            "salt": True,
            "pepper": True,
            "results": [
                {
                    "password": "password",
                    "length": 64,
                    "entropy": 4.0,
                    "common": False,
                    "patterns": False,
                    "too_short": False,
                    "score": 10.0,
                    "verdict": "weak",
                    "salt": True,
                    "pepper": True,
                }
            ],
        },
    }
    rows = list(csv.reader(io.StringIO(format_report_csv(data))))
    # Header + 1 audit row
    assert len(rows) == 2
    assert rows[0][11] == "salt"
    assert rows[0][12] == "pepper"
    assert rows[1][11] == "true"
    assert rows[1][12] == "true"