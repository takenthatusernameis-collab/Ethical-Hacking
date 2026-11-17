"""Regression guard keeping the README in sync with the CLI.

``check_readme.py`` performs a manual check, but nothing in the test suite
prevented the README from drifting away from the CLI. That drift recurred
repeatedly: commands were documented as offering options they do not have,
whole commands were omitted, or CLI options were added without ever being
documented. This module turns those checks into permanent, deterministic
tests so drift fails the suite instead of slipping through.

Two levels are covered:

* command presence -- a registered command that is never documented, or a
  README bullet naming a command the CLI does not register, fails.
* option presence -- for every documented command bullet, the set of
  ``--long`` options mentioned must exactly match the options Click exposes
  for that command (including boolean ``--foo/--no-foo`` pairs and aliases
  such as ``--format``/``--output-format``). Options are read from Click's
  own parameter metadata rather than by scraping ``--help`` text, so the
  check is exact and fast rather than brittle.
"""
from __future__ import annotations

import re
from pathlib import Path

import click

from ethscan.cli import cli

# Matches the bullet style used throughout the README:
#   - **<label>: `cmd` command ...
# The same pattern is used by check_readme.py so the two stay in agreement.
_COMMAND_BULLET = re.compile(
    r"^-\s+\*\*[^:]+:\s+`([a-z0-9]+)`\s+command",
    re.MULTILINE,
)

# Matches a long CLI option token such as ``--output-format`` inside a README
# bullet. Lowercase to match the toolkit's option naming convention.
_OPTION_TOKEN = re.compile(r"--[a-z0-9][a-z0-9-]*")

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def _readme_bullets() -> dict[str, str]:
    """Map each documented command to the README bullet line documenting it."""
    content = README_PATH.read_text(encoding="utf-8")
    bullets: dict[str, str] = {}
    for line in content.splitlines():
        match = _COMMAND_BULLET.match(line)
        if match:
            bullets[match.group(1)] = line
    return bullets


def _readme_commands() -> set[str]:
    return set(_readme_bullets())


def _readme_options() -> dict[str, set[str]]:
    """Documented long options per command, parsed from the README bullets."""
    return {
        cmd: set(_OPTION_TOKEN.findall(line))
        for cmd, line in _readme_bullets().items()
    }


def _cli_options(command: click.Command) -> set[str]:
    """Every long option Click exposes for *command*, excluding ``--help``."""
    options: set[str] = set()
    for param in command.params:
        options.update(param.opts)
        options.update(param.secondary_opts)
    options.discard("--help")
    return {opt for opt in options if opt.startswith("--")}


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


def test_readme_documents_every_cli_option() -> None:
    documented = _readme_options()
    missing_by_command: dict[str, list[str]] = {}
    for name, command in cli.commands.items():
        undocumented = _cli_options(command) - documented.get(name, set())
        if undocumented:
            missing_by_command[name] = sorted(undocumented)
    assert not missing_by_command, (
        "CLI options missing from the README bullet for their command "
        f"(document them so the README stays in sync): {missing_by_command}"
    )


def test_readme_has_no_unknown_options() -> None:
    documented = _readme_options()
    unknown_by_command: dict[str, list[str]] = {}
    for name, options in documented.items():
        command = cli.commands.get(name)
        if command is None:
            continue  # unknown commands are covered by the presence test
        unknown = options - _cli_options(command)
        if unknown:
            unknown_by_command[name] = sorted(unknown)
    assert not unknown_by_command, (
        "README documents options the CLI does not expose "
        f"(remove or fix them): {unknown_by_command}"
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