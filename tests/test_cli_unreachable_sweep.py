"""Permanent sweep test: the CLI reports an unreachable target, never raises.

The module sweep (``tests/test_protocol_hostile_sweep.py``) checks that a
transport failure is reported through the module's own failure field. This
sweep checks the same invariant one level up, at the command line: a command
that cannot reach its target must print its own failure signal and exit 0,
the way it does against a target that is really unreachable.

The transport is patched, so the sweep needs no network and does not depend on
what the machine that runs it can reach. Each command keeps its own failure
signal: the ping command reports a failed probe, the osdetect command a
NO-RESPONSE probe, and the four DNS commands the absence of records.
"""
from __future__ import annotations

import json
import socket
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: TEST-NET-1 (RFC 5737): reserved for documentation, never routable.
UNREACHABLE_HOST = "192.0.2.1"

#: ".invalid" (RFC 2606): reserved, never resolvable.
UNRESOLVABLE_HOST = "host.invalid"


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


def test_ping_cli_reports_an_unreachable_target(monkeypatch) -> None:
    """The ping command reports a failed probe and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.ping.socket.socket", boom)

    report = _run_cli(["ping", "--target", UNREACHABLE_HOST, "--count", "1"])

    probe = report["probes"][0]
    assert probe["response_type"] == "NO-RESPONSE"
    assert probe["error"]
    assert report["failed"] == 1
    assert report["successful"] == 0


def test_osdetect_cli_reports_an_unreachable_target(monkeypatch) -> None:
    """The osdetect command reports a NO-RESPONSE probe and exits 0."""

    def boom(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr("ethscan.osdetect.socket.create_connection", boom)

    report = _run_cli(["osdetect", "--target", UNREACHABLE_HOST])

    probe = report["probes"][0]
    assert probe["response"] == "NO-RESPONSE"
    assert probe["error"]
    assert report["inferred_os"] == []


def test_resolve_cli_reports_an_unresolvable_target(monkeypatch) -> None:
    """The resolve command reports empty records and exits 0."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr("ethscan.resolve.socket.getaddrinfo", boom)

    report = _run_cli(["resolve", "--target", UNRESOLVABLE_HOST, "--types", "A"])

    assert report["records"]["A"] == []


def test_dns_cli_reports_an_unresolvable_target(monkeypatch) -> None:
    """The dns command reports empty records and exits 0."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr("ethscan.dns.socket.getaddrinfo", boom)

    report = _run_cli(["dns", "--target", UNRESOLVABLE_HOST, "--types", "A"])

    assert report["records"]["A"] == []


def test_stale_cli_reports_an_unresolvable_target(monkeypatch) -> None:
    """The stale command reports a stale domain and exits 0."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr("ethscan.stale.socket.getaddrinfo", boom)

    report = _run_cli(["stale", "--target", UNRESOLVABLE_HOST])

    entry = report["results"][0]
    assert entry["A"] == []
    assert entry["stale"] is True


def test_subdomains_cli_reports_an_unresolvable_target(monkeypatch) -> None:
    """The subdomains command reports unresolved names and exits 0."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr("ethscan.subdomains.socket.gethostbyname", boom)

    report = _run_cli(["subdomains", "--target", UNRESOLVABLE_HOST])

    assert report["resolved"] == []
    assert report["all_results"]
    assert all(entry["ip"] is None for entry in report["all_results"])
