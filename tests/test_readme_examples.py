"""Offline regression tests for the README console examples.

Every documented error example in README.md (lines 115-285) must keep
producing the same usage error (exit code 2) with the same Usage / Try /
Error text. Tests invoke through CliRunner, so no network, DNS, or
filesystem access beyond tmp_path is required. The CliRunner program name
is "cli", so the Usage/Try lines carry that name while the Error text
matches README.md exactly.

The ``s3 --target "[::1]:443`` example (README.md lines 247-258) is the one
documented example that reports an in-band probe failure (exit 0) instead of
a usage error: a valid host whose name cannot be an S3 bucket is still
reported as a failed probe inside its own output.
"""

import json

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


def test_readme_example_web_invalid_port() -> None:
    result = _invoke(["web", "--target", "host:notaport"])
    assert result.exit_code == 2
    assert "Usage: cli web [OPTIONS]" in result.output
    assert "Try 'cli web --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'"
        in result.output
    )


def test_readme_example_web_host_with_space() -> None:
    result = _invoke(["web", "--target", "host name"])
    assert result.exit_code == 2
    assert "Usage: cli web [OPTIONS]" in result.output
    assert "Try 'cli web --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target host contains a space or control character"
        in result.output
    )


def test_readme_example_web_path_with_space() -> None:
    result = _invoke(["web", "--target", "https://example.com/a b"])
    assert result.exit_code == 2
    assert "Usage: cli web [OPTIONS]" in result.output
    assert "Try 'cli web --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target path contains a space or control character"
        in result.output
    )


def test_readme_example_trace_empty_target() -> None:
    result = _invoke(["trace", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli trace [OPTIONS]" in result.output
    assert "Try 'cli trace --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_s3_empty_target() -> None:
    result = _invoke(["s3", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli s3 [OPTIONS]" in result.output
    assert "Try 'cli s3 --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_redis_empty_target() -> None:
    result = _invoke(["redis", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli redis [OPTIONS]" in result.output
    assert "Try 'cli redis --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_s3_invalid_bucket_name() -> None:
    result = _invoke(["s3", "--target", "[::1]:443"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target"] == "[::1]:443"
    assert data["domain"] == "::1"
    assert data["region"] == "us-east-1"
    assert data["candidates_tested"] == 77
    results = data["results"]
    assert isinstance(results, list) and len(results) == 77
    first = results[0]
    assert first["bucket"] == "::1"
    assert first["region"] == "us-east-1"
    assert first["url"] == "https://::1.s3.amazonaws.com/"
    assert first["dns_resolved"] is None
    assert first["status_code"] is None
    assert first["exists"] is False
    assert first["public"] is False
    assert (
        first["error"]
        == "Invalid bucket name: contains characters that are not allowed in a bucket name"
    )


def test_readme_example_headers_invalid_port() -> None:
    result = _invoke(["headers", "--target", "host:notaport"])
    assert result.exit_code == 2
    assert "Usage: cli headers [OPTIONS]" in result.output
    assert "Try 'cli headers --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'"
        in result.output
    )


def test_readme_example_urlcheck_invalid_port() -> None:
    result = _invoke(["urlcheck", "--target", "host:notaport"])
    assert result.exit_code == 2
    assert "Usage: cli urlcheck [OPTIONS]" in result.output
    assert "Try 'cli urlcheck --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'"
        in result.output
    )


def test_readme_example_ssh_invalid_port() -> None:
    result = _invoke(["ssh", "--target", "host:notaport"])
    assert result.exit_code == 2
    assert "Usage: cli ssh [OPTIONS]" in result.output
    assert "Try 'cli ssh --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'"
        in result.output
    )


def test_readme_example_fuzz_invalid_port() -> None:
    result = _invoke(["fuzz", "--target", "host:notaport"])
    assert result.exit_code == 2
    assert "Usage: cli fuzz [OPTIONS]" in result.output
    assert "Try 'cli fuzz --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Port could not be cast to integer value as 'notaport'"
        in result.output
    )


def test_readme_example_headers_host_with_space() -> None:
    result = _invoke(["headers", "--target", "host name"])
    assert result.exit_code == 2
    assert "Usage: cli headers [OPTIONS]" in result.output
    assert "Try 'cli headers --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target host contains a space or control character"
        in result.output
    )


def test_readme_example_urlcheck_host_with_space() -> None:
    result = _invoke(["urlcheck", "--target", "host name"])
    assert result.exit_code == 2
    assert "Usage: cli urlcheck [OPTIONS]" in result.output
    assert "Try 'cli urlcheck --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target host contains a space or control character"
        in result.output
    )


def test_readme_example_fuzz_host_with_space() -> None:
    result = _invoke(["fuzz", "--target", "host name"])
    assert result.exit_code == 2
    assert "Usage: cli fuzz [OPTIONS]" in result.output
    assert "Try 'cli fuzz --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target host contains a space or control character"
        in result.output
    )


def test_readme_example_s3_host_with_space() -> None:
    result = _invoke(["s3", "--target", "host name"])
    assert result.exit_code == 2
    assert "Usage: cli s3 [OPTIONS]" in result.output
    assert "Try 'cli s3 --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target host contains a space or control character"
        in result.output
    )


def test_readme_example_headers_path_with_space() -> None:
    result = _invoke(["headers", "--target", "https://example.com/a b"])
    assert result.exit_code == 2
    assert "Usage: cli headers [OPTIONS]" in result.output
    assert "Try 'cli headers --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target path contains a space or control character"
        in result.output
    )


def test_readme_example_urlcheck_path_with_space() -> None:
    result = _invoke(["urlcheck", "--target", "https://example.com/a b"])
    assert result.exit_code == 2
    assert "Usage: cli urlcheck [OPTIONS]" in result.output
    assert "Try 'cli urlcheck --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Target path contains a space or control character"
        in result.output
    )


def test_readme_example_recon_empty_target() -> None:
    result = _invoke(["recon", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli recon [OPTIONS]" in result.output
    assert "Try 'cli recon --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_geo_empty_target() -> None:
    result = _invoke(["geo", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli geo [OPTIONS]" in result.output
    assert "Try 'cli geo --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_mysql_empty_target() -> None:
    result = _invoke(["mysql", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli mysql [OPTIONS]" in result.output
    assert "Try 'cli mysql --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_mongodb_empty_target() -> None:
    result = _invoke(["mongodb", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli mongodb [OPTIONS]" in result.output
    assert "Try 'cli mongodb --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )


def test_readme_example_mssql_empty_target() -> None:
    result = _invoke(["mssql", "--target", ""])
    assert result.exit_code == 2
    assert "Usage: cli mssql [OPTIONS]" in result.output
    assert "Try 'cli mssql --help' for help." in result.output
    assert (
        "Error: Invalid value for '--target': Could not parse host from target ''"
        in result.output
    )
