"""Tests for the ethscan CLI."""

from click.testing import CliRunner

from ethscan.cli import cli


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help_lists_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "audit" in result.output
    assert "report" in result.output
    assert "web" in result.output


def test_web_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["web", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--checks" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_fuzz_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["fuzz", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_fuzz() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "fuzz" in result.output


def test_web_unknown_check() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["web", "--target", "https://example.com", "--checks", "bogus", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "Unknown checks" in result.output


def test_subdomains_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--wordlist" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_subdomains() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "subdomains" in result.output


def test_subdomains_offline_target_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["subdomains", "--target", "nonexistent.invalid.domain.tld", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "nonexistent.invalid.domain.tld" in result.output
    assert "resolved_count" in result.output


def test_subdomains_offline_target_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Subdomain Enumeration Report" in result.output


def test_subdomains_wordlist_option(tmp_path) -> None:
    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "www" in result.output
    assert "mail" in result.output


def test_subdomains_out_option(tmp_path) -> None:
    out_file = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "nonexistent.invalid.domain.tld",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "nonexistent.invalid.domain.tld" in content


def test_whois_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["whois", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--server" in result.output
    assert "--port" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_whois() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "whois" in result.output


def test_whois_offline_target_json(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "Registrar: Test Registrar\n",
            "parsed": {
                "registrar": "Test Registrar",
                "creation_date": "2020-01-01",
                "expiration_date": "2025-01-01",
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "Registrar: Test Registrar\n",
            },
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["whois", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "Test Registrar" in result.output


def test_whois_offline_target_markdown(monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "Registrar: Test Registrar\n",
            "parsed": {
                "registrar": "Test Registrar",
                "creation_date": "2020-01-01",
                "expiration_date": "2025-01-01",
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "Registrar: Test Registrar\n",
            },
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "WHOIS Lookup Report" in result.output


def test_whois_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0):
        called_args["server"] = server
        called_args["target"] = target
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "",
            },
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
            "--server",
            "whois.example.org",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["server"] == "whois.example.org"


def test_whois_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_whois(target, server="whois.iana.org", port=43, timeout=5.0):
        return {
            "target": target,
            "server": server,
            "port": port,
            "raw": "test",
            "parsed": {
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "nameservers": [],
                "registrant_org": None,
                "status_codes": [],
                "raw": "test",
            },
        }

    monkeypatch.setattr("ethscan.cli.run_whois", mock_run_whois)

    out_file = tmp_path / "whois_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "whois",
            "--target",
            "example.com",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "example.com" in content


def test_dns_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dns", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--types" in result.output
    assert "--server" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_dns() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "dns" in result.output


def test_dns_offline_target_json(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {
                "A": ["93.184.216.34"],
                "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
            },
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dns", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "93.184.216.34" in result.output


def test_dns_offline_target_markdown(monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {
                "A": ["93.184.216.34"],
                "AAAA": [],
            },
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "DNS Record Enumeration Report" in result.output


def test_dns_types_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        called_args["record_types"] = record_types
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--types",
            "A,MX,NS",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["record_types"] == ["A", "MX", "NS"]


def test_dns_unknown_type() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--types",
            "INVALID",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown record types" in result.output


def test_dns_server_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        called_args["server"] = server
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--server",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["server"] == "8.8.8.8"


def test_dns_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_dns(target, record_types=None, server=None, timeout=2.0):
        return {
            "target": target,
            "domain": "example.com",
            "record_types_queried": record_types or ["A", "AAAA"],
            "records": {"A": ["93.184.216.34"]},
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_dns", mock_run_dns)

    out_file = tmp_path / "dns_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dns",
            "--target",
            "example.com",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "example.com" in content


def test_ssl_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["ssl", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_ssl() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ssl" in result.output


def test_ssl_offline_target_json(monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["ssl", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "connection refused" in result.output


def test_ssl_offline_target_markdown(monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": None,
            "chain_length": 2,
            "cert": {
                "subject": "example.com",
                "issuer": "Let's Encrypt",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2030 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "SSL/TLS Certificate Report" in result.output


def test_ssl_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_ssl(target, port=443, timeout=5.0):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": "connection refused",
            "chain_length": 0,
            "cert": None,
            "valid": False,
            "days_remaining": None,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
            "--port",
            "8443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 8443


def test_ssl_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_ssl(target, port=443, timeout=5.0):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "error": None,
            "chain_length": 1,
            "cert": {
                "subject": "example.com",
                "issuer": "Test CA",
                "sans": ["example.com"],
                "not_before": "Jan  1 00:00:00 2020 GMT",
                "not_after": "Jan  1 00:00:00 2030 GMT",
                "signature_algorithm": "sha256WithRSAEncryption",
                "key_size": 2048,
            },
            "valid": True,
            "days_remaining": 3650,
        }

    monkeypatch.setattr("ethscan.cli.run_ssl", mock_run_ssl)

    out_file = tmp_path / "ssl_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "ssl",
            "--target",
            "example.com",
            "--out",
            str(out_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "example.com" in content
    assert "Test CA" in content