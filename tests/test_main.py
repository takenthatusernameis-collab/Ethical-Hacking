"""Tests for the ethscan entry points (ethscan.main and ethscan.__main__)."""

import inspect
import subprocess
import sys

from click.testing import CliRunner

import ethscan.__main__
import ethscan.main
from ethscan import __version__
from ethscan.cli import cli


def test_main_module_exposes_cli() -> None:
    assert ethscan.main.cli is cli


def test_main_module_guard_present() -> None:
    source = inspect.getsource(ethscan.main)
    assert 'if __name__ == "__main__":' in source
    assert "cli()" in source


def test_main_dunder_main_module_exposes_cli() -> None:
    assert ethscan.__main__.cli is cli


def test_main_dunder_main_guard_present() -> None:
    source = inspect.getsource(ethscan.__main__)
    assert 'if __name__ == "__main__":' in source
    assert "cli()" in source


def test_cli_help_via_entry_point() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "hash" in result.output


def test_cli_version_via_entry_point() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_python_m_ethscan_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ethscan", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "scan" in result.stdout


def test_python_m_ethscan_version_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ethscan", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_python_m_ethscan_main_help_runs() -> None:
    """Execute ethscan.main with __name__ == "__main__" to cover the cli() guard (main.py:7)."""
    import runpy

    saved_argv = sys.argv
    sys.argv = ["ethscan.main", "--help"]
    try:
        import ethscan.cli as cli_mod

        called = {"n": 0}
        orig_cli = cli_mod.cli

        def counting_cli(*args, **kwargs):
            called["n"] += 1
            raise SystemExit(0)

        cli_mod.cli = counting_cli
        try:
            try:
                runpy.run_module("ethscan.main", run_name="__main__")
            except SystemExit:
                pass
        finally:
            cli_mod.cli = orig_cli
    finally:
        sys.argv = saved_argv

    assert called["n"] == 1, "cli() should be invoked exactly once by the __main__ guard"
