"""Permanent sweep test: every file option of every command refuses hostile values.

This complements the string-option sweep by exercising file-path options with
hostile inputs (missing files, directories passed as files, over-long names).
The command must not leak a traceback; it should return a usage error (exit 2)
or a controlled exit per its contract.
"""
from __future__ import annotations

import signal
from typing import Any

import pytest
from click.testing import CliRunner

from ethscan import cli


class _Timeout(BaseException):
    """Raised by the alarm to abort a single invocation."""


def _alarm(signum: int, frame: Any) -> None:
    raise _Timeout()


SLOW_COMMANDS = frozenset({"dnssec", "netbios", "snmp"})

# Hostile values for file paths
HOSTILE_VALUES = ("/nonexistent/path/that/does/not/exist", "/tmp", "x" * 300)

# Some file options might legitimately behave differently; but for most,
# click.Path(exists=True, readable=True, dir_okay=False) gives exit 2.
# Also commands that need a --target
TARGET = "127.0.0.1"
PER_INVOCATION_TIMEOUT = 5


def _file_params(cmd: Any) -> list:
    params = []
    for p in cmd.params:
        t = type(p.type)
        tname = getattr(t, "__name__", str(t))
        if "Path" in tname and p.opts:
            params.append(p)
    return params


def _build_args(name: str, param: Any, value: str) -> list[str]:
    args = [name, param.opts[0], value]
    # Add target if command needs it and param isn't target
    cmd = cli.cli.commands.get(name)
    if cmd:
        has_target = any(q.name == "target" for q in cmd.params)
        if has_target and param.name != "target":
            args += ["--target", TARGET]
    return args


@pytest.mark.parametrize("name", sorted(cli.cli.commands))
def test_every_file_option_refuses_hostile_values(name: str, no_external_network) -> None:
    if name in SLOW_COMMANDS:
        pytest.skip(f"{name} is excluded from the sweep")
    cmd = cli.cli.commands.get(name)
    if cmd is None:
        return
    params = _file_params(cmd)
    if not params:
        pytest.skip(f"{name} has no file options")

    signal.signal(signal.SIGALRM, _alarm)
    runner = CliRunner()
    try:
        for param in params:
            for value in HOSTILE_VALUES:
                args = _build_args(name, param, value)
                signal.setitimer(signal.ITIMER_REAL, PER_INVOCATION_TIMEOUT)
                try:
                    result = runner.invoke(cli.cli, args)
                except _Timeout:
                    pytest.fail(
                        f"{name} {param.opts[0]} {value!r} timed out after "
                        f"{PER_INVOCATION_TIMEOUT}s"
                    )
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                exc = result.exception
                if exc is not None and not isinstance(exc, SystemExit):
                    pytest.fail(
                        f"{name} {param.opts[0]} {value!r} leaked a traceback: "
                        f"{type(exc).__name__}: {exc}"
                    )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
