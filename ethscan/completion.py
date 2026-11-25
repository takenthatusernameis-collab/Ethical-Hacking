"""Shell completion support for ethscan.

Generates shell completion scripts for bash, zsh, and fish using
click's built-in shell completion machinery. The scripts wrap the
``ethscan`` CLI so that interactive shells can tab-complete command
names, option names, and option values.
"""

from ethscan.fileio import csv_writer
import io
import os
from pathlib import Path
from typing import Any

import click
from click import shell_completion

# Default program name used in the generated completion scripts.
DEFAULT_PROG_NAME = "ethscan"

# Shell RC file locations and source snippets.
_SHELL_RC_INFO: dict[str, dict[str, str]] = {
    "bash": {
        "rc_file": "~/.bashrc",
        "source_line": 'source ~/.ethscan_complete.bash',
        "script_path": "~/.ethscan_complete.bash",
    },
    "zsh": {
        "rc_file": "~/.zshrc",
        "source_line": 'source ~/.ethscan_complete.zsh',
        "script_path": "~/.ethscan_complete.zsh",
    },
    "fish": {
        "rc_file": "~/.config/fish/config.fish",
        "source_line": "source ~/.config/fish/completions/ethscan.fish",
        "script_path": "~/.config/fish/completions/ethscan.fish",
    },
}


def _expand_path(path: str) -> Path:
    """Expand a path with tilde, using os.path.expanduser for testability."""
    return Path(os.path.expanduser(path))


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


def detect_shell() -> str | None:
    """Detect the current user's shell from the SHELL environment variable.

    Returns the shell name (bash, zsh, fish) if recognized, otherwise None.
    """
    shell_path = os.environ.get("SHELL", "")
    if not shell_path:
        return None
    shell_name = Path(shell_path).name
    if shell_name in _available_shells():
        return shell_name
    return None


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
    cli_obj: click.Command,
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
    cli_obj: click.Command,
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
    if not isinstance(result, dict):
        result = {}
    lines = [
        "# ethscan Shell Completion",
        "",
        f"- **Shell:** {result.get('shell', '')}",
        f"- **Program:** {result.get('prog_name', '')}",
        "",
        "## Script",
        "",
        "```",
        f"{result.get('script', '')}".rstrip(),
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
    if not isinstance(result, dict):
        result = {}
    output = io.StringIO()
    writer = csv_writer(output)

    writer.writerow(["field", "value"])
    writer.writerow(["shell", result.get("shell", "")])
    writer.writerow(["prog_name", result.get("prog_name", "")])
    writer.writerow([])
    writer.writerow(["script"])
    script = result.get("script", "")
    if not isinstance(script, str):
        script = ""
    for line in script.splitlines():
        writer.writerow([line])

    return output.getvalue().rstrip("\r\n")


def install_completion(
    cli_obj: click.Command,
    shell: str | None = None,
    prog_name: str = DEFAULT_PROG_NAME,
) -> dict[str, Any]:
    """Install shell completion for the detected or specified shell.

    Generates the completion script, writes it to the appropriate location,
    and appends a source line to the shell's RC file if not already present.

    Args:
        cli_obj: The click command group to generate completions for.
        shell: Shell to install for (bash, zsh, fish). If None, attempts
            to detect from the SHELL environment variable.
        prog_name: Program name embedded in the completion script.

    Returns:
        A dict with keys: shell, script_path, rc_file, installed (bool),
        already_installed (bool), and message (str).

    Raises:
        ValueError: If the shell is not supported or cannot be detected.
    """
    if shell is None:
        shell = detect_shell()
    if shell is None:
        raise ValueError(
            "Could not detect shell. Please specify with --shell option. "
            f"Supported: {', '.join(available_shells())}"
        )
    if shell not in _SHELL_RC_INFO:
        raise ValueError(
            f"Unsupported shell: {shell}. Supported: "
            f"{', '.join(sorted(_SHELL_RC_INFO))}"
        )

    info = _SHELL_RC_INFO[shell]
    script_path = _expand_path(info["script_path"])
    rc_file = _expand_path(info["rc_file"])
    source_line = info["source_line"]

    # Ensure the script directory exists
    script_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate and write the completion script
    script = generate_completion_script(cli_obj, shell, prog_name)
    script_path.write_text(script)

    # Check if already installed in RC file
    already_installed = False
    if rc_file.exists():
        rc_content = rc_file.read_text()
        if source_line in rc_content:
            already_installed = True

    # Append source line to RC file if not already present
    installed = False
    if not already_installed:
        # Ensure RC file ends with newline
        if rc_file.exists():
            rc_content = rc_file.read_text()
            if rc_content and not rc_content.endswith("\n"):
                rc_file.write_text(rc_content + "\n")
        else:
            rc_file.write_text("")
        with rc_file.open("a") as f:
            f.write(f"\n# ethscan completion\n{source_line}\n")
        installed = True

    return {
        "shell": shell,
        "script_path": str(script_path),
        "rc_file": str(rc_file),
        "installed": installed,
        "already_installed": already_installed,
        "message": (
            f"Completion for {shell} installed successfully."
            if installed
            else f"Completion for {shell} was already installed."
        ),
    }


def format_install_report_json(result: dict[str, Any]) -> str:
    """Render an installation report as JSON."""
    import json

    return json.dumps(result, indent=2, default=str)


def format_install_report_markdown(result: dict[str, Any]) -> str:
    """Render an installation report as Markdown."""
    if not isinstance(result, dict):
        result = {}
    lines = [
        "# ethscan Completion Installation",
        "",
        f"- **Shell:** {result.get('shell', '')}",
        f"- **Script Path:** {result.get('script_path', '')}",
        f"- **RC File:** {result.get('rc_file', '')}",
        f"- **Installed:** {'Yes' if result.get('installed') else 'No'}",
        f"- **Already Installed:** {'Yes' if result.get('already_installed') else 'No'}",
        "",
        "## Message",
        "",
        f"{result.get('message', '')}",
        "",
    ]
    return "\n".join(lines)


def format_install_report_csv(result: dict[str, Any]) -> str:
    """Format installation report as CSV."""
    if not isinstance(result, dict):
        result = {}
    output = io.StringIO()
    writer = csv_writer(output)

    writer.writerow(["field", "value"])
    writer.writerow(["shell", result.get("shell", "")])
    writer.writerow(["script_path", result.get("script_path", "")])
    writer.writerow(["rc_file", result.get("rc_file", "")])
    writer.writerow(["installed", "true" if result.get("installed") else "false"])
    writer.writerow(["already_installed", "true" if result.get("already_installed") else "false"])
    writer.writerow(["message", result.get("message", "")])

    return output.getvalue().rstrip("\r\n")