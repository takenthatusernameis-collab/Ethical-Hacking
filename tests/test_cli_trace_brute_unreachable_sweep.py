"""Permanent sweep test: the trace and brute commands report a failure, never raise.

The module sweep checks that a hostile transport is reported through the
module's own failure field. This sweep checks the same invariant one level
up, at the command line: a command whose transport fails must print its own
failure signal and exit 0, the way it does against a target that is really
unreachable.

The transport is patched, so the sweep needs no network and does not depend on
what the machine that runs it can reach. Each command keeps its own failure
signal: the trace command the ``error`` of the name lookup and the
``error_code`` of the hop it stopped at, the brute command the ``error`` of
the attempt.
"""
from __future__ import annotations

import json
import socket
import types
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: A target that is never reached: the transport is patched, so the target
#: only has to be well formed.
UNREACHABLE_HOST = "127.0.0.1"


@pytest.fixture(autouse=True)
def _restore_default_socket_timeout():
    """Restore the process-wide default socket timeout after every check.

    The resolution helpers call ``socket.setdefaulttimeout()``, which changes
    the default timeout of every socket created later in the process.
    """
    original = socket.getdefaulttimeout()
    yield
    socket.setdefaulttimeout(original)


def _run_cli(args: list[str]) -> dict[str, Any]:
    """Run *args* through the CLI and return the JSON report it printed."""
    result = CliRunner().invoke(cli.cli, args)

    assert result.exit_code == 0, f"{args} exited {result.exit_code}:\n{result.output}"
    assert "Traceback (most recent call last)" not in result.output, (
        f"{args} leaked a traceback:\n{result.output}"
    )
    return json.loads(result.output)


def _hostile_transport(monkeypatch, seam: str) -> None:
    """Make the transport at *seam* fail with an error type the module ignores.

    A failure the module does not know is the interesting one: it has to be
    reported through the module's own failure field, never raised.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(seam, boom)


def _wordlists(tmp_path: Path) -> tuple[Path, Path]:
    """Write a one-entry user and password wordlist and return their paths."""
    user_file = tmp_path / "users.txt"
    pass_file = tmp_path / "passwords.txt"
    user_file.write_text("admin\n")
    pass_file.write_text("admin\n")
    return user_file, pass_file


def _brute_args(user_file: Path, pass_file: Path, protocol: str = "ftp") -> list[str]:
    """Build the command line of the brute command for the given wordlists."""
    return [
        "brute",
        "--target",
        UNREACHABLE_HOST,
        "--protocol",
        protocol,
        "--user-file",
        str(user_file),
        "--pass-file",
        str(pass_file),
        "--timeout",
        "1.0",
    ]


def test_trace_cli_reports_a_failed_name_lookup(monkeypatch) -> None:
    """The trace command reports a failed name lookup and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.trace.socket.gethostbyname")

    report = _run_cli(["trace", "--target", "example.com", "--timeout", "1.0"])

    assert report["error"] == "hostile transport"
    assert report["reached"] is False
    assert report["hops"] == []


def test_trace_cli_reports_a_failed_socket(monkeypatch) -> None:
    """The trace command reports a failed socket and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.trace.socket.socket")

    report = _run_cli(["trace", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["error"] == "hostile transport"
    assert report["reached"] is False
    assert report["hops"][0]["error_code"] == "hostile transport"


def test_brute_cli_reports_a_failed_login(monkeypatch, tmp_path: Path) -> None:
    """The brute command reports a failed FTP login and exits 0."""

    class _FailingFTP:
        """An FTP client whose connection fails."""

        def __init__(self, *args, **kwargs) -> None:
            pass

        def connect(self, *args, **kwargs) -> None:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    monkeypatch.setattr("ethscan.brute.FTP", _FailingFTP)
    user_file, pass_file = _wordlists(tmp_path)

    report = _run_cli(_brute_args(user_file, pass_file))

    assert report["attempts"] == 1
    assert report["successful_count"] == 0
    assert report["results"][0]["error"] == "hostile transport"


def test_brute_cli_reports_an_unbuildable_client(monkeypatch, tmp_path: Path) -> None:
    """The brute command reports a client that cannot even be built and exits 0.

    The client is built inside the guarded block of the module, so a failure
    of the constructor is a failed attempt and not a crash of the command.
    """

    class _UnbuildableFTP:
        """An FTP client that cannot be constructed."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    monkeypatch.setattr("ethscan.brute.FTP", _UnbuildableFTP)
    user_file, pass_file = _wordlists(tmp_path)

    report = _run_cli(_brute_args(user_file, pass_file))

    assert report["attempts"] == 1
    assert report["successful_count"] == 0
    assert report["results"][0]["error"] == "hostile transport"


def test_brute_cli_reports_a_failed_ssh_login(monkeypatch, tmp_path: Path) -> None:
    """The brute command reports a failed SSH login and exits 0."""

    class _FailingSSHClient:
        """An SSH client whose connection fails."""

        def set_missing_host_key_policy(self, policy) -> None:
            pass

        def connect(self, *args, **kwargs) -> None:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.SSHClient = _FailingSSHClient
    fake_paramiko.AutoAddPolicy = lambda: None

    monkeypatch.setattr("ethscan.brute.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.brute.PARAMIKO_AVAILABLE", True)
    user_file, pass_file = _wordlists(tmp_path)

    report = _run_cli(_brute_args(user_file, pass_file, protocol="ssh"))

    assert report["attempts"] == 1
    assert report["successful_count"] == 0
    assert report["results"][0]["error"] == "hostile transport"


def test_brute_cli_reports_an_unbuildable_ssh_client(monkeypatch, tmp_path: Path) -> None:
    """The brute command reports an SSH client that cannot be built and exits 0.

    The client is built inside the guarded block of the module, so a failure
    of the constructor is a failed attempt and not a crash of the command.
    """

    class _UnbuildableSSHClient:
        """An SSH client that cannot be constructed."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.SSHClient = _UnbuildableSSHClient
    fake_paramiko.AutoAddPolicy = lambda: None

    monkeypatch.setattr("ethscan.brute.paramiko", fake_paramiko, raising=False)
    monkeypatch.setattr("ethscan.brute.PARAMIKO_AVAILABLE", True)
    user_file, pass_file = _wordlists(tmp_path)

    report = _run_cli(_brute_args(user_file, pass_file, protocol="ssh"))

    assert report["attempts"] == 1
    assert report["successful_count"] == 0
    assert report["results"][0]["error"] == "hostile transport"
