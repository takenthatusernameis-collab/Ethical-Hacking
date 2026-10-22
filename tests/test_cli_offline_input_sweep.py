"""Permanent sweep test: the offline commands report an unusable input, never raise.

The other CLI sweeps check the commands that reach a target over the network.
This sweep checks the ten commands that work offline: the audit, cidr,
completion, config, hash, jwt, nmap, radix, validate and wifi commands. A
command that is given an input it cannot use must report the problem in its
own output and never leak a traceback.

The input of an offline command is foreign data too: a password file, a
network specification, a configuration file, a token, a port specification or
the output of another tool. Each command keeps its own failure signal: the
audit, cidr, nmap and radix commands a usage error that names the option at
fault, the completion command a usage error for an unsupported shell, the
config command the ``parse_error`` of the file it cannot read, the hash and
jwt commands the ``error`` of their report, the validate command the ``error``
of the specification it cannot use, and the wifi command the notes of a scan
that found nothing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: Every check of this sweep runs offline: the commands it checks do not
#: reach the network, and the fixture keeps it that way.
pytestmark = pytest.mark.usefixtures("no_external_network")


def _run_cli(args: list[str]) -> dict[str, Any]:
    """Run *args* through the CLI and return the JSON report it printed."""
    result = CliRunner().invoke(cli.cli, args)

    assert result.exit_code == 0, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in result.output, (
        f"{args} leaked a traceback:\n{result.output}"
    )
    return json.loads(result.output)


def _run_cli_usage_error(args: list[str], expected: str) -> None:
    """Run *args* and check that it reports a usage error naming *expected*.

    A usage error is the documented answer of a command to an input it
    cannot use: it names the option at fault and exits with the code click
    uses for it, instead of raising.
    """
    result = CliRunner().invoke(cli.cli, args)

    assert result.exit_code == 2, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in result.output, (
        f"{args} leaked a traceback:\n{result.output}"
    )
    assert expected in result.output, (
        f"{args} did not report {expected!r}:\n{result.output}"
    )


def test_audit_cli_reports_a_file_it_cannot_read(tmp_path: Path) -> None:
    """The audit command reports a credential file it cannot read.

    A credential file that is not valid UTF-8 cannot be read without changing
    the credentials it holds, so the command refuses it and names the option
    at fault.
    """
    password_file = tmp_path / "passwords.txt"
    password_file.write_bytes(b"\xff\xfe\n")

    _run_cli_usage_error(
        ["audit", "--file", str(password_file)],
        "the file is not valid UTF-8",
    )


def test_cidr_cli_reports_a_network_it_cannot_use() -> None:
    """The cidr command reports a network it cannot use."""
    _run_cli_usage_error(
        ["cidr", "--cidr", "not-a-network"],
        "does not appear to be an IPv4 or IPv6 network",
    )


def test_radix_cli_reports_a_network_it_cannot_use() -> None:
    """The radix command reports a network it cannot use."""
    _run_cli_usage_error(
        ["radix", "--cidrs", "not-a-network"],
        "does not appear to be an IPv4 or IPv6 network",
    )


def test_nmap_cli_reports_a_file_it_cannot_parse(tmp_path: Path) -> None:
    """The nmap command reports a file that does not hold Nmap XML."""
    scan_file = tmp_path / "scan.xml"
    scan_file.write_text("<notnmap>")

    _run_cli_usage_error(
        ["nmap", "--input-file", str(scan_file)],
        "invalid Nmap XML",
    )


def test_completion_cli_reports_an_unsupported_shell() -> None:
    """The completion command reports a shell it cannot generate a script for."""
    _run_cli_usage_error(
        ["completion", "tcsh"],
        "is not one of 'bash', 'zsh', 'fish'",
    )


def test_completion_cli_names_the_variable_the_shell_calls() -> None:
    """The completion command names the variable the shell will call.

    Click derives the name of the completion variable from the name of the
    program, so the generated script has to use the same name: a script that
    calls another variable can never be triggered.
    """
    report = _run_cli(["completion", "bash", "--prog-name", "my-tool"])

    assert report["prog_name"] == "my-tool"
    assert "_MY_TOOL_COMPLETE" in report["script"]


def test_config_cli_reports_a_file_it_cannot_parse(tmp_path: Path) -> None:
    """The config command reports a configuration file it cannot use.

    A configuration file holds a mapping; a file that holds something else
    cannot be used, and the command says so in its report instead of raising.
    """
    config_file = tmp_path / "ethscan.yaml"
    config_file.write_text("- a\n- b\n")

    report = _run_cli(["config", "--config", str(config_file)])

    assert "must be a mapping" in (report.get("parse_error") or "")
    assert report["defaults"] == {}
    assert report["commands"] == {}


def test_hash_cli_reports_a_digest_it_cannot_compare() -> None:
    """The hash command reports a digest whose algorithm it cannot infer.

    The algorithm of a digest is inferred from its length, so a digest of a
    length no algorithm has cannot be compared: the report says so and
    compares nothing.
    """
    report = _run_cli(["hash", "--password", "secret", "--check", "abc"])

    assert report["match"] is None
    assert report["computed"] is None
    assert "Could not infer algorithm" in (report.get("error") or "")


def test_jwt_cli_reports_a_token_it_cannot_read() -> None:
    """The jwt command reports a token that is not a JWT."""
    report = _run_cli(["jwt", "--token", "not-a-jwt"])

    assert report["valid_structure"] is False
    assert report["error"] == "Invalid JWT structure"
    assert report["findings"]


def test_jwt_cli_reports_a_header_that_is_not_an_object() -> None:
    """The jwt command reports a header segment that is not an object.

    A segment of a token can hold any JSON value, not only an object, so a
    header that holds a list is read as a segment that cannot be read.
    """
    report = _run_cli(["jwt", "--token", "WzEsMl0.e30."])

    assert report["valid_structure"] is True
    assert report["header"] is None
    assert any(
        finding.startswith("Could not decode header segment")
        for finding in report["findings"]
    )


def test_validate_cli_reports_a_specification_it_cannot_use() -> None:
    """The validate command reports a port specification it cannot use."""
    report = _run_cli(["validate", "--ports", "notaport"])

    entry = report["ports"][0]
    assert entry["valid"] is False
    assert entry["error"] == "Invalid port number 'notaport'"
    assert report["summary"]["all_valid"] is False


def _wireless_interface() -> list[dict[str, object]]:
    """Return the single wireless interface the wifi checks scan."""
    return [
        {
            "interface": "wlan0",
            "status": "0000",
            "link_quality": 45.0,
            "signal_level": -45.0,
            "noise_level": -256,
        }
    ]


def test_wifi_cli_reports_a_failed_scan(monkeypatch) -> None:
    """The wifi command reports a scan that found nothing.

    The Wi-Fi tools are the transport of the command: a tool that fails, or
    that fails in a way the module does not know, is a scan that found
    nothing, never a crash of the command.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.wifi._is_linux", lambda: True)
    monkeypatch.setattr("ethscan.wifi._parse_proc_net_wireless", lambda *a, **k: _wireless_interface())
    monkeypatch.setattr("ethscan.wifi.subprocess.run", boom)

    report = _run_cli(["wifi"])

    assert report["platform_supported"] is True
    assert report["access_points"] == []
    assert any("wlan0" in note for note in report["notes"])


def test_wifi_cli_reports_output_it_cannot_decode(monkeypatch) -> None:
    """The wifi command reports output of the tool it cannot decode.

    An SSID is an arbitrary 32-byte string, so the output of the Wi-Fi tools
    can hold a byte that is not valid UTF-8.
    """

    def boom(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr("ethscan.wifi._is_linux", lambda: True)
    monkeypatch.setattr("ethscan.wifi._parse_proc_net_wireless", lambda *a, **k: _wireless_interface())
    monkeypatch.setattr("ethscan.wifi.subprocess.run", boom)

    report = _run_cli(["wifi"])

    assert report["access_points"] == []
    assert any("wlan0" in note for note in report["notes"])
