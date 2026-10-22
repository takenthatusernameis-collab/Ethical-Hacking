"""Permanent check: every command of the CLI is covered by a CLI-level sweep.

The CLI sweeps check the same invariant for every command of the CLI: a
command that cannot do its work reports the failure and never raises. The
check below compares the commands the CLI has with the commands the sweeps
name, so a command that is added without a sweep check is caught here instead
of being counted by hand.

The comparison is made on the source of the sweeps: a command is covered when
one of the sweeps names it as the command it runs.
"""
from __future__ import annotations

import ast
from pathlib import Path

from ethscan import cli

#: The directory the sweeps live in.
TESTS_DIR = Path(__file__).parent


def _sweep_files() -> list[Path]:
    """Return the source of every CLI sweep."""
    return sorted(TESTS_DIR.glob("test_cli_*sweep*.py"))


def _named_commands(path: Path) -> set[str]:
    """Return every string literal the file holds.

    The literals are read from the parsed source, so a name that is only
    mentioned in a comment does not count as a covered command.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_every_command_of_the_cli_is_named_in_a_cli_sweep() -> None:
    """Every command of the CLI is covered by a CLI-level sweep."""
    named: set[str] = set()
    for path in _sweep_files():
        named |= _named_commands(path)

    every = set(cli.cli.commands)
    missing = sorted(every - named)

    assert not missing, f"commands without a CLI-level sweep: {missing}"
