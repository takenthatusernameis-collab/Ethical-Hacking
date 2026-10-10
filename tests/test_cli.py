"""Tests for the ethscan CLI."""

import json

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


def test_subdomains_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_subdomains(
        target, subdomains=None, timeout=2.0, max_workers=50, resolver=None
    ):
        called_args["resolver"] = resolver
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "subdomains_tested": 2,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {"subdomain": "www", "hostname": "www.example.com", "ip": None},
                {"subdomain": "mail", "hostname": "mail.example.com", "ip": None},
            ],
            "resolver": resolver,
            "dnspython_available": False,
        }

    monkeypatch.setattr("ethscan.cli.run_subdomains", mock_run_subdomains)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "subdomains",
            "--target",
            "example.com",
            "--resolver",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_subdomains_help_shows_resolver() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["subdomains", "--help"])
    assert result.exit_code == 0
    assert "--resolver" in result.output


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


def test_brute_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["brute", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--protocol" in result.output
    assert "--port" in result.output
    assert "--user-file" in result.output
    assert "--pass-file" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_brute() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "brute" in result.output


def test_brute_offline_target_json(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 2,
            "attempts": 2,
            "successful_count": 1,
            "successful": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                }
            ],
            "results": [
                {
                    "username": "admin",
                    "password": "secret",
                    "success": True,
                    "error": None,
                },
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "530 Login incorrect",
                },
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["brute", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "admin" in result.output
    assert "secret" in result.output


def test_brute_offline_target_markdown(monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Brute Force Report" in result.output


def test_brute_protocol_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["protocol"] = protocol
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 22,
            "timeout": timeout,
            "usernames_tested": 0,
            "passwords_tested": 0,
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--protocol",
            "ssh",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["protocol"] == "ssh"


def test_brute_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": port,
            "timeout": timeout,
            "usernames_tested": 0,
            "passwords_tested": 0,
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--port",
            "2121",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 2121


def test_brute_wordlist_options(tmp_path, monkeypatch) -> None:
    user_file = tmp_path / "users.txt"
    user_file.write_text("admin\nroot\n")
    pass_file = tmp_path / "passwords.txt"
    pass_file.write_text("secret\npassword\n")

    called_args = {}

    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        called_args["usernames"] = usernames
        called_args["passwords"] = passwords
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": len(usernames or []),
            "passwords_tested": len(passwords or []),
            "attempts": 0,
            "successful_count": 0,
            "successful": [],
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
            "--target",
            "example.com",
            "--user-file",
            str(user_file),
            "--pass-file",
            str(pass_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["usernames"] == ["admin", "root"]
    assert called_args["passwords"] == ["secret", "password"]


def test_brute_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_brute(
        target,
        protocol="ftp",
        usernames=None,
        passwords=None,
        port=None,
        timeout=5.0,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "protocol": protocol,
            "port": 21,
            "timeout": timeout,
            "usernames_tested": 1,
            "passwords_tested": 1,
            "attempts": 1,
            "successful_count": 0,
            "successful": [],
            "results": [
                {
                    "username": "admin",
                    "password": "wrong",
                    "success": False,
                    "error": "connection refused",
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_brute", mock_run_brute)

    out_file = tmp_path / "brute_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "brute",
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
    assert "connection refused" in content


def test_service_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_service() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "service" in result.output


def test_service_offline_target_json(monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 3,
            "services_found": 2,
            "results": [
                {"port": 21, "banner": "220 FTP Server ready", "service": "FTP"},
                {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["service", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "FTP" in result.output
    assert "OpenSSH" in result.output


def test_service_offline_target_markdown(monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 2,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Service Detection Report" in result.output
    assert "*No services detected.*" in result.output


def test_service_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--ports",
            "21,22,80,443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 80, 443]


def test_service_ports_range_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--ports",
            "8000-8010",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == list(range(8000, 8011))


def test_service_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
            "--target",
            "example.com",
            "--workers",
            "100",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 100


def test_service_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_service(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": 2,
            "services_found": 1,
            "results": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9", "service": "OpenSSH"},
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    out_file = tmp_path / "service_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "service",
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
    assert "OpenSSH" in content


def test_scan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--profile" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "fast" in result.output
    assert "normal" in result.output
    assert "full" in result.output


def test_scan_profile_fast(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_scan_profile_normal(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "normal"])
    assert result.exit_code == 0
    assert called_args["ports"] == [20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]
    assert called_args["timeout"] == 1.0
    assert called_args["max_workers"] == 100


def test_scan_profile_full(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "full"])
    assert result.exit_code == 0
    assert len(called_args["ports"]) == 1024 + 24 - len(set(range(1, 1025)) & set([20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]))
    assert called_args["timeout"] == 2.0
    assert called_args["max_workers"] == 50


def test_scan_profile_override_ports(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast", "--ports", "80,443"])
    assert result.exit_code == 0
    assert called_args["ports"] == [80, 443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_scan_profile_override_timeout_workers(monkeypatch) -> None:
    called_args = {}

    def mock_scan_ports(host, ports, timeout=1.0, max_workers=100):
        called_args["host"] = host
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return [(p, False) for p in ports]

    monkeypatch.setattr("ethscan.cli.scan_ports", mock_scan_ports)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--target", "example.com", "--profile", "fast", "--timeout", "5.0", "--workers", "10"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 5.0
    assert called_args["max_workers"] == 10


def test_service_profile_fast(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_service_profile_normal(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "normal"])
    assert result.exit_code == 0
    assert called_args["ports"] == [20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]
    assert called_args["timeout"] == 1.0
    assert called_args["max_workers"] == 100


def test_service_profile_full(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "full"])
    assert result.exit_code == 0
    assert len(called_args["ports"]) == 1024 + 24 - len(set(range(1, 1025)) & set([20, 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 8888]))
    assert called_args["timeout"] == 2.0
    assert called_args["max_workers"] == 50


def test_service_profile_override_ports(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast", "--ports", "80,443"])
    assert result.exit_code == 0
    assert called_args["ports"] == [80, 443]
    assert called_args["timeout"] == 0.5
    assert called_args["max_workers"] == 200


def test_service_profile_override_timeout_workers(monkeypatch) -> None:
    called_args = {}

    def mock_run_service(target, ports=None, timeout=3.0, max_workers=50):
        called_args["target"] = target
        called_args["ports"] = ports
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_scanned": len(ports) if ports else 0,
            "services_found": 0,
            "results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_service", mock_run_service)

    runner = CliRunner()
    result = runner.invoke(cli, ["service", "--target", "example.com", "--profile", "fast", "--timeout", "5.0", "--workers", "10"])
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]
    assert called_args["timeout"] == 5.0
    assert called_args["max_workers"] == 10


def test_tls_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["tls", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--versions" in result.output
    assert "--ciphers" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_tls() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "tls" in result.output


def test_tls_offline_target_json(monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 2,
            "ciphers_tested": 2,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
                {
                    "version": "TLSv1",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_cipher": None,
                    "negotiated_protocol": None,
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
                {
                    "cipher": "AES128-SHA",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_version": None,
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tls", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "TLSv1_2" in result.output
    assert "AES128-GCM-SHA256" in result.output
    assert "supported_version_count" in result.output


def test_tls_offline_target_markdown(monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 2,
            "ciphers_tested": 2,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
                {
                    "version": "TLSv1",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_cipher": None,
                    "negotiated_protocol": None,
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
                {
                    "cipher": "AES128-SHA",
                    "supported": False,
                    "error": "handshake failure",
                    "negotiated_version": None,
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "TLS Enumeration Report" in result.output
    assert "TLSv1_2" in result.output
    assert "AES128-GCM-SHA256" in result.output


def test_tls_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
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


def test_tls_versions_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["versions"] = versions
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": len(versions or []),
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--versions",
            "TLSv1_2,TLSv1_3",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["versions"] == ["TLSv1_2", "TLSv1_3"]


def test_tls_ciphers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["ciphers"] = ciphers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": len(ciphers or []),
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--ciphers",
            "AES128-GCM-SHA256,AES256-GCM-SHA384",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ciphers"] == ["AES128-GCM-SHA256", "AES256-GCM-SHA384"]


def test_tls_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 0,
            "ciphers_tested": 0,
            "versions": [],
            "ciphers": [],
            "supported_versions": [],
            "supported_ciphers": [],
            "supported_version_count": 0,
            "supported_cipher_count": 0,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--workers",
            "25",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 25


def test_tls_unknown_version() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
            "--target",
            "example.com",
            "--versions",
            "BOGUS",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown TLS versions" in result.output
    assert "BOGUS" in result.output


def test_tls_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_tls(
        target,
        port=443,
        timeout=5.0,
        versions=None,
        ciphers=None,
        max_workers=10,
    ):
        return {
            "target": target,
            "host": "example.com",
            "port": port,
            "timeout": timeout,
            "versions_tested": 1,
            "ciphers_tested": 1,
            "versions": [
                {
                    "version": "TLSv1_2",
                    "supported": True,
                    "error": None,
                    "negotiated_cipher": "AES128-GCM-SHA256",
                    "negotiated_protocol": "TLSv1.2",
                },
            ],
            "ciphers": [
                {
                    "cipher": "AES128-GCM-SHA256",
                    "supported": True,
                    "error": None,
                    "negotiated_version": "TLSv1.2",
                },
            ],
            "supported_versions": ["TLSv1_2"],
            "supported_ciphers": ["AES128-GCM-SHA256"],
            "supported_version_count": 1,
            "supported_cipher_count": 1,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_tls", mock_run_tls)

    out_file = tmp_path / "tls_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "tls",
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
    assert "TLSv1_2" in content
    assert "AES128-GCM-SHA256" in content


def test_vuln_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["vuln", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--services-file" in result.output
    assert "--tls-file" in result.output
    assert "--ssl-file" in result.output
    assert "--severity" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_vuln() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "vuln" in result.output


def test_vuln_offline_target_json(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["vuln", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "CVE-2018-15473" in result.output
    assert "finding_count" in result.output


def test_vuln_offline_target_markdown(monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": True,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [
                {
                    "id": "CVE-2014-3566",
                    "kind": "protocol",
                    "title": "SSLv3 is vulnerable to POODLE",
                    "severity": "high",
                    "description": "SSLv3 supports CBC-mode ciphers.",
                    "protocol": "SSLv3",
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Vulnerability Report" in result.output
    assert "CVE-2014-3566" in result.output
    assert "SSLv3" in result.output


def test_vuln_services_file_option(tmp_path) -> None:
    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "results": [
                    {
                        "port": 21,
                        "banner": "220 ProFTPD 1.3.5 Server (Debian)",
                        "service": "ProFTPD",
                    },
                ],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--services-file",
            str(services_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "CVE-2015-3306" in result.output
    assert "ProFTPD" in result.output


def test_vuln_tls_file_option(tmp_path) -> None:
    tls_file = tmp_path / "tls_report.json"
    tls_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "supported_versions": ["SSLv3", "TLSv1_2"],
                "supported_ciphers": ["RC4-SHA", "AES128-GCM-SHA256"],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--tls-file",
            str(tls_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "CVE-2014-3566" in result.output
    assert "CVE-2013-2566" in result.output


def test_vuln_ssl_file_option(tmp_path) -> None:
    ssl_file = tmp_path / "ssl_report.json"
    ssl_file.write_text(
        json.dumps(
            {
                "target": "example.com",
                "host": "example.com",
                "cert": {
                    "key_size": 1024,
                    "signature_algorithm": "sha256WithRSAEncryption",
                },
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--ssl-file",
            str(ssl_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "WEAK-RSA-KEY" in result.output


def test_vuln_severity_option(tmp_path) -> None:
    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "results": [
                    {"port": 21, "banner": "220 (vsFTPd 2.3.4)"},
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_7.2p2"},
                ],
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--services-file",
            str(services_file),
            "--severity",
            "critical",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "VSFTPD-2.3.4-BACKDOOR" in result.output
    assert "CVE-2018-15473" not in result.output


def test_vuln_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--ports",
            "21,22,80",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [21, 22, 80]


def test_vuln_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 0,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [],
            "finding_count": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--workers",
            "25",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_workers"] == 25


def test_vuln_out_option(tmp_path, monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    out_file = tmp_path / "vuln_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
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
    assert "CVE-2018-15473" in content


def test_vuln_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_vuln(
        target,
        ports=None,
        timeout=3.0,
        max_workers=50,
        services=None,
        tls=None,
        certificate=None,
        severity=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports": ports,
            "services_checked": 1,
            "tls_checked": False,
            "certificate_checked": False,
            "severity_filter": severity,
            "findings": [
                {
                    "id": "CVE-2018-15473",
                    "kind": "service",
                    "title": "OpenSSH user enumeration via malformed userauth request",
                    "severity": "medium",
                    "description": "OpenSSH before 7.7 allows user enumeration.",
                    "product": "OpenSSH",
                    "version": "7.2p2",
                    "port": 22,
                }
            ],
            "finding_count": 1,
            "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 0},
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_vuln", mock_run_vuln)

    out_file = tmp_path / "vuln_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "vuln",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "Vulnerability Report" in content
    assert "CVE-2018-15473" in content


def test_dnsbrute_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ns" in result.output
    assert "--wordlist" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_dnsbrute() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "dnsbrute" in result.output


def test_dnsbrute_offline_target_json(monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [
                {
                    "nameserver": "ns1.example.com",
                    "success": False,
                    "records_count": 0,
                    "records": [],
                    "error": "transfer refused (REFUSED)",
                }
            ],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 1,
            "resolved": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["dnsbrute", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "93.184.216.34" in result.output


def test_dnsbrute_offline_target_markdown(monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [
                {
                    "nameserver": "ns1.example.com",
                    "success": False,
                    "records_count": 0,
                    "records": [],
                    "error": "transfer refused (REFUSED)",
                }
            ],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "DNS Brute Force Report" in result.output


def test_dnsbrute_ns_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        called_args["nameservers"] = nameservers
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": nameservers or [],
            "nameserver_source": "option" if nameservers else "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 0,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--ns",
            "ns1.example.com,ns2.example.com",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["nameservers"] == ["ns1.example.com", "ns2.example.com"]


def test_dnsbrute_wordlist_option(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        called_args["subdomains"] = subdomains
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": len(subdomains or []),
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    wordlist_file = tmp_path / "subs.txt"
    wordlist_file.write_text("www\nmail\n")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["subdomains"] == ["www", "mail"]


def test_dnsbrute_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 0,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "10",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["max_workers"] == 10


def test_dnsbrute_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": ["ns1.example.com"],
            "nameserver_source": "option",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 1,
            "resolved": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": ["93.184.216.34"],
                    "aaaa": [],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    out_file = tmp_path / "dnsbrute_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
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
    assert "93.184.216.34" in content


def test_dnsbrute_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    out_file = tmp_path / "dnsbrute_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "DNS Brute Force Report" in content


def test_dnsbrute_resolver_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_dnsbrute(
        target,
        nameservers=None,
        subdomains=None,
        timeout=2.0,
        max_workers=50,
        resolver=None,
    ):
        called_args["resolver"] = resolver
        called_args["target"] = target
        return {
            "target": target,
            "domain": "example.com",
            "zone": "example.com",
            "nameservers": [],
            "nameserver_source": "none",
            "dnspython_available": False,
            "axfr": [],
            "axfr_success": False,
            "axfr_total_records": 0,
            "subdomains_tested": 1,
            "resolved_count": 0,
            "resolved": [],
            "all_results": [
                {
                    "subdomain": "www",
                    "hostname": "www.example.com",
                    "a": [],
                    "aaaa": [],
                }
            ],
            "resolver": resolver,
        }

    monkeypatch.setattr("ethscan.cli.run_dnsbrute", mock_run_dnsbrute)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "dnsbrute",
            "--target",
            "example.com",
            "--resolver",
            "8.8.8.8",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["resolver"] == "8.8.8.8"


def test_dnsbrute_help_shows_resolver() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["dnsbrute", "--help"])
    assert result.exit_code == 0
    assert "--resolver" in result.output


def test_urlcheck_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["urlcheck", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--checks" in result.output
    assert "--wordlist" in result.output
    assert "--fuzz-paths" in result.output
    assert "--port" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_urlcheck() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "urlcheck" in result.output


def test_urlcheck_offline_target_json(monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": ["Content-Security-Policy"],
                    "missing": ["X-Frame-Options"],
                    "total": 7,
                    "present_count": 1,
                    "missing_count": 6,
                },
                "information_disclosure": [],
                "ssl": {"valid": True, "subject": "example.com", "issuer": "Let's Encrypt", "not_after": "Jan  1 00:00:00 2027 GMT", "days_remaining": 100},
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": 2,
                "findings": [{"path": "/admin", "status_code": 200, "error": None}],
                "all_results": [
                    {"path": "/admin", "status_code": 200, "error": None},
                    {"path": "/login", "status_code": 404, "error": None},
                ],
            },
            "ssl": {
                "target": "example.com",
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
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 7,
                "web_checks_run": ["headers", "info_disclosure", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["urlcheck", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "Content-Security-Policy" in result.output
    assert "admin" in result.output


def test_urlcheck_offline_target_markdown(monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "info_disclosure", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": [],
                    "missing": ["Content-Security-Policy"],
                    "total": 7,
                    "present_count": 0,
                    "missing_count": 7,
                },
                "information_disclosure": [],
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": 1,
                "findings": [],
                "all_results": [{"path": "/admin", "status_code": 404, "error": None}],
            },
            "ssl": {
                "target": "example.com",
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
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 8,
                "web_checks_run": ["headers", "info_disclosure", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Consolidated Web Assessment Report" in result.output
    assert "example.com" in result.output


def test_urlcheck_checks_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["checks"] = checks
        called_args["target"] = target
        called_args["fuzz_paths"] = fuzz_paths
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {
                    "present": [],
                    "missing": [],
                    "total": 7,
                    "present_count": 0,
                    "missing_count": 7,
                },
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--checks",
            "headers,ssl",
            "--no-fuzz-paths",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["checks"] == ["headers", "ssl"]
    assert called_args["fuzz_paths"] is False


def test_urlcheck_unknown_check() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "https://example.com",
            "--checks",
            "bogus",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "Unknown checks" in result.output


def test_urlcheck_wordlist_option(tmp_path, monkeypatch) -> None:
    wordlist_file = tmp_path / "paths.txt"
    wordlist_file.write_text("/admin\n/login\n")
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["wordlist"] = wordlist
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": {
                "target": target,
                "base_url": "https://example.com",
                "paths_tested": len(wordlist or []),
                "findings": [],
                "all_results": [],
            },
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--wordlist",
            str(wordlist_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["wordlist"] == ["/admin", "/login"]


def test_urlcheck_no_fuzz_paths_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["fuzz_paths"] = fuzz_paths
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--no-fuzz-paths",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["fuzz_paths"] is False


def test_urlcheck_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
                "ssl": {"valid": False, "error": "connection refused"},
            },
            "fuzz": None,
            "ssl": {
                "target": "example.com",
                "host": "example.com",
                "port": port,
                "timeout": timeout,
                "error": "connection refused",
                "chain_length": 0,
                "cert": None,
                "valid": False,
                "days_remaining": None,
            },
            "summary": {
                "total_findings": 1,
                "web_checks_run": ["headers", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
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


def test_urlcheck_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        called_args["timeout"] = timeout
        called_args["workers"] = workers
        called_args["target"] = target
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": checks or ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "25",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["workers"] == 25


def test_urlcheck_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers", "ssl"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": {
                "target": "example.com",
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
                    "not_after": "Jan  1 00:00:00 2027 GMT",
                    "signature_algorithm": "sha256WithRSAEncryption",
                    "key_size": 2048,
                },
                "valid": True,
                "days_remaining": 3650,
            },
            "summary": {
                "total_findings": 0,
                "web_checks_run": ["headers", "ssl"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": True,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    out_file = tmp_path / "urlcheck_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
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


def test_urlcheck_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_urlcheck(
        target,
        checks=None,
        wordlist=None,
        fuzz_paths=True,
        port=443,
        timeout=5.0,
        workers=10,
    ):
        return {
            "target": target,
            "normalized_target": "https://example.com",
            "checks_requested": checks or ["headers"],
            "fuzz_enabled": fuzz_paths,
            "port": port,
            "timeout": timeout,
            "workers": workers,
            "web": {
                "target": target,
                "host": "example.com",
                "port": port,
                "secure": True,
                "security_headers": {"present": [], "missing": [], "total": 7, "present_count": 0, "missing_count": 7},
                "information_disclosure": [],
            },
            "fuzz": None,
            "ssl": None,
            "summary": {
                "total_findings": 0,
                "web_checks_run": ["headers"],
                "fuzz_enabled": fuzz_paths,
                "ssl_checked": False,
            },
        }

    monkeypatch.setattr("ethscan.cli.run_urlcheck", mock_run_urlcheck)

    out_file = tmp_path / "urlcheck_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "urlcheck",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "Consolidated Web Assessment Report" in content


def test_osdetect_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["osdetect", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--ports" in result.output
    assert "--banners-file" in result.output
    assert "--timeout" in result.output
    assert "--workers" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_osdetect() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "osdetect" in result.output


def test_osdetect_offline_target_json(monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        port_list = ports or [22, 80, 443]
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(port_list),
            "probes": [
                {
                    "port": port,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
                for port in port_list
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": bool(banners),
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["osdetect", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "inferred_os" in result.output


def test_osdetect_offline_target_markdown(monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        port_list = ports or [22, 80, 443]
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(port_list),
            "probes": [
                {
                    "port": port,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
                for port in port_list
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": bool(banners),
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "OS Detection Report" in result.output


def test_osdetect_ports_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["ports"] = ports
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or []),
            "probes": [],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--ports",
            "22,80,443",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["ports"] == [22, 80, 443]


def test_osdetect_banners_file_option(tmp_path, monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["banners"] = banners
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [],
            "inferred_os": ["Linux"],
            "inferred_os_count": 1,
            "banners_provided": bool(banners),
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    services_file = tmp_path / "service_report.json"
    services_file.write_text(
        json.dumps(
            {
                "results": [
                    {"port": 22, "banner": "SSH-2.0-OpenSSH_8.9 Linux"},
                ]
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--banners-file",
            str(services_file),
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["banners"] == {22: "SSH-2.0-OpenSSH_8.9 Linux"}


def test_osdetect_timeout_workers_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        called_args["timeout"] = timeout
        called_args["max_workers"] = max_workers
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--timeout",
            "3.5",
            "--workers",
            "25",
        ],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 3.5
    assert called_args["max_workers"] == 25


def test_osdetect_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [
                {
                    "port": 22,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    out_file = tmp_path / "osdetect_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
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
    assert "inferred_os" in content


def test_osdetect_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_osdetect(
        target,
        ports=None,
        timeout=5.0,
        max_workers=10,
        banners=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "timeout": timeout,
            "ports_probed": len(ports or [22, 80, 443]),
            "probes": [
                {
                    "port": 22,
                    "probe_type": "SYN",
                    "connected": False,
                    "response": "NO-RESPONSE",
                    "flags_observed": None,
                    "error": None,
                }
            ],
            "inferred_os": [],
            "inferred_os_count": 0,
            "banners_provided": False,
            "notes": ["No open ports responded to SYN probes"],
        }

    monkeypatch.setattr("ethscan.cli.run_osdetect", mock_run_osdetect)

    out_file = tmp_path / "osdetect_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "osdetect",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "OS Detection Report" in content


# ---------------------------------------------------------------------------
# trace (TCP traceroute) CLI tests
# ---------------------------------------------------------------------------


def test_trace_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["trace", "--help"])
    assert result.exit_code == 0
    assert "--target" in result.output
    assert "--port" in result.output
    assert "--max-hops" in result.output
    assert "--probes-per-hop" in result.output
    assert "--timeout" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_trace() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "trace" in result.output


def test_trace_offline_target_json(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {
                    "hop": 1,
                    "ttl": 1,
                    "ip": None,
                    "host": "*",
                    "response_type": "NO-RESPONSE",
                    "rtt_ms": 0.5,
                    "rtt_avg_ms": 0.5,
                    "probes": [
                        {
                            "hop": 1, "ttl": 1, "ip": None, "host": "*",
                            "response_type": "NO-RESPONSE",
                            "rtt_ms": 0.5, "reached_destination": False,
                            "error_code": None,
                        }
                    ],
                    "reached_destination": False,
                    "error_code": None,
                }
            ],
            "hop_count": 1,
            "destination_reached": False,
            "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert "example.com" in result.output
    assert "hops" in result.output  # JSON contains hops field
    parsed = json.loads(result.output)
    assert parsed["target"] == "example.com"


def test_trace_offline_target_markdown(monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "93.184.216.34",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [
                {
                    "hop": 1,
                    "ttl": 1,
                    "ip": None,
                    "host": "*",
                    "response_type": "NO-RESPONSE",
                    "rtt_ms": 0.5,
                    "rtt_avg_ms": 0.5,
                    "probes": [
                        {
                            "hop": 1, "ttl": 1, "ip": None, "host": "*",
                            "response_type": "NO-RESPONSE",
                            "rtt_ms": 0.5, "reached_destination": False,
                            "error_code": None,
                        }
                    ],
                    "reached_destination": False,
                    "error_code": None,
                }
            ],
            "hop_count": 1,
            "destination_reached": False,
            "notes": ["Raw ICMP socket unavailable; connect-only fallback mode"],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--format",
            "markdown",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert "TCP Traceroute Report" in result.output
    assert "Hop Table" in result.output


def test_trace_port_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        called_args["port"] = port
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--port", "443", "--timeout", "1.0"],
    )
    assert result.exit_code == 0
    assert called_args["port"] == 443


def test_trace_max_hops_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        called_args["max_hops"] = max_hops
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--max-hops",
            "10",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["max_hops"] == 10


def test_trace_probes_per_hop_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        called_args["probes_per_hop"] = probes_per_hop
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--probes-per-hop",
            "5",
            "--timeout",
            "1.0",
        ],
    )
    assert result.exit_code == 0
    assert called_args["probes_per_hop"] == 5


def test_trace_timeout_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        called_args["timeout"] = timeout
        called_args["target"] = target
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["trace", "--target", "example.com", "--timeout", "5.0"],
    )
    assert result.exit_code == 0
    assert called_args["timeout"] == 5.0


def test_trace_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    out_file = tmp_path / "trace_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
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
    assert "TCP Traceroute Report" not in content  # JSON, not markdown
    parsed = json.loads(content)
    assert parsed["target"] == "example.com"


def test_trace_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_trace(
        target,
        port=80,
        max_hops=30,
        timeout=3.0,
        probes_per_hop=3,
        raw_socket=None,
    ):
        return {
            "target": target,
            "host": "example.com",
            "ip": "10.0.0.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "raw_socket_available": False,
            "hops": [],
            "hop_count": 0,
            "destination_reached": False,
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_trace", mock_run_trace)

    out_file = tmp_path / "trace_report.md"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trace",
            "--target",
            "example.com",
            "--format",
            "markdown",
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
    assert "TCP Traceroute Report" in content


def test_wifi_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--help"])
    assert result.exit_code == 0
    assert "--interface" in result.output
    assert "--format" in result.output
    assert "--out" in result.output
    assert "json" in result.output
    assert "markdown" in result.output


def test_cli_help_lists_wifi() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "wifi" in result.output


def test_wifi_offline_json(monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [
                {"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}
            ],
            "access_points": [
                {"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "TestNetwork", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}
            ],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi"])
    assert result.exit_code == 0
    assert "TestNetwork" in result.output
    assert "wlan0" in result.output


def test_wifi_offline_markdown(monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [
                {"interface": "wlan0", "status": 0, "link_quality": 45.0, "signal_level": -45.0, "noise_level": -256.0}
            ],
            "access_points": [
                {"interface": "wlan0", "bssid": "00:11:22:33:44:55", "ssid": "TestNetwork", "channel": 1, "frequency": 2.412, "encryption": "wpa2", "signal_dbm": -65, "quality": "45/70"}
            ],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Wi-Fi Reconnaissance Report" in result.output
    assert "TestNetwork" in result.output


def test_wifi_interface_option(monkeypatch) -> None:
    called_args = {}

    def mock_run_wifi(interface=None):
        called_args["interface"] = interface
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--interface", "wlan1"])
    assert result.exit_code == 0
    assert called_args["interface"] == "wlan1"


def test_wifi_out_option_json(tmp_path, monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    out_file = tmp_path / "wifi_report.json"
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "platform" in content
    assert "Linux" in content
    parsed = json.loads(content)
    assert parsed["platform"] == "Linux"


def test_wifi_out_option_markdown(tmp_path, monkeypatch) -> None:
    def mock_run_wifi(interface=None):
        return {
            "platform": "Linux",
            "platform_supported": True,
            "interfaces": [],
            "access_points": [],
            "notes": [],
        }

    monkeypatch.setattr("ethscan.cli.run_wifi", mock_run_wifi)

    out_file = tmp_path / "wifi_report.md"
    runner = CliRunner()
    result = runner.invoke(cli, ["wifi", "--format", "markdown", "--out", str(out_file)])
    assert result.exit_code == 0
    assert "Report written" in result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "Wi-Fi Reconnaissance Report" in content