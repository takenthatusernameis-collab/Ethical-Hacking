"""CLI tests for trace command."""
from click.testing import CliRunner

from ethscan import cli


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
