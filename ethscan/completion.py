"""Shell completion support for ethscan.

Generates shell completion scripts for bash, zsh, and fish using
click's built-in shell completion machinery. The scripts wrap the
``ethscan`` CLI so that interactive shells can tab-complete command
names, option names, and option values.
"""

import csv
import io
from typing import Any

import click
from click import shell_completion

# Default program name used in the generated completion scripts.
DEFAULT_PROG_NAME = "ethscan"


def _available_shells() -> dict[str, Any]:
    """Return the mapping of supported shell names to click completion classes.

    Uses click's internal registry so the list always matches what click
    can actually generate. Falls back to a static set if the registry is
    unavailable.
    """
    try:
        return dict(shell_completion._available_shells)
    except AttributeError:  # pragma: no cover - defensive fallback
        return {"bash": shell_completion.BashComplete,
                "zsh": shell_completion.ZshComplete,
                "fish": shell_completion.FishComplete}


def available_shells() -> tuple[str, ...]:
    """Return the tuple of shell names that ethscan can generate completions for."""
    return tuple(sorted(_available_shells().keys()))


def _completion_class_for(shell: str):
    """Return the click ShellComplete subclass for ``shell``.

    Raises ``ValueError`` if the shell is not supported.
    """
    shells = _available_shells()
    if shell not in shells:
        raise ValueError(
            f"Unsupported shell: {shell}. Supported: {', '.join(sorted(shells))}"
        )
    return shells[shell]


def generate_completion_script(
    cli_obj: click.BaseCommand,
    shell: str,
    prog_name: str = DEFAULT_PROG_NAME,
) -> str:
    """Generate the completion script for ``shell``.

    ``cli_obj`` is the click group (or any command) to generate
    completions for. ``prog_name`` is the name the user types in their
    shell (e.g. ``ethscan``); it is embedded in the generated script.
    """
    complete_cls = _completion_class_for(shell)
    # Click derives the completion environment variable at runtime by
    # replacing "-" and "." with "_" before upper-casing (click/core.py).
    # The generated script must use the same name or the completion can
    # never be triggered.
    sanitized_name = prog_name.replace("-", "_").replace(".", "_")
    complete_var = f"_{sanitized_name.upper()}_COMPLETE"
    complete = complete_cls(cli_obj, {}, prog_name, complete_var)
    return complete.source()


def run_completion(
    cli_obj: click.BaseCommand,
    shell: str,
    prog_name: str = DEFAULT_PROG_NAME,
) -> dict[str, Any]:
    """Public entry point: build a structured completion report.

    Returns a dictionary with ``shell``, ``prog_name``, and ``script``
    keys. Raises ``ValueError`` for unsupported shells.
    """
    if shell not in _available_shells():
        raise ValueError(
            f"Unsupported shell: {shell}. Supported: {', '.join(available_shells())}"
        )
    script = generate_completion_script(cli_obj, shell, prog_name)
    return {
        "shell": shell,
        "prog_name": prog_name,
        "script": script,
    }


def format_completion_report_json(result: dict[str, Any]) -> str:
    """Render a completion report as JSON."""
    import json

    return json.dumps(result, indent=2, default=str)


def format_completion_report_markdown(result: dict[str, Any]) -> str:
    """Render a completion report as Markdown."""
    lines = [
        "# ethscan Shell Completion",
        "",
        f"- **Shell:** {result['shell']}",
        f"- **Program:** {result['prog_name']}",
        "",
        "## Script",
        "",
        "```",
        result["script"].rstrip(),
        "```",
        "",
        "## Installation",
        "",
        "Save the script above to a file and source it in your shell:",
        "",
        "```bash",
        "# bash",
        "ethscan completion bash > ~/.ethscan_complete.bash",
        "source ~/.ethscan_complete.bash",
        "```",
        "",
        "```zsh",
        "# zsh",
        "ethscan completion zsh > ~/.ethscan_complete.zsh",
        "source ~/.ethscan_complete.zsh",
        "```",
        "",
        "```fish",
        "# fish",
        "ethscan completion fish > ~/.config/fish/completions/ethscan.fish",
        "```",
        "",
    ]
    return "\n".join(lines)


def format_completion_report_csv(result: dict[str, Any]) -> str:
    """Format completion report as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["field", "value"])
    writer.writerow(["shell", result.get("shell", "")])
    writer.writerow(["prog_name", result.get("prog_name", "")])
    writer.writerow([])
    writer.writerow(["script"])
    script = result.get("script", "")
    for line in script.splitlines():
        writer.writerow([line])

    return output.getvalue().rstrip("\r\n")