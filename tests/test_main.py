"""Tests for the ethscan entry points (ethscan.main and ethscan.__main__)."""

import ast
import contextlib
import importlib
import inspect
import json
import runpy
import subprocess
import sys

import pytest
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
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "scan" in result.stdout


def test_python_m_ethscan_version_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ethscan", "--version"],
        check=False,
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

        sys.modules.pop("ethscan.main", None)

        called = {"n": 0}
        orig_cli = cli_mod.cli

        def counting_cli(*args, **kwargs):
            called["n"] += 1
            raise SystemExit(0)

        cli_mod.cli = counting_cli
        try:
            with contextlib.suppress(SystemExit):
                runpy.run_module("ethscan.main", run_name="__main__")
        finally:
            cli_mod.cli = orig_cli
    finally:
        sys.argv = saved_argv

    assert called["n"] == 1, "cli() should be invoked exactly once by the __main__ guard"


def test_python_m_ethscan_dunder_main_help_runs() -> None:
    """Execute ethscan.__main__ with __name__ == "__main__" to cover the cli() guard (__main__.py:6)."""
    import runpy

    saved_argv = sys.argv
    sys.argv = ["ethscan.__main__", "--help"]
    try:
        called = {"n": 0}

        def counting_cli(*args, **kwargs):
            called["n"] += 1
            raise SystemExit(0)

        import ethscan.cli as cli_mod

        sys.modules.pop("ethscan.__main__", None)

        orig_cli = cli_mod.cli
        cli_mod.cli = counting_cli
        try:
            with contextlib.suppress(SystemExit):
                runpy.run_module("ethscan.__main__", run_name="__main__")
        finally:
            cli_mod.cli = orig_cli
    finally:
        sys.argv = saved_argv

    assert called["n"] == 1, "cli() should be invoked exactly once by the __main__ guard"


@pytest.mark.parametrize("module_name", ["ethscan.cli", "ethscan.main", "ethscan.__main__"])
def test_main_guard_is_the_last_statement_of_the_module(module_name: str) -> None:
    """The __main__ guard must be the last statement of an entry-point module.

    The guard runs the CLI while the module body is still executing, so a
    name that a command uses but that is defined below the guard is not
    bound yet and the command dies with a NameError.
    """
    module = importlib.import_module(module_name)
    tree = ast.parse(inspect.getsource(module))

    last = tree.body[-1]
    assert isinstance(last, ast.If), f"{module_name} has a statement below the __main__ guard"
    test = last.test
    assert isinstance(test, ast.Compare)
    assert isinstance(test.left, ast.Name) and test.left.id == "__name__"
    assert [type(op) for op in test.ops] == [ast.Eq]
    assert [comparator.value for comparator in test.comparators] == ["__main__"]


def test_cli_module_as_main_runs_the_brute_command(monkeypatch, tmp_path, capsys) -> None:
    """Execute ethscan.cli with __name__ == "__main__" and run a command.

    The guard of ethscan/cli.py runs the CLI while the module body is
    still executing, so a helper that the commands use has to be defined
    above the guard. The FTP transport is replaced, so the command reports
    its own failure field instead of reaching the network.
    """

    class _FakeFTP:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def connect(self, *args, **kwargs) -> None:
            raise RuntimeError("hostile transport")

        def close(self) -> None:
            pass

    monkeypatch.setattr("ethscan.brute.FTP", _FakeFTP)

    user_file = tmp_path / "users.txt"
    pass_file = tmp_path / "passwords.txt"
    user_file.write_text("admin\n", encoding="utf-8")
    pass_file.write_text("admin\n", encoding="utf-8")

    saved_argv = sys.argv
    sys.argv = [
        "ethscan.cli",
        "brute",
        "--target",
        "127.0.0.1",
        "--user-file",
        str(user_file),
        "--pass-file",
        str(pass_file),
        "--timeout",
        "1.0",
    ]
    try:
        sys.modules.pop("ethscan.cli", None)
        with contextlib.suppress(SystemExit):
            runpy.run_module("ethscan.cli", run_name="__main__")
    finally:
        sys.argv = saved_argv

    report = json.loads(capsys.readouterr().out)
    assert report["attempts"] == 1
    assert report["successful_count"] == 0
    assert report["results"][0]["error"] == "hostile transport"
