"""Tests for the ethscan completion module."""

from unittest.mock import MagicMock

import click
import pytest

from ethscan.completion import (
    DEFAULT_PROG_NAME,
    _available_shells,
    _completion_class_for,
    available_shells,
    generate_completion_script,
    run_completion,
    format_completion_report_json,
    format_completion_report_markdown,
)


# ---------------------------------------------------------------------------
# Public API helpers
# ---------------------------------------------------------------------------


def test_available_shells_returns_dict() -> None:
    shells = _available_shells()
    assert isinstance(shells, dict)
    assert "bash" in shells
    assert "zsh" in shells
    assert "fish" in shells


def test_available_shells_returns_tuple() -> None:
    shells = available_shells()
    assert isinstance(shells, tuple)
    assert "bash" in shells
    assert "zsh" in shells
    assert "fish" in shells


def test_default_prog_name_constant() -> None:
    assert DEFAULT_PROG_NAME == "ethscan"


# ---------------------------------------------------------------------------
# _completion_class_for
# ---------------------------------------------------------------------------


def test_completion_class_for_bash() -> None:
    from click.shell_completion import BashComplete

    assert _completion_class_for("bash") is BashComplete


def test_completion_class_for_zsh() -> None:
    from click.shell_completion import ZshComplete

    assert _completion_class_for("zsh") is ZshComplete


def test_completion_class_for_fish() -> None:
    from click.shell_completion import FishComplete

    assert _completion_class_for("fish") is FishComplete


def test_completion_class_for_unknown_raises() -> None:
    with pytest.raises(ValueError):
        _completion_class_for("powershell")


# ---------------------------------------------------------------------------
# generate_completion_script
# ---------------------------------------------------------------------------


def _make_cli() -> click.BaseCommand:
    @click.group()
    def grp() -> None:
        pass

    @grp.command()
    @click.option("--target", required=True)
    def scan(target: str) -> None:
        pass

    return grp


def test_generate_completion_script_bash() -> None:
    cli_obj = _make_cli()
    script = generate_completion_script(cli_obj, "bash")
    assert "_ethscan_completion()" in script
    assert "_ethscan_completion_setup" in script
    assert "complete -o nosort -F" in script


def test_generate_completion_script_zsh() -> None:
    cli_obj = _make_cli()
    script = generate_completion_script(cli_obj, "zsh")
    assert "#compdef ethscan" in script
    assert "compdef" in script


def test_generate_completion_script_fish() -> None:
    cli_obj = _make_cli()
    script = generate_completion_script(cli_obj, "fish")
    assert "function _ethscan_completion" in script
    assert "complete --no-files" in script


def test_generate_completion_script_custom_prog_name() -> None:
    cli_obj = _make_cli()
    script = generate_completion_script(cli_obj, "bash", prog_name="mytool")
    assert "mytool" in script
    assert "_mytool_completion" in script


def test_generate_completion_script_invalid_shell_raises() -> None:
    cli_obj = _make_cli()
    with pytest.raises(ValueError):
        generate_completion_script(cli_obj, "invalid")


# ---------------------------------------------------------------------------
# run_completion
# ---------------------------------------------------------------------------


def test_run_completion_bash() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "bash")
    assert result["shell"] == "bash"
    assert result["prog_name"] == DEFAULT_PROG_NAME
    assert "_ethscan_completion" in result["script"]


def test_run_completion_custom_prog_name() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "bash", prog_name="custom")
    assert result["prog_name"] == "custom"
    assert "_custom_completion" in result["script"]


def test_run_completion_invalid_shell_raises() -> None:
    cli_obj = _make_cli()
    with pytest.raises(ValueError):
        run_completion(cli_obj, "invalid")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_format_completion_report_json() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "bash")
    output = format_completion_report_json(result)
    import json

    parsed = json.loads(output)
    assert parsed["shell"] == "bash"
    assert parsed["prog_name"] == "ethscan"
    assert "_ethscan_completion" in parsed["script"]


def test_format_completion_report_json_custom_prog() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "bash", prog_name="mytool")
    output = format_completion_report_json(result)
    import json

    parsed = json.loads(output)
    assert parsed["prog_name"] == "mytool"


def test_format_completion_report_markdown_bash() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "bash")
    output = format_completion_report_markdown(result)
    assert "ethscan Shell Completion" in output
    assert "bash" in output
    assert "_ethscan_completion" in output
    assert "Installation" in output


def test_format_completion_report_markdown_zsh() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "zsh")
    output = format_completion_report_markdown(result)
    assert "zsh" in output
    assert "#compdef ethscan" in output


def test_format_completion_report_markdown_fish() -> None:
    cli_obj = _make_cli()
    result = run_completion(cli_obj, "fish")
    output = format_completion_report_markdown(result)
    assert "fish" in output
    assert "function _ethscan_completion" in output