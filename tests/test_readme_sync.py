"""Regression guard keeping the README command list in sync with the CLI.

``check_readme.py`` performs this check by hand, but nothing in the test
suite prevented the README from drifting away from the CLI. That drift
recurred repeatedly: commands were documented as offering options they do
not have, or whole commands were omitted. This module turns the manual
command-presence check into a permanent, deterministic test so a new command
that is registered but never documented (or a README bullet that names a
command that no longer exists) fails the suite instead of slipping through.

The check is deliberately limited to command *presence*: comparing every
documented option against ``--help`` output is brittle and slow, while the
presence check is exact and catches the most common and most damaging drift
(a command missing from one side or the other).
"""
from __future__ import annotations

import re
from pathlib import Path

from ethscan.cli import cli

# Matches the bullet style used throughout the README:
#   - **<label>: `cmd` command ...
# The same pattern is used by check_readme.py so the two stay in agreement.
_COMMAND_BULLET = re.compile(
    r"^-\s+\*\*[^:]+:\s+`([a-z0-9]+)`\s+command",
    re.MULTILINE,
)

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def _readme_commands() -> set[str]:
    content = README_PATH.read_text(encoding="utf-8")
    return set(_COMMAND_BULLET.findall(content))


def test_readme_documents_every_cli_command() -> None:
    readme = _readme_commands()
    cli_commands = set(cli.commands.keys())
    missing = cli_commands - readme
    assert not missing, (
        "CLI commands missing a README bullet "
        f"(add a '- **...: `cmd` command ...' bullet): {sorted(missing)}"
    )


def test_readme_has_no_unknown_commands() -> None:
    readme = _readme_commands()
    cli_commands = set(cli.commands.keys())
    unknown = readme - cli_commands
    assert not unknown, (
        "README documents commands that the CLI does not register "
        f"(remove or rename these bullets): {sorted(unknown)}"
    )


def test_readme_command_parser_finds_a_plausible_number() -> None:
    """Guard the parser itself: a broken regex would make the checks above vacuous."""
    readme = _readme_commands()
    assert len(readme) >= 50, (
        "README command parser found too few commands "
        f"({len(readme)}); the bullet pattern may have regressed"
    )
    assert len(readme) == len(cli.commands), (
        "README documents a different number of commands than the CLI "
        f"registers ({len(readme)} vs {len(cli.commands)})"
    )