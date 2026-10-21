"""Permanent sweep test: the aggregator commands report a failure, never raise.

The module sweeps check that a hostile transport is reported through the
module's own failure field. This sweep checks the same invariant one level up,
at the command line, for the three commands that aggregate the work of other
modules: ``vuln``, ``recon`` and ``report``. A command whose transport fails
must print its own failure signal and exit 0, the way it does against a target
that is really unreachable.

The transport is patched, so the sweep needs no network and does not depend on
what the machine that runs it can reach. Each command keeps its own failure
signal: the vuln command the notes of its report, the report command the
closed ports of its scan section, the recon command the failure of each of the
modules it runs.

The ``vuln`` command reads the output of other commands from a file
(``--services-file``, ``--tls-file``, ``--ssl-file``). Those documents are
foreign data: a document that does not hold the expected shape is named in the
notes of the report, never raised.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: TEST-NET-1 (RFC 5737): reserved for documentation, never routable.
UNREACHABLE_HOST = "192.0.2.1"

#: A host whose resolution is patched in the checks that use it.
UNRESOLVABLE_HOST = "example.com"

#: Every check of this sweep runs offline: the transport the check is about is
#: patched, and every other transport fails at once instead of reaching the
#: network.
pytestmark = pytest.mark.usefixtures("no_external_network")


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


def _write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> str:
    """Write a JSON document and return its path."""
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return str(path)


def test_vuln_cli_reports_a_failed_service_detection(monkeypatch) -> None:
    """The vuln command reports a failed service detection and exits 0.

    vuln detects the services of the target with the service module; a
    hostile transport there must leave the report with its own failure signal
    (no service checked, no finding) instead of raising.
    """
    _hostile_transport(monkeypatch, "ethscan.service.socket.create_connection")

    report = _run_cli(["vuln", "--target", UNREACHABLE_HOST, "--timeout", "1.0"])

    assert report["services_checked"] == 0
    assert report["findings"] == []
    assert report["finding_count"] == 0
    assert "No service banners detected" in report["notes"]


def test_vuln_cli_reports_an_unusable_services_file(tmp_path: Path) -> None:
    """The vuln command reports a services file it cannot read and exits 0.

    The services file holds the output of the service command, so its
    ``results`` key holds a list of objects. A document that holds something
    else is named in the notes of the report, not raised.
    """
    services_file = _write_json(tmp_path, "services.json", {"results": "not a list"})

    report = _run_cli(
        ["vuln", "--target", UNREACHABLE_HOST, "--services-file", services_file]
    )

    assert report["services_checked"] == 0
    assert report["findings"] == []
    assert "Service data holds no 'results' list" in report["notes"]


def test_vuln_cli_reports_an_unusable_tls_file(tmp_path: Path) -> None:
    """The vuln command reports a TLS file it cannot read and exits 0.

    The TLS file holds the output of the tls command, so its
    ``supported_versions`` key holds a list of names.
    """
    tls_file = _write_json(tmp_path, "tls.json", {"supported_versions": 5})

    report = _run_cli(["vuln", "--target", UNREACHABLE_HOST, "--tls-file", tls_file])

    assert report["tls_checked"] is True
    assert report["findings"] == []
    assert "TLS data holds no 'supported_versions' list" in report["notes"]


def test_vuln_cli_reports_an_unusable_certificate_file(tmp_path: Path) -> None:
    """The vuln command reports a certificate file it cannot read and exits 0.

    The certificate file holds the output of the ssl command, so its ``cert``
    key holds the parsed certificate, whose ``key_size`` is a number.
    """
    ssl_file = _write_json(tmp_path, "ssl.json", {"cert": {"key_size": "small"}})

    report = _run_cli(["vuln", "--target", UNREACHABLE_HOST, "--ssl-file", ssl_file])

    assert report["certificate_checked"] is True
    assert report["findings"] == []
    assert "No known vulnerabilities matched" in report["notes"]


def test_vuln_cli_reports_a_certificate_file_without_a_certificate(
    tmp_path: Path,
) -> None:
    """The vuln command reports a certificate file without a certificate.

    The certificate file holds the output of the ssl command, so its ``cert``
    key holds the parsed certificate.
    """
    ssl_file = _write_json(tmp_path, "ssl.json", {"cert": 5})

    report = _run_cli(["vuln", "--target", UNREACHABLE_HOST, "--ssl-file", ssl_file])

    assert report["certificate_checked"] is True
    assert report["findings"] == []
    assert "Certificate data holds no 'cert' object" in report["notes"]


def test_vuln_cli_reports_service_entries_that_are_not_objects(tmp_path: Path) -> None:
    """The vuln command reports service entries it cannot read and exits 0.

    The services file holds the output of the service command, so every entry
    of its ``results`` list is an object.
    """
    services_file = _write_json(tmp_path, "services.json", {"results": ["not an object"]})

    report = _run_cli(
        ["vuln", "--target", UNREACHABLE_HOST, "--services-file", services_file]
    )

    assert report["services_checked"] == 0
    assert report["findings"] == []
    assert "Service data holds entries that are not objects" in report["notes"]


def test_report_cli_reports_a_failed_scan(monkeypatch) -> None:
    """The report command reports a failed scan and exits 0.

    The report command scans the ports of the target with the scanner
    module; a hostile transport there must leave the scan section with its
    own failure signal (no open port) instead of raising.
    """
    _hostile_transport(monkeypatch, "ethscan.scanner.socket.create_connection")

    report = _run_cli(
        ["report", "--target", UNREACHABLE_HOST, "--ports", "80,443", "--timeout", "1.0"]
    )

    assert report["scan"]["ports_scanned"] == 2
    assert report["scan"]["open_ports"] == []
    assert all(not entry["open"] for entry in report["scan"]["details"])


def test_recon_cli_reports_the_failure_of_every_module(monkeypatch) -> None:
    """The recon command reports the failure of every module it runs.

    Each module of a recon run keeps its own failure signal: the subdomains
    module reports unresolved names, the dns module empty records, the whois
    module the error of its lookup, the geo module its note and the trace
    module the error of its probe.
    """
    _hostile_transport(monkeypatch, "ethscan.subdomains.socket.gethostbyname")
    _hostile_transport(monkeypatch, "ethscan.dns.socket.getaddrinfo")
    _hostile_transport(monkeypatch, "ethscan.whois.socket.socket")
    _hostile_transport(monkeypatch, "ethscan.geo.socket.gethostbyname")
    _hostile_transport(monkeypatch, "ethscan.trace.socket.gethostbyname")
    # The dnspython path of the dns module talks to a real resolver, so it is
    # disabled for the check: the sweep must not depend on the network.
    monkeypatch.setattr("ethscan.dns.DNS_AVAILABLE", False)

    report = _run_cli(["recon", "--target", UNRESOLVABLE_HOST, "--timeout", "1.0"])

    assert report["modules_run"] == ["subdomains", "dns", "whois", "geo", "trace"]
    assert report["subdomains"]["resolved"] == []
    assert report["dns"]["records"]["A"] == []
    assert "hostile transport" in (report["whois"]["error"] or "")
    assert report["geo"]["geolocation"] is None
    assert report["trace"]["error"] == "hostile transport"
    assert report["trace"]["reached"] is False


def test_recon_cli_reports_a_failed_module(monkeypatch) -> None:
    """The recon command reports a module that fails and exits 0.

    A module that cannot run at all is caught by the recon module and
    recorded as a note; the command still prints its consolidated report.
    """
    _hostile_transport(monkeypatch, "ethscan.recon.run_dns")

    report = _run_cli(["recon", "--target", UNRESOLVABLE_HOST, "--modules", "dns"])

    assert report["modules_run"] == ["dns"]
    assert report["dns"] is None
    assert "dns module failed: hostile transport" in report["notes"]
