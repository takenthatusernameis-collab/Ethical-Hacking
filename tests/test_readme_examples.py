"""Offline regression tests for the README console examples.

Every documented error example in README.md (lines 115-285) must keep
producing the same usage error (exit code 2) with the same Usage / Try /
Error text. Tests invoke through CliRunner, so no network, DNS, or
filesystem access beyond tmp_path is required. The CliRunner program name
is "cli", so the Usage/Try lines carry that name while the Error text
matches README.md exactly.
"""

from click.testing import CliRunner

from ethscan.cli import cli


def _invoke(args: list[str]):
    return CliRunner().invoke(cli, args)


def test_readme_example_scan_invalid_ports() -> None:
    result = _invoke(["scan", "--target", "127.0.0.1", "--ports", "abc"])
    assert result.exit_code == 2
    assert "Usage: cli scan [OPTIONS]" in result.output
    assert "Try 'cli scan --help' for help." in result.output
    assert (
        "Error: Invalid value for '--ports': Invalid port number 'abc'"
        in result.output
    )


def test_readme_example_cidr_invalid_cidr() -> None:
    result = _invoke(["cidr", "--cidr", "bogus"])
    assert result.exit_code == 2
    assert "Usage: cli cidr [OPTIONS]" in result.output
    assert "Try 'cli cidr --help' for help." in result.output
    assert (
        "Error: Invalid value for '--cidr': 'bogus/128' does not appear to be an IPv4 or IPv6 network"
        in result.output
    )


def test_readme_example_radix_mixed_address_families() -> None:
    result = _invoke(["radix", "--cidrs", "192.168.1.0/24,2001:db8::/32"])
    assert result.exit_code == 2
    assert "Usage: cli radix [OPTIONS]" in result.output
    assert "Try 'cli radix --help' for help." in result.output
    assert (
        "Error: Invalid value for '--cidrs': Cannot mix IPv4 and IPv6 networks in a single radix tree"
        in result.output
    )


def test_readme_example_vuln_broken_services_file(tmp_path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("not json{", encoding="utf-8")
    result = _invoke(["vuln", "--target", "example.com", "--services-file", str(broken)])
    assert result.exit_code == 2
    assert "Usage: cli vuln [OPTIONS]" in result.output
    assert "Try 'cli vuln --help' for help." in result.output
    assert (
        "Error: Invalid value for '--services-file': Expecting value: line 1 column 1 (char 0)"
        in result.output
    )


def test_readme_example_redis_port_out_of_range() -> None:
    result = _invoke(["redis", "--target", "example.com:99999"])
    assert result.exit_code == 2
    assert "Usage: cli redis [OPTIONS]" in result.output
    assert "Try 'cli redis --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port out of range 0-65535"
        in result.output
    )


def test_readme_example_audit_non_utf8_file(tmp_path) -> None:
    passwords = tmp_path / "passwords.txt"
    passwords.write_bytes(b"bad\xffbyte")
    result = _invoke(["audit", "--file", str(passwords)])
    assert result.exit_code == 2
    assert "Usage: cli audit [OPTIONS]" in result.output
    assert "Try 'cli audit --help' for help." in result.output
    assert (
        "Error: Invalid value for '--file': the file is not valid UTF-8"
        in result.output
    )
