"""Permanent sweep test: every string option of every command refuses hostile values.

The hostile sweep of the session that finished the CLI's hostile-option work
lives outside the repository (it is a script, not a test) because it needs a
per-invocation timeout and takes about twenty minutes. This test is the short,
permanent version: it walks the commands of ``ethscan.cli`` and checks that
every **string** option of every command refuses a small set of hostile values
without leaking a traceback.

The per-invocation timeout is enforced with ``signal.SIGALRM``, the same
mechanism the sweep scripts use. Commands that need a network round trip to
probe a real host are excluded by name: they time out under the timeout and are
not part of the guarantee this test enforces (the sweep of the previous
sessions timed them out with or without a change).

A command that leaks a traceback is a finding, not a test failure to be
papered over: the assertion names the command, the option and the value.
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


# Commands that probe a real host and take a network round trip. They are
# excluded from the sweep: a per-invocation timeout of a few seconds is not
# enough for them, and they are not part of the "no traceback leak" guarantee
# that this test enforces.
SLOW_COMMANDS = frozenset({"dnssec", "netbios", "snmp"})

# Commands that have no string options at all (nothing to sweep).
NO_STRING_OPTIONS = frozenset({"config", "nmap", "validate"})

# Hostile values per option. A small set: an empty string, an over-long name
# and a path that does not exist. The sweep of the previous sessions used many
# more values per option; this test keeps the guarantee alive with a handful.
HOSTILE_VALUES = ("", "x" * 300, "/nonexistent/path")

# Commands that need a --target to run and whose option under test is not the
# target itself get this target supplied.
TARGET = "127.0.0.1"

# Per-invocation timeout, in seconds. Short enough that the whole test stays
# well under a minute, with margin for the slowest included command (s3, which
# peaks around 2.5s when its target triggers a DNS lookup).
PER_INVOCATION_TIMEOUT = 5

# Commands that resolve a name for every candidate and therefore wait for the
# full DNS timeout when the resolver does not answer. They stay in the sweep
# (their options are swept like every other command) but they get a longer
# per-invocation timeout: with the short one the sweep failed on a slow
# resolver, although the command itself exits cleanly. The subtake command
# resolves three record types for each of its 26 candidate labels, so it needs
# the same margin as the subdomains command.
DNS_COMMANDS = frozenset({"subdomains", "subtake"})

# Per-invocation timeout for the commands of DNS_COMMANDS, in seconds.
DNS_COMMAND_TIMEOUT = 20


def _string_params(cmd: Any) -> list:
    """Return the string-typed options of a command that have a CLI flag."""
    return [
        p
        for p in cmd.params
        if type(p.type).__name__ == "StringParamType" and p.opts
    ]


def _build_args(name: str, param: Any, value: str) -> list[str]:
    """Build the argv for one (command, option, value) invocation."""
    args = [name, param.opts[0], value]
    has_target = any(q.name == "target" for q in cli.cli.commands[name].params)
    if has_target and param.name != "target":
        args += ["--target", TARGET]
    return args


@pytest.mark.parametrize("name", sorted(cli.cli.commands))
def test_every_string_option_refuses_hostile_values(name: str, no_external_network) -> None:
    """Every string option of every command refuses hostile values cleanly.

    A hostile value is an empty string, an over-long name or a path that does
    not exist. The command must not leak a traceback: it either reports a
    usage error (exit 2), reports a failed probe inside its own output (exit
    0) or exits 1 for its own reasons, but never with an unhandled exception.
    """
    if name in SLOW_COMMANDS or name in NO_STRING_OPTIONS:
        pytest.skip(
            f"{name} is excluded from the sweep (see module docstring)"
        )
    params = _string_params(cli.cli.commands[name])
    if not params:
        pytest.skip(f"{name} has no string options")

    signal.signal(signal.SIGALRM, _alarm)
    runner = CliRunner()
    timeout = DNS_COMMAND_TIMEOUT if name in DNS_COMMANDS else PER_INVOCATION_TIMEOUT
    try:
        for param in params:
            for value in HOSTILE_VALUES:
                args = _build_args(name, param, value)
                signal.setitimer(signal.ITIMER_REAL, timeout)
                try:
                    result = runner.invoke(cli.cli, args)
                except _Timeout:
                    pytest.fail(
                        f"{name} {param.opts[0]} {value!r} timed out after "
                        f"{timeout}s"
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