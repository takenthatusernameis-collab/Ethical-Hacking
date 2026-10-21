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


# ---------------------------------------------------------------------------
# The ten commands of the session before this one. Their transport is a
# socket call (the database modules, the scanner and dnsbrute), a UDP socket
# (netbios) or an injectable connector (ftp, smtp); each reports its own
# failure signal at the command line and exits 0.
# ---------------------------------------------------------------------------


def test_scan_cli_reports_a_closed_port(monkeypatch) -> None:
    """The scan command reports closed ports and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.scanner.socket.create_connection", boom)

    report = _run_cli(
        ["scan", "--target", UNREACHABLE_HOST, "--ports", "80,443", "--timeout", "1.0"]
    )

    assert report["open_ports"] == []
    assert report["ports_scanned"] == 2
    assert all(not entry["open"] for entry in report["details"])


def test_dnsbrute_cli_reports_a_refused_zone_transfer(monkeypatch) -> None:
    """The dnsbrute command reports a refused transfer and exits 0.

    The raw socket path is the one that is exercised here, whatever the host
    has installed, so dnspython is disabled for the check.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.dnsbrute.socket.create_connection", boom)
    monkeypatch.setattr("ethscan.dnsbrute.DNS_AVAILABLE", False)
    monkeypatch.setattr("ethscan.dns.socket.getaddrinfo", boom)

    report = _run_cli(
        ["dnsbrute", "--target", UNRESOLVABLE_HOST, "--ns", "127.0.0.1", "--timeout", "1.0"]
    )

    assert report["axfr_success"] is False
    assert report["axfr"]
    assert "hostile transport" in (report["axfr"][0]["error"] or "")
    assert report["resolved"] == []


def _database_cli_report(monkeypatch, command, target, module):
    """Run a database command against a hostile transport and return the report."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(f"ethscan.{module}.socket.create_connection", boom)

    return _run_cli([command, "--target", target, "--timeout", "1.0"])


def test_mysql_cli_reports_a_refused_connection(monkeypatch) -> None:
    """The mysql command reports a refused connection and exits 0."""
    report = _database_cli_report(monkeypatch, "mysql", "127.0.0.1:1", "mysql")
    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_mongodb_cli_reports_a_refused_connection(monkeypatch) -> None:
    """The mongodb command reports a refused connection and exits 0."""
    report = _database_cli_report(monkeypatch, "mongodb", "127.0.0.1:1", "mongodb")
    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_postgresql_cli_reports_a_refused_connection(monkeypatch) -> None:
    """The postgresql command reports a refused connection and exits 0."""
    report = _database_cli_report(
        monkeypatch, "postgresql", "127.0.0.1:1", "postgresql"
    )
    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_mssql_cli_reports_a_refused_connection(monkeypatch) -> None:
    """The mssql command reports a refused connection and exits 0."""
    report = _database_cli_report(monkeypatch, "mssql", "127.0.0.1:1", "mssql")
    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_oracle_cli_reports_a_refused_connection(monkeypatch) -> None:
    """The oracle command reports a refused connection and exits 0."""
    report = _database_cli_report(monkeypatch, "oracle", "127.0.0.1:1", "oracle")
    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_netbios_cli_reports_a_failed_request(monkeypatch) -> None:
    """The netbios command reports a failed request and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.netbios.socket.socket", boom)

    report = _run_cli(["netbios", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert "node status request failed" in (report["error"] or "")
    assert "hostile transport" in (report["error"] or "")


def test_ftp_cli_reports_a_failed_connection(monkeypatch) -> None:
    """The ftp command reports a failed connection and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.ftp._connect", boom)

    report = _run_cli(["ftp", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["connected"] is False
    assert "hostile transport" in (report["error"] or "")


def test_smtp_cli_reports_a_failed_connection(monkeypatch) -> None:
    """The smtp command reports a failed connection and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.smtp._connect", boom)

    report = _run_cli(["smtp", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["connected"] is False
    assert "hostile transport" in (report["error"] or "")
