"""Focused coverage tests for remaining defensive/edge branches in ethscan.cli."""

from __future__ import annotations

import runpy
import sys
from typing import Any

import click
import pytest
from click.testing import CliRunner

import ethscan.cli as cli_mod
from ethscan.cli import (
    _CheckedDefaultMap,
    _check_config_path,
    _validate_api_url,
    _validate_dns_resolver,
    _validate_s3_region,
    _validate_whois_server,
    cli,
)


def test_checked_default_map_getitem_missing_and_present() -> None:
    checked = _CheckedDefaultMap(cli, "scan", {"workers": 1})
    with pytest.raises(KeyError):
        _ = checked["missing"]
    assert checked["workers"] == 1


def test_validate_s3_region_none_and_blank_return_none() -> None:
    assert _validate_s3_region(None) is None
    assert _validate_s3_region("   ") is None


def test_validate_dns_resolver_none_blank_https_and_invalid() -> None:
    assert _validate_dns_resolver(None, "--resolver") is None
    assert _validate_dns_resolver("   ", "--resolver") is None
    assert _validate_dns_resolver("https://dns.example/dns-query", "--resolver") == "https://dns.example/dns-query"
    with pytest.raises(click.UsageError, match="not a valid IP address or https:// resolver URL"):
        _validate_dns_resolver("not-an-ip", "--resolver")


def test_validate_api_url_none_and_blank_return_none() -> None:
    assert _validate_api_url(None, "--api-url") is None
    assert _validate_api_url("   ", "--api-url") is None


def test_validate_whois_server_accepts_ip_and_rejects_empty_label() -> None:
    assert _validate_whois_server("203.0.113.5", "--server") == "203.0.113.5"
    with pytest.raises(click.UsageError, match="not a valid WHOIS server hostname or IP address"):
        _validate_whois_server("bad..name", "--server")


def test_check_config_path_unreadable_file(tmp_path) -> None:
    unreadable = tmp_path / "unreadable.yaml"
    unreadable.write_text("defaults: {}\n")
    unreadable.chmod(0o000)
    try:
        with pytest.raises(click.BadParameter, match="the config file is not readable"):
            _check_config_path(str(unreadable))
    finally:
        unreadable.chmod(0o600)


def test_radix_cidr_file_oserror_is_bad_parameter(monkeypatch, tmp_path) -> None:
    cidr_file = tmp_path / "cidrs.txt"
    cidr_file.write_text("10.0.0.0/24\n")

    def boom(_path: str) -> list[str]:
        raise OSError("permission denied")

    monkeypatch.setattr(cli_mod.ethscan.fileio, "read_lines", boom)
    runner = CliRunner()
    result = runner.invoke(cli, ["radix", "--cidr-file", str(cidr_file)])
    assert result.exit_code == 2
    assert "Error: Invalid value for '--cidr-file':" in result.output
    assert "cannot be read" in result.output


def _probe_fallback_case(monkeypatch, command: str, probes_opt: str, run_attr: str, fmt_attr: str) -> None:
    captured: dict[str, Any] = {}

    def fake_run(target: str, **kwargs: Any) -> dict[str, object]:
        captured.update(kwargs)
        return {"target": target}

    monkeypatch.setattr(cli_mod, run_attr, fake_run)
    monkeypatch.setattr(cli_mod, fmt_attr, lambda _r: "{}")
    runner = CliRunner()
    result = runner.invoke(cli, [command, "--target", "127.0.0.1", probes_opt, " , "])
    assert result.exit_code == 0, result.output
    assert captured.get("probes")


@pytest.mark.parametrize(
    ("command", "probes_opt", "run_attr", "fmt_attr"),
    [
        ("memcached", "--probes", "run_memcached", "format_memcached_report_json"),
        ("redis", "--probes", "run_redis", "format_redis_report_json"),
        ("mssql", "--probes", "run_mssql", "format_mssql_report_json"),
        ("oracle", "--probes", "run_oracle", "format_oracle_report_json"),
    ],
)
def test_empty_probe_tokens_fall_back_to_defaults(
    monkeypatch, command: str, probes_opt: str, run_attr: str, fmt_attr: str
) -> None:
    _probe_fallback_case(monkeypatch, command, probes_opt, run_attr, fmt_attr)


def test_nmap_oserror_is_bad_parameter(monkeypatch, tmp_path) -> None:
    infile = tmp_path / "scan.xml"
    infile.write_text("<nmaprun></nmaprun>")

    def boom(_path: str) -> dict[str, object]:
        raise OSError("denied")

    monkeypatch.setattr(cli_mod, "run_nmap", boom)
    runner = CliRunner()
    result = runner.invoke(cli, ["nmap", "--input-file", str(infile)])
    assert result.exit_code == 2
    assert "Error: Invalid value for '--input-file':" in result.output
    assert "cannot be read" in result.output


def test_stale_target_file_oserror_is_bad_parameter(monkeypatch, tmp_path) -> None:
    infile = tmp_path / "targets.txt"
    infile.write_text("example.com\n")

    def boom(_path: str) -> list[str]:
        raise OSError("denied")

    monkeypatch.setattr(cli_mod.ethscan.stale, "load_domains_from_file", boom)
    runner = CliRunner()
    result = runner.invoke(cli, ["stale", "--file", str(infile)])
    assert result.exit_code == 2
    assert "Error: Invalid value for '--file':" in result.output
    assert "cannot be read" in result.output


def test_version_command_json_and_out(tmp_path) -> None:
    """Cover version JSON rendering and --out path (including json import branch)."""
    out = tmp_path / "version.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["version", "--output-format", "json", "--out", str(out)])
    assert result.exit_code == 0, result.output
    content = out.read_text()
    assert content.startswith("{")
    assert '"dependencies"' in content
    assert '"config_file"' in content
    assert "Report written to" in result.output


def test_version_dependency_attribute_errors(monkeypatch) -> None:
    """Cover dependency version fallbacks when modules lack __version__."""
    import types

    bad_click = types.ModuleType("click")
    bad_yaml = types.ModuleType("yaml")
    bad_dns = types.ModuleType("dns")
    monkeypatch.setitem(sys.modules, "click", bad_click)
    monkeypatch.setitem(sys.modules, "yaml", bad_yaml)
    monkeypatch.setitem(sys.modules, "dns", bad_dns)

    runner = CliRunner()
    result = runner.invoke(cli, ["version", "--output-format", "json"])
    assert result.exit_code == 0, result.output
    assert '"click": "unknown"' in result.output
    assert '"pyyaml": "unknown"' in result.output
    assert '"dnspython": "not installed"' in result.output


def test_cli_main_guard_executes() -> None:
    # Execute module as __main__ to cover the guard; invoke version to exit quickly.
    old_argv = sys.argv
    try:
        sys.argv = ["ethscan.cli", "version", "--output-format", "json"]
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("ethscan.cli", run_name="__main__", alter_sys=True)
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv


@pytest.mark.parametrize(
    ("command", "probes_opt", "run_attr", "fmt_attr"),
    [
        ("mysql", "--probes", "run_mysql", "format_mysql_report_json"),
        ("mongodb", "--probes", "run_mongodb", "format_mongodb_report_json"),
        ("postgresql", "--probes", "run_postgresql", "format_postgresql_report_json"),
    ],
)
def test_empty_probe_tokens_fall_back_to_defaults_db(
    monkeypatch, command: str, probes_opt: str, run_attr: str, fmt_attr: str
) -> None:
    _probe_fallback_case(monkeypatch, command, probes_opt, run_attr, fmt_attr)
