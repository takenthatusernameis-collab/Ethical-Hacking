"""Permanent sweep test: every config value of every command is refused when its type is wrong.

The file-option sweep (``tests/test_file_option_sweep.py``) checks the *path*
of a file option and the file-content sweep (``tests/test_file_content_sweep.py``)
checks the *content* of a file. This sweep checks the fourth source of
hostile input: the values that the config file holds.

A config value reaches a command through click's ``default_map``, so the
option's own type checks it. Click's converters only ever see the text that a
command line delivers, so a config value that is a mapping (or a sequence)
made click raise an unhandled ``TypeError`` instead of reporting a usage
error. Every value of the wrong type must be refused as a usage error (exit
code 2) that names the option, and no command may leak a traceback.

The per-invocation timeout is enforced with ``signal.SIGALRM``, the same
mechanism the other sweeps use. The commands that need a network round trip to
probe a real host are excluded by name, the same way the other sweeps exclude
them.
"""
from __future__ import annotations

import signal
from typing import Any

import click
import pytest
import yaml
from click.testing import CliRunner

from ethscan import cli


class _Timeout(BaseException):
    """Raised by the alarm to abort a single invocation."""


def _alarm(signum: int, frame: Any) -> None:
    raise _Timeout()


# Commands that probe a real host and take a network round trip. They are
# excluded from the sweep for the same reason as in the other sweeps.
SLOW_COMMANDS = frozenset({"dnssec", "netbios", "snmp"})

# A mapping is never a valid value for a single option, so it is hostile for
# every option of every command.
HOSTILE_MAPPING = {"a": 1}

# A value of the wrong type for the option types that have one. Click refuses
# these the same way it refuses the same text on the command line.
HOSTILE_SCALARS = {
    "IntRange": "many",
    "IntParamType": "many",
    "FloatRange": "abc",
    "FloatParamType": "abc",
    "Choice": "bogus",
    "BoolParamType": "maybe",
}

# A file option that has to exist is also hostile when it names a file that
# is not there.
MISSING_PATH = "/nonexistent/path/from/the/config/file"

# Commands that need a --target to run get this target supplied.
TARGET = "127.0.0.1"

# The value that satisfies a required option of a command.
REQUIRED_VALUES = {
    "target": TARGET,
    "cidr": "192.168.1.0/24",
}

# Per-invocation timeout, in seconds.
PER_INVOCATION_TIMEOUT = 5


def _hostile_values(param: Any) -> list[Any]:
    """Return the values that the config file must refuse for an option."""
    values: list[Any] = [HOSTILE_MAPPING]
    if param.multiple:
        values.append([HOSTILE_MAPPING])
        return values
    type_name = type(param.type).__name__
    if type_name in HOSTILE_SCALARS:
        values.append(HOSTILE_SCALARS[type_name])
    elif type_name == "Path" and getattr(param.type, "exists", False):
        values.append(MISSING_PATH)
    return values


def _option_hint(param: Any, ctx: click.Context) -> str:
    """Return the hint click uses for an option in its error messages."""
    return param.get_error_hint(ctx)


def _required_args(cmd: Any, tmp_path: Any, skip: str) -> list[str]:
    """Return the arguments that satisfy the required options of a command.

    The option under test is left out: the config file has to fill it, or
    the command would stop at the missing option before the config value is
    ever looked at.
    """
    args: list[str] = []
    for param in cmd.params:
        if not param.required or param.name == skip or not param.opts:
            continue
        if param.name == "input_file":
            path = tmp_path / "nmap.xml"
            path.write_text("<nmaprun></nmaprun>")
            args += [param.opts[0], str(path)]
        else:
            args += [param.opts[0], REQUIRED_VALUES.get(param.name, TARGET)]
    return args


@pytest.mark.parametrize("name", sorted(cli.cli.commands))
def test_every_config_value_of_the_wrong_type_is_refused(name: str, tmp_path) -> None:
    """Every config value of the wrong type is refused as a usage error.

    The value is written to the config file twice: once for the command
    itself and once in the global defaults, which every command inherits. The
    command must report a usage error (exit code 2) that names the option,
    and must never leak a traceback.
    """
    if name in SLOW_COMMANDS:
        pytest.skip(f"{name} is excluded from the sweep (see module docstring)")
    cmd = cli.cli.commands.get(name)
    if cmd is None:
        return
    params = [p for p in cmd.params if p.opts or p.human_readable_name]
    if not params:
        pytest.skip(f"{name} has no options")

    ctx = click.Context(cmd)
    signal.signal(signal.SIGALRM, _alarm)
    runner = CliRunner()
    try:
        for param in params:
            for index, value in enumerate(_hostile_values(param)):
                sections = (
                    ("command", {"commands": {name: {param.name: value}}}),
                    ("global", {"defaults": {param.name: value}}),
                )
                for section, payload in sections:
                    path = tmp_path / f"{name}-{param.name}-{section}-{index}.yaml"
                    path.write_text(yaml.safe_dump(payload))
                    args = ["--config", str(path), name]
                    args += _required_args(cmd, tmp_path, skip=param.name)
                    signal.setitimer(signal.ITIMER_REAL, PER_INVOCATION_TIMEOUT)
                    try:
                        result = runner.invoke(cli.cli, args)
                    except _Timeout:
                        pytest.fail(
                            f"{name} {param.name} {value!r} timed out after "
                            f"{PER_INVOCATION_TIMEOUT}s"
                        )
                    finally:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                    exc = result.exception
                    if exc is not None and not isinstance(exc, SystemExit):
                        pytest.fail(
                            f"{name} {param.name} {value!r} leaked a traceback: "
                            f"{type(exc).__name__}: {exc}"
                        )
                    assert result.exit_code == 2, (
                        f"{name} {param.name} {value!r} ({section}) should be a usage "
                        f"error, got exit code {result.exit_code}\n{result.output}"
                    )
                    assert "Invalid value for" in result.output, (
                        f"{name} {param.name} {value!r} ({section}) did not report a "
                        f"usage error\n{result.output}"
                    )
                    assert f"Invalid value for {_option_hint(param, ctx)}" in result.output, (
                        f"{name} {param.name} {value!r} ({section}) did not name the "
                        f"option\n{result.output}"
                    )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def test_a_valid_config_value_is_applied_and_not_refused(tmp_path) -> None:
    """A config value of the right type is used, not refused."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text(yaml.safe_dump({"commands": {"cidr": {"output_fmt": "csv"}}}))
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["--config", str(cfg), "cidr", "--cidr", "192.168.1.0/24"],
    )
    assert result.exit_code == 0, result.output
    assert "network_address" in result.output


def test_a_valid_global_config_value_is_applied_and_not_refused(tmp_path) -> None:
    """A global config value of the right type is used, not refused."""
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text(yaml.safe_dump({"defaults": {"output_fmt": "csv"}}))
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["--config", str(cfg), "cidr", "--cidr", "192.168.1.0/24"],
    )
    assert result.exit_code == 0, result.output
    assert "network_address" in result.output


def test_a_config_value_of_a_command_that_is_not_run_is_not_refused(tmp_path) -> None:
    """A broken value of another command does not stop this command.

    The config file is read by every command, but a value that only another
    command uses is none of this command's business.
    """
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text(yaml.safe_dump({"commands": {"scan": {"workers": {"a": 1}}}}))
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["--config", str(cfg), "cidr", "--cidr", "192.168.1.0/24"],
    )
    assert result.exit_code == 0, result.output


def test_a_command_line_value_overrides_a_broken_config_value(tmp_path) -> None:
    """A command line argument still wins over a broken config value.

    Click looks a config value up only for the options that the command line
    did not fill, so a value that is overridden is never used and never
    refused. The command line always takes precedence over the config file.
    """
    cfg = tmp_path / "ethscan.yaml"
    cfg.write_text(yaml.safe_dump({"commands": {"cidr": {"output_fmt": {"a": 1}}}}))
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "--config",
            str(cfg),
            "cidr",
            "--cidr",
            "192.168.1.0/24",
            "--output-format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "network_address" in result.output
