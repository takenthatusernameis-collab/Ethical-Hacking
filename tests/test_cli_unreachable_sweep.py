"""Permanent sweep test: the CLI reports an unreachable target, never raises.

The module sweep (``tests/test_protocol_hostile_sweep.py``) checks that a
transport failure is reported through the module's own failure field. This
sweep checks the same invariant one level up, at the command line: a command
that cannot reach its target must print its own failure signal and exit 0,
the way it does against a target that is really unreachable.

The transport is patched, so the sweep needs no network and does not depend on
what the machine that runs it can reach. Each command keeps its own failure
signal: the ping command reports a failed probe, the osdetect command a
NO-RESPONSE probe, the four DNS commands the absence of records, the scan and
service commands the absence of an open port, and the protocol commands the
error of their own probe.
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


def test_osdetect_cli_reports_a_hostile_transport(monkeypatch) -> None:
    """The osdetect command reports a transport error of an unknown type.

    A transport that fails with a type the module does not name (a
    ``RuntimeError``, not the ``socket.timeout`` the probe knows) must still be
    reported through the probe's own failure field and never raised.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr("ethscan.osdetect.socket.create_connection", boom)

    report = _run_cli(["osdetect", "--target", UNREACHABLE_HOST])

    probe = report["probes"][0]
    assert probe["response"] == "NO-RESPONSE"
    assert "hostile transport" in probe["error"]
    assert report["inferred_os"] == []


def test_resolve_cli_reports_an_unresolvable_target(monkeypatch) -> None:
    """The resolve command reports empty records and exits 0."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr("ethscan.resolve.socket.getaddrinfo", boom)

    report = _run_cli(["resolve", "--target", UNRESOLVABLE_HOST, "--types", "A"])

    assert report["records"]["A"] == []


def test_resolve_cli_reports_a_hostile_transport(monkeypatch) -> None:
    """The resolve command reports a transport error of an unknown type.

    A resolver that fails with a type the module does not name must still be
    reported as an empty record set and never raised.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

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


def test_dns_cli_reports_a_hostile_transport(monkeypatch) -> None:
    """The dns command reports a transport error of an unknown type and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

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


def test_stale_cli_reports_a_hostile_transport(monkeypatch) -> None:
    """The stale command reports a transport error of an unknown type and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

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


def test_subdomains_cli_reports_a_hostile_transport(monkeypatch) -> None:
    """The subdomains command reports a transport error of an unknown type and exits 0."""

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

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


# ---------------------------------------------------------------------------
# The protocol commands that take a connector seam. The command line never
# injects a connector, so the transport that is patched here is the socket
# the module really opens; each command reports its own failure signal and
# exits 0.
# ---------------------------------------------------------------------------


def _hostile_transport(monkeypatch, seam: str) -> None:
    """Make the transport at *seam* fail with an error type the module ignores.

    A failure the module does not know is the interesting one: it has to be
    reported through the module's own failure field, never raised.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(seam, boom)


def test_redis_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The redis command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.redis.socket.socket")

    report = _run_cli(["redis", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_memcached_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The memcached command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.memcached.socket.socket")

    report = _run_cli(["memcached", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_ntp_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The ntp command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.ntp.socket.socket")

    report = _run_cli(["ntp", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["time_response"] is None
    assert report["is_reflector"] is False
    assert "hostile transport" in (report["error"] or "")


def test_ldap_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The ldap command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.ldap.socket.socket")

    report = _run_cli(["ldap", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_smb_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The smb command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.smb.socket.socket")

    report = _run_cli(["smb", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["accessible"] is False
    assert "hostile transport" in (report["error"] or "")


def test_snmp_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The snmp command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.snmp.socket.socket")

    report = _run_cli(["snmp", "--target", "127.0.0.1", "--timeout", "1.0"])

    assert report["communities"] == []
    assert "hostile transport" in (report["error"] or "")


def test_ssh_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The ssh command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.ssh.socket.create_connection")

    report = _run_cli(["ssh", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["banner"] is None
    assert "hostile transport" in (report["error"] or "")


def test_ssl_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The ssl command reports a failed probe and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.ssl.socket.create_connection")

    report = _run_cli(["ssl", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["cert"] is None
    assert report["valid"] is False
    assert "hostile transport" in (report["error"] or "")


def test_tls_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The tls command reports a failed probe per version and per cipher."""
    _hostile_transport(monkeypatch, "ethscan.tls.socket.create_connection")

    report = _run_cli(["tls", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["versions"]
    assert report["ciphers"]
    for entry in report["versions"]:
        assert entry["supported"] is False
        assert "hostile transport" in (entry["error"] or "")
    for entry in report["ciphers"]:
        assert entry["supported"] is False
        assert entry["error"]
    assert report["supported_versions"] == []
    assert report["supported_ciphers"] == []


def test_whois_cli_reports_a_failed_lookup(monkeypatch) -> None:
    """The whois command reports a failed lookup and exits 0."""

    class _FailingSocket:
        """A socket whose connection fails like a refused one does."""

        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, *args, **kwargs):
            pass

        def connect(self, *args, **kwargs):
            raise RuntimeError("hostile transport")

        def close(self, *args, **kwargs):
            pass

    monkeypatch.setattr("ethscan.whois.socket.socket", _FailingSocket)

    report = _run_cli(
        [
            "whois",
            "--target",
            "example.com",
            "--server",
            "127.0.0.1",
            "--timeout",
            "1.0",
        ]
    )

    assert report["raw"] == ""
    assert "Connection failed" in (report["error"] or "")
    assert "hostile transport" in (report["error"] or "")


def test_service_cli_reports_a_closed_port(monkeypatch) -> None:
    """The service command reports closed ports and exits 0."""
    _hostile_transport(monkeypatch, "ethscan.service.socket.create_connection")

    report = _run_cli(
        [
            "service",
            "--target",
            UNREACHABLE_HOST,
            "--ports",
            "80,443",
            "--timeout",
            "1.0",
        ]
    )

    assert report["ports_scanned"] == 2
    assert report["services_found"] == 0
    assert report["results"] == []


def test_dnssec_cli_reports_a_failed_probe(monkeypatch) -> None:
    """The dnssec command reports a failed probe and exits 0.

    Both the stdlib path and the dnspython path are stubbed, so the check
    holds whether or not dnspython is installed.
    """

    def boom(*args, **kwargs):
        raise RuntimeError("hostile transport")

    monkeypatch.setattr(
        "ethscan.dnssec._resolve_nameservers", lambda domain, timeout: ["127.0.0.1"]
    )
    monkeypatch.setattr("ethscan.dnssec._query_dnskey_raw", boom)
    monkeypatch.setattr("ethscan.dnssec._query_dnskey_dnspython", boom)

    report = _run_cli(["dnssec", "--target", "example.com", "--timeout", "1.0"])

    assert report["validated"] is False
    assert "hostile transport" in (report["dnskey"]["error"] or "")
    assert "hostile transport" in (report["ds"]["error"] or "")
