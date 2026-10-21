"""Permanent sweep test: the HTTP-facing commands report a failure, never raise.

The module sweep (``tests/test_http_hostile_sweep.py``) checks that a hostile
HTTP answer is reported through the module's own failure field. This sweep
checks the same invariant one level up, at the command line: a command whose
transport fails must print its own failure signal and exit 0, the way it does
against a target that is really unreachable.

The transport is patched, so the sweep needs no network and does not depend on
what the machine that runs it can reach. Each command keeps its own failure
signal: the web and headers commands an ``error`` field, the fuzz command the
``error`` of every probed path, the urlcheck command the ``error`` of its web
part and of its certificate inspection, the cert, geo and mac commands the
``error`` of the data they could not fetch, the s3 command the ``error`` of
every probed bucket, and the cve and subtake commands a missing entry.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli

#: A target that is never reached: the transport is patched, so the target
#: only has to be well formed. The scheme is HTTPS, so the commands that
#: inspect a certificate really open a TLS connection.
UNREACHABLE_URL = "https://127.0.0.1:9/"


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


def _unresolvable_name(monkeypatch, seam: str) -> None:
    """Make the name resolution at *seam* fail the way a missing name does."""

    def boom(*args, **kwargs):
        raise socket.gaierror("name does not resolve")

    monkeypatch.setattr(seam, boom)


def test_web_cli_reports_a_failed_fetch(monkeypatch) -> None:
    """The web command reports a failed fetch and exits 0."""
    _hostile_transport(monkeypatch, "urllib.request.urlopen")
    _hostile_transport(monkeypatch, "ethscan.web.socket.create_connection")

    report = _run_cli(["web", "--target", UNREACHABLE_URL, "--timeout", "1.0"])

    assert "hostile transport" in (report["error"] or "")
    assert report["headers"] == {}
    assert report["security_headers"]["present_count"] == 0
    assert report["ssl"]["error"] == "hostile transport"
    assert report["ssl"]["valid"] is False


def test_headers_cli_reports_a_failed_fetch(monkeypatch) -> None:
    """The headers command reports a failed fetch and exits 0."""
    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(["headers", "--target", UNREACHABLE_URL, "--timeout", "1.0"])

    assert "hostile transport" in (report["error"] or "")
    assert report["headers"] == {}
    assert report["security_headers"]["present_count"] == 0


def test_fuzz_cli_reports_a_failed_probe(monkeypatch, tmp_path: Path) -> None:
    """The fuzz command reports a failed probe per path and exits 0."""
    wordlist = tmp_path / "paths.txt"
    wordlist.write_text("/admin\n/login\n")

    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(
        [
            "fuzz",
            "--target",
            UNREACHABLE_URL,
            "--wordlist",
            str(wordlist),
            "--timeout",
            "1.0",
        ]
    )

    assert report["paths_tested"] == 2
    assert report["findings"] == []
    assert len(report["all_results"]) == 2
    for entry in report["all_results"]:
        assert entry["status_code"] is None
        assert "hostile transport" in (entry["error"] or "")


def test_urlcheck_cli_reports_a_failed_fetch(monkeypatch, tmp_path: Path) -> None:
    """The urlcheck command reports a failed fetch and exits 0."""
    wordlist = tmp_path / "paths.txt"
    wordlist.write_text("/admin\n")

    _hostile_transport(monkeypatch, "urllib.request.urlopen")
    _hostile_transport(monkeypatch, "ethscan.ssl.socket.create_connection")

    report = _run_cli(
        [
            "urlcheck",
            "--target",
            UNREACHABLE_URL,
            "--wordlist",
            str(wordlist),
            "--timeout",
            "1.0",
        ]
    )

    assert "hostile transport" in (report["web"]["error"] or "")
    assert "hostile transport" in (report["ssl"]["error"] or "")
    assert report["ssl"]["cert"] is None
    assert report["ssl"]["valid"] is False
    fuzzed = report["fuzz"]["all_results"]
    assert len(fuzzed) == 1
    assert fuzzed[0]["status_code"] is None
    assert "hostile transport" in (fuzzed[0]["error"] or "")


def test_cert_cli_reports_a_failed_lookup(monkeypatch) -> None:
    """The cert command reports a failed lookup and exits 0."""
    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(
        [
            "cert",
            "--target",
            "127.0.0.1",
            "--timeout",
            "1.0",
            "--no-cache",
            "--no-offline-fallback",
        ]
    )

    assert report["ip"] == "127.0.0.1"
    assert report["cert_data"]["error"] == "Failed to fetch certificate transparency data"
    assert report["cert_data"]["entries"] == []
    assert report["subdomains"] == []


def test_geo_cli_reports_a_failed_lookup(monkeypatch) -> None:
    """The geo command reports a failed lookup and exits 0."""
    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(
        [
            "geo",
            "--target",
            "8.8.8.8",
            "--timeout",
            "1.0",
            "--no-cache",
            "--no-offline-fallback",
        ]
    )

    assert report["ip"] == "8.8.8.8"
    assert report["geolocation"]["status"] == "fail"
    assert report["geolocation"]["error"] == "Failed to fetch geolocation data"


def test_mac_cli_reports_a_failed_lookup(monkeypatch) -> None:
    """The mac command reports a failed lookup and exits 0."""
    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(
        [
            "mac",
            "--target",
            "00:1A:2B:3C:4D:5E",
            "--timeout",
            "1.0",
            "--no-cache",
            "--no-offline-fallback",
        ]
    )

    assert report["mac"] == "00:1a:2b:3c:4d:5e"
    assert report["mac_data"]["error"] == "Failed to fetch MAC vendor data"


def test_s3_cli_reports_a_failed_probe(monkeypatch, tmp_path: Path) -> None:
    """The s3 command reports a failed probe per bucket and exits 0."""
    wordlist = tmp_path / "buckets.txt"
    wordlist.write_text("mybucket\n")

    _hostile_transport(monkeypatch, "urllib.request.urlopen")
    # The endpoint of a bucket is resolved by name; the probe reports a
    # missing name and the request itself still fails.
    _unresolvable_name(monkeypatch, "ethscan.s3.socket.gethostbyname")

    report = _run_cli(
        [
            "s3",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist),
            "--timeout",
            "1.0",
        ]
    )

    assert report["results"]
    assert report["public_buckets"] == []
    assert report["existing_buckets"] == []
    for entry in report["results"]:
        assert entry["public"] is False
        assert entry["status_code"] is None
        assert entry["error"]
    probed = [entry for entry in report["results"] if entry["bucket"] == "mybucket"]
    assert len(probed) == 1
    # The reason of the failed probe, and not the class name of the
    # exception: the probe reports the failure itself.
    assert probed[0]["error"] == "hostile transport"


def test_cve_cli_reports_a_failed_lookup(monkeypatch, tmp_path: Path) -> None:
    """The cve command reports a failed lookup and exits 0."""
    services = tmp_path / "services.json"
    services.write_text(json.dumps({"services": [{"port": 22, "banner": "OpenSSH_7.2"}]}))

    _hostile_transport(monkeypatch, "urllib.request.urlopen")

    report = _run_cli(
        [
            "cve",
            "--target",
            "127.0.0.1",
            "--services-file",
            str(services),
            "--timeout",
            "1.0",
            "--no-cache",
            "--no-offline-fallback",
        ]
    )

    assert report["services_checked"] == 1
    assert "NVD lookup failed" in (report["error"] or "")
    assert "Failed to fetch CVE data" in (report["error"] or "")


def test_subtake_cli_reports_an_unresolvable_subdomain(monkeypatch, tmp_path: Path) -> None:
    """The subtake command reports an unresolved subdomain and exits 0."""
    wordlist = tmp_path / "subdomains.txt"
    wordlist.write_text("www\n")

    _hostile_transport(monkeypatch, "urllib.request.urlopen")
    _unresolvable_name(monkeypatch, "ethscan.subtake.socket.getaddrinfo")

    report = _run_cli(
        [
            "subtake",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist),
            "--timeout",
            "1.0",
        ]
    )

    assert report["subdomains_tested"] == 1
    assert report["vulnerable_count"] == 0
    assert report["vulnerable"] == []
    entry = report["all_results"][0]
    assert entry["subdomain"] == "www"
    assert entry["cname"] is None
    assert entry["a_records"] == []
    assert entry["vulnerable"] is False
    # A lookup that failed is a missing entry, not an error of its own.
    assert "error" not in entry
