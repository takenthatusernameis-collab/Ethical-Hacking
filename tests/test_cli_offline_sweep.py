"""Permanent sweep test: the offline commands report a failure, never raise.

The other CLI sweeps check that a command whose transport fails prints its own
failure signal and exits 0. This sweep checks the same invariant for the ten
commands that do not open a transport of their own: they work on the file, the
value or the local tool the user hands them, so the failure they can meet is
not an unreachable target but a hostile input.

Each command keeps its own failure signal, and the signal is the one the
command documents: the audit and hash commands refuse a file that is not valid
UTF-8, the hash command reports a digest it cannot check, the cidr and radix
commands refuse a network that is not a network, the nmap command refuses a
file that is not Nmap XML, the jwt command reports the token it cannot decode,
the validate command reports the port it cannot use, the config command
reports the file it cannot parse, the wifi command reports the interface it
cannot scan and the completion command reports the shell it cannot generate a
script for.

The inputs are hostile, so the sweep needs no network and no local tool. A
command that refuses a value it cannot use reports it as a usage error (exit
2); a command that reports the failure in its report exits 0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: Every check of this sweep runs offline: the commands are offline, and the
#: network of the machine that runs the sweep must not change their result.
pytestmark = pytest.mark.usefixtures("no_external_network")


def _output_text(result: Any) -> str:
    """Return everything the command printed, on stdout and on stderr.

    Click mixes the two streams into ``output`` in the versions that support
    it and keeps them apart in the ones that do not, so both are read.
    """
    text = result.output or ""
    try:
        stderr = result.stderr
    except ValueError:  # pragma: no cover - the streams are mixed here
        stderr = ""
    return text + (stderr or "")


def _run_cli(args: list[str]) -> dict[str, Any]:
    """Run *args* through the CLI and return the JSON report it printed."""
    result = CliRunner().invoke(cli.cli, args)

    assert result.exit_code == 0, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in _output_text(result), (
        f"{args} leaked a traceback:\n{result.output}"
    )
    return json.loads(result.output)


def _run_cli_usage_error(args: list[str]) -> str:
    """Run *args* through the CLI and return the usage error it printed.

    A command that is handed a value it cannot use refuses it: it exits 2 and
    prints the reason, without a traceback.
    """
    result = CliRunner().invoke(cli.cli, args)

    assert result.exit_code == 2, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in _output_text(result), (
        f"{args} leaked a traceback:\n{result.output}"
    )
    return _output_text(result)


# ---------------------------------------------------------------------------
# The commands that read a file.
# ---------------------------------------------------------------------------


def test_audit_cli_refuses_a_file_that_is_not_utf8(tmp_path: Path) -> None:
    """The audit command refuses a password file it cannot read.

    A password file whose bytes are not valid UTF-8 cannot be audited
    without changing the passwords it holds, so the command refuses it.
    """
    wordlist = tmp_path / "passwords.txt"
    wordlist.write_bytes(b"\xff\xfehunter2\n")

    output = _run_cli_usage_error(["audit", "--file", str(wordlist)])

    assert "the file is not valid UTF-8" in output


def test_hash_cli_refuses_a_file_that_is_not_utf8(tmp_path: Path) -> None:
    """The hash command refuses a password file it cannot read."""
    wordlist = tmp_path / "passwords.txt"
    wordlist.write_bytes(b"\xff\xfehunter2\n")

    output = _run_cli_usage_error(["hash", "--file", str(wordlist)])

    assert "the file is not valid UTF-8" in output


def test_hash_cli_reports_a_digest_it_cannot_check() -> None:
    """The hash command reports a digest it cannot compare and exits 0.

    A digest whose length names no algorithm cannot be checked, and the
    report says so instead of pretending that the password does not match.
    """
    report = _run_cli(["hash", "--password", "hunter2", "--check", "zz"])

    assert report["match"] is None
    assert report["computed"] is None
    assert "Could not infer algorithm" in (report["error"] or "")


def test_nmap_cli_refuses_a_file_that_is_not_nmap_xml(tmp_path: Path) -> None:
    """The nmap command refuses a file that is not Nmap XML."""
    scan_file = tmp_path / "scan.xml"
    scan_file.write_text("not xml at all")

    output = _run_cli_usage_error(["nmap", "--input-file", str(scan_file)])

    assert "invalid Nmap XML" in output


def test_config_cli_reports_a_config_file_it_cannot_parse(tmp_path: Path) -> None:
    """The config command reports a config file it cannot parse and exits 0.

    A config file with broken YAML is a file that cannot be used, and the
    report names it in its ``parse_error`` field instead of failing.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text("defaults: [unclosed\n\tbad: : :\n")

    report = _run_cli(["config", "--config", str(config_file)])

    assert report["defaults"] == {}
    assert "Failed to parse" in report["parse_error"]


# ---------------------------------------------------------------------------
# The commands that work on a value.
# ---------------------------------------------------------------------------


def test_cidr_cli_refuses_a_network_that_is_not_a_network() -> None:
    """The cidr command refuses a network it cannot compute with."""
    output = _run_cli_usage_error(["cidr", "--cidr", "10.0.0.0/33"])

    assert "does not appear to be an IPv4 or IPv6 network" in output


def test_radix_cli_refuses_a_file_with_a_network_that_is_not_a_network(
    tmp_path: Path,
) -> None:
    """The radix command refuses a file that holds a network it cannot use."""
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("10.0.0.0/8\nnot-a-network\n")

    output = _run_cli_usage_error(["radix", "--cidr-file", str(cidr_file)])

    assert "does not appear to be an IPv4 or IPv6 network" in output


def test_jwt_cli_reports_a_token_it_cannot_decode() -> None:
    """The jwt command reports a token it cannot decode and exits 0.

    A token that is not two or three dot-separated segments is not a token,
    and the report says so in its ``error`` field.
    """
    report = _run_cli(["jwt", "--token", "not-a-token"])

    assert report["valid_structure"] is False
    assert report["error"] == "Invalid JWT structure"
    assert report["claims"] is None
    assert report["findings"]


def test_validate_cli_reports_a_port_it_cannot_use() -> None:
    """The validate command reports a port it cannot use and exits 0.

    A port outside the range of a port number cannot be expanded, and the
    report names it in the ``error`` field of its specification.
    """
    report = _run_cli(["validate", "--ports", "70000"])

    assert report["summary"]["all_valid"] is False
    assert report["ports"][0]["valid"] is False
    assert "out of range" in report["ports"][0]["error"]


# ---------------------------------------------------------------------------
# The commands that work on a local tool.
# ---------------------------------------------------------------------------


def test_wifi_cli_reports_a_scan_that_fails(monkeypatch) -> None:
    """The wifi command reports a scan tool that fails and exits 0.

    The scan is done by a local tool (``iw`` or ``iwlist``). A tool that
    fails in a way the module does not know leaves the interface unscanned,
    and the report names the failure in its notes instead of raising.
    """
    monkeypatch.setattr("ethscan.wifi.platform.system", lambda: "Linux")
    monkeypatch.setattr(
        "ethscan.wifi._parse_proc_net_wireless",
        lambda *args, **kwargs: [
            {
                "interface": "wlan0",
                "status": 0,
                "link_quality": 45.0,
                "signal_level": -45.0,
                "noise_level": -256.0,
            }
        ],
    )

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.wifi.subprocess.run", boom)

    report = _run_cli(["wifi"])

    assert report["access_points"] == []
    assert any("hostile transport" in note for note in report["notes"])


def test_completion_cli_reports_a_shell_it_cannot_generate(monkeypatch) -> None:
    """The completion command reports a shell it cannot generate for.

    The shell is one of the ones the option accepts, but the completion
    machinery of click does not know it (yet), so the command reports the
    shell it cannot generate a script for and exits 1.
    """
    monkeypatch.setattr("ethscan.completion._available_shells", lambda: {"bash": object()})

    result = CliRunner().invoke(cli.cli, ["completion", "zsh"])

    assert result.exit_code == 1, f"exited {result.exit_code}:\n{result.output}"
    # The command reports the shell and exits; it does not raise.
    assert isinstance(result.exception, SystemExit), (
        f"the command raised {result.exception!r} instead of reporting the shell"
    )
    assert "Traceback (most recent call last)" not in _output_text(result)
    assert "Unsupported shell: zsh" in _output_text(result)
