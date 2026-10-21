"""Permanent sweep test: every input file of every command survives hostile content.

The file-option sweep (``tests/test_file_option_sweep.py``) checks the *path*
of a file option: a missing file, a directory, an over-long name. This sweep
checks the *content* of the file: bytes that are not valid UTF-8, a null byte,
a line that holds a space, a file that is not the JSON (or the XML) it claims
to be. The command must not leak a traceback: it reports the problem as a
usage error (exit 2), reports it inside its own output (exit 0) or exits 1
for its own reasons, but never with an unhandled exception.

The per-invocation timeout is enforced with ``signal.SIGALRM``, the same
mechanism the other sweeps use. The commands that need a network round trip to
probe a real host are excluded by name, the same way the file-option sweep
excludes them.
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
# excluded from the sweep for the same reason as in the file-option sweep.
SLOW_COMMANDS = frozenset({"dnssec", "netbios", "snmp"})

# The options that name a file the command *reads*. The options that name an
# output path (``--out``, ``--output``, ``--init``) are not part of the sweep:
# their content is written by the command, not read from the file system.
INPUT_FILE_DESTS = frozenset(
    {
        "file",
        "password_file",
        "user_file",
        "pass_file",
        "config_path",
        "services_file",
        "tls_file",
        "ssl_file",
        "wordlist_path",
        "subdomains_wordlist_path",
        "input_file",
        "banners_file",
        "cidr_file",
        "audit_file",
        "target_file",
    }
)

# Hostile content: bytes that are not valid UTF-8, a null byte, a line that
# holds a space, a file that is not the JSON (or the XML) it claims to be, and
# a JSON file that nests deeper than the parser can read.
HOSTILE_CONTENTS = (
    b"\xff\xfe not utf-8\n",
    b"a\x00b\n",
    b"a b\n",
    b"{ not json\n",
    b"[" * 20000 + b"]" * 20000,
)

# Commands that need a --target to run get this target supplied.
TARGET = "127.0.0.1"

# Per-invocation timeout, in seconds.
PER_INVOCATION_TIMEOUT = 5


def _input_file_params(cmd: Any) -> list:
    """Return the options of a command that read a file."""
    return [p for p in cmd.params if p.name in INPUT_FILE_DESTS and p.opts]


@pytest.mark.parametrize("name", sorted(cli.cli.commands))
def test_every_input_file_survives_hostile_content(name: str, tmp_path) -> None:
    """Every input file of every command is read without leaking a traceback.

    A hostile file holds bytes that are not valid UTF-8, a null byte, a space
    or content that is not the JSON (or the XML) the option expects. The
    command must not leak a traceback: it either reports a usage error (exit
    2), reports a failed read inside its own output (exit 0) or exits 1 for
    its own reasons, but never with an unhandled exception.
    """
    if name in SLOW_COMMANDS:
        pytest.skip(f"{name} is excluded from the sweep (see module docstring)")
    cmd = cli.cli.commands.get(name)
    if cmd is None:
        return
    params = _input_file_params(cmd)
    if not params:
        pytest.skip(f"{name} has no input file options")

    has_target = any(q.name == "target" for q in cmd.params)
    signal.signal(signal.SIGALRM, _alarm)
    runner = CliRunner()
    try:
        for param in params:
            for index, content in enumerate(HOSTILE_CONTENTS):
                path = tmp_path / f"{param.name}-{index}.txt"
                path.write_bytes(content)
                args = [name, param.opts[0], str(path)]
                if has_target:
                    args += ["--target", TARGET]
                signal.setitimer(signal.ITIMER_REAL, PER_INVOCATION_TIMEOUT)
                try:
                    result = runner.invoke(cli.cli, args)
                except _Timeout:
                    pytest.fail(
                        f"{name} {param.opts[0]} {content!r} timed out after "
                        f"{PER_INVOCATION_TIMEOUT}s"
                    )
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                exc = result.exception
                if exc is not None and not isinstance(exc, SystemExit):
                    pytest.fail(
                        f"{name} {param.opts[0]} {content!r} leaked a traceback: "
                        f"{type(exc).__name__}: {exc}"
                    )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
