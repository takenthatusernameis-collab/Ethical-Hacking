"""CLI tests for trace command."""
import pytest
from click.testing import CliRunner

from ethscan import cli

# The targets that do not contain a usable host.
UNUSABLE_TARGETS = (
    "",
    "   ",
    "http://",
    "https://",
    "/",
)

TARGET_ERROR_MESSAGE = "Invalid target"


def _assert_target_usage_error(result, command: str) -> None:
    """Assert that ``result`` is a clean click usage error for --target."""
    assert result.exit_code == 2, (
        f"{command}: expected exit code 2, got {result.exit_code}\n{result.output}"
    )
    assert "Error: Invalid value for '--target':" in result.output, (
        f"{command}: missing usage error message\n{result.output}"
    )
    assert "Traceback (most recent call last)" not in result.output, (
        f"{command}: leaked a traceback\n{result.output}"
    )
    assert not isinstance(result.exception, ValueError), (
        f"{command}: leaked {result.exception!r} instead of a usage error"
    )


def test_trace_help():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["trace", "--help"])
    assert result.exit_code == 0
    assert "target" in result.output
    assert "max-hops" in result.output or "max_hops" in result.output


def test_trace_help_lists_options():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["trace", "--help"])
    assert result.exit_code == 0
    assert "--max-hops" in result.output
    assert "--probes-per-hop" in result.output
    assert "--port" in result.output


def test_trace_runs_json(monkeypatch):
    runner = CliRunner()

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [{"hop": 1, "ip": "1.1.1.1", "rtt_ms": 5.0, "reached": True}],
            "reached": True,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    result = runner.invoke(cli.cli, ["trace", "--target", "example.com"])
    assert result.exit_code == 0
    assert '"target": "example.com"' in result.output


def test_trace_runs_markdown(monkeypatch):
    runner = CliRunner()

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [],
            "reached": False,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    result = runner.invoke(cli.cli, ["trace", "--target", "example.com", "--format", "markdown"])
    assert result.exit_code == 0
    assert "TCP Traceroute Report" in result.output


def test_trace_runs_csv(monkeypatch):
    runner = CliRunner()

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [{"hop": 1, "ip": "1.1.1.1", "rtt_ms": 5.0, "reached": True}],
            "reached": True,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    result = runner.invoke(cli.cli, ["trace", "--target", "example.com", "--output-format", "csv"])
    assert result.exit_code == 0
    assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in result.output
    assert "example.com,1,1.1.1.1" in result.output


def test_trace_format_csv_alias(monkeypatch):
    runner = CliRunner()

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [],
            "reached": False,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    result = runner.invoke(cli.cli, ["trace", "--target", "example.com", "--format", "csv"])
    assert result.exit_code == 0
    assert "target,hop,ip,host,response_type,rtt_ms,reached_destination" in result.output


def test_trace_output_format_default_is_json(monkeypatch):
    runner = CliRunner()

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [],
            "reached": False,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    result = runner.invoke(cli.cli, ["trace", "--target", "example.com"])
    assert result.exit_code == 0
    assert '"target": "example.com"' in result.output
    assert "target,hop,ip" not in result.output  # not CSV by default


# --- A target without a usable host ----------------------------------------
#
# ``trace`` used to raise a bare ``ValueError`` for such a target, which
# escaped as a raw traceback. It is now reported as a usage error.

@pytest.mark.parametrize("target", UNUSABLE_TARGETS)
def test_trace_rejects_a_target_without_a_host(target):
    """An unusable target must be rejected cleanly."""
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["trace", "--target", target])
    _assert_target_usage_error(result, f"trace --target {target!r}")
    assert TARGET_ERROR_MESSAGE in result.output, result.output


def test_trace_usage_error_is_a_single_line():
    """The failure must be a one-line error, not a multi-line traceback."""
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["trace", "--target", ""])
    error_lines = [
        line for line in result.output.splitlines() if line.startswith("Error:")
    ]
    assert len(error_lines) == 1, result.output
    assert error_lines[0] == (
        "Error: Invalid value for '--target': Invalid target"
    )


def test_trace_usage_error_does_not_start_a_probe(monkeypatch):
    """A rejected target must abort before any network access happens."""
    import ethscan.trace

    calls = []

    def make_tripwire(attribute):
        def tripwire(*args, **kwargs):
            calls.append(attribute)
            raise AssertionError("a probe was started for an invalid target")

        return tripwire

    monkeypatch.setattr(
        ethscan.trace.socket, "gethostbyname", make_tripwire("gethostbyname")
    )
    monkeypatch.setattr(ethscan.trace, "_probe_once", make_tripwire("_probe_once"))

    runner = CliRunner()
    for target in UNUSABLE_TARGETS:
        result = runner.invoke(cli.cli, ["trace", "--target", target])
        _assert_target_usage_error(result, f"trace --target {target!r}")
    assert calls == [], "no probe may start for an invalid --target value"


def test_trace_still_accepts_a_usable_target(monkeypatch):
    """A target with a usable host keeps reaching the traceroute."""
    calls = []

    def fake_run(target, port=80, max_hops=30, timeout=2.0, probes_per_hop=3, recursive=False, max_depth=2):
        calls.append(target)
        return {
            "target": target,
            "dst_ip": "1.1.1.1",
            "port": port,
            "max_hops": max_hops,
            "timeout": timeout,
            "probes_per_hop": probes_per_hop,
            "hops": [],
            "reached": False,
        }

    monkeypatch.setattr(cli, "run_trace", fake_run)
    runner = CliRunner()
    for target in ("example.com", "example.com:80", "http://example.com/"):
        result = runner.invoke(cli.cli, ["trace", "--target", target])
        assert result.exit_code == 0, f"{target}: {result.output}"
        assert "Invalid value for '--target'" not in result.output, result.output
    assert calls == ["example.com", "example.com:80", "http://example.com/"]
