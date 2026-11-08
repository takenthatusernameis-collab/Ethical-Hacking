"""Tests for the ethscan completion module."""


import click
import pytest
from click.testing import CliRunner

from ethscan.cli import cli
from ethscan.completion import (
    DEFAULT_PROG_NAME,
    _available_shells,
    _completion_class_for,
    available_shells,
    format_completion_report_csv,
    format_completion_report_json,
    format_completion_report_markdown,
    generate_completion_script,
    run_completion,
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


@pytest.mark.parametrize("prog_name", ["my-tool", "my.tool", "my-tool.v2"])
@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_generate_completion_script_uses_click_env_var_name(
    prog_name: str, shell: str
) -> None:
    """The completion env var must match the one click's runtime reads.

    Click derives the variable at runtime by replacing ``-`` and ``.`` with
    ``_`` before upper-casing (``click/core.py``).  A script that sets
    ``_MY-TOOL_COMPLETE`` can therefore never be triggered, so the emitted
    completion is dead code for any hyphenated or dotted program name.
    """
    cli_obj = _make_cli()
    script = generate_completion_script(cli_obj, shell, prog_name=prog_name)
    sanitized = prog_name.replace("-", "_").replace(".", "_")
    expected_var = f"_{sanitized.upper()}_COMPLETE"
    assert expected_var in script
    assert f"_{prog_name.upper()}_COMPLETE" not in script


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


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_completion_report_csv_basic() -> None:
    result = {
        "shell": "bash",
        "prog_name": "ethscan",
        "script": "# bash completion\ncomplete -o default -F _ethscan_completion ethscan",
    }
    output = format_completion_report_csv(result)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "shell,bash" in lines
    assert "prog_name,ethscan" in lines
    assert lines[4] == "script"
    assert "# bash completion" in lines[5]
    assert "complete -o default -F _ethscan_completion ethscan" in lines[6]


def test_format_completion_report_csv_empty() -> None:
    result: dict[str, str] = {"shell": "bash", "prog_name": "ethscan", "script": ""}
    output = format_completion_report_csv(result)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "shell,bash" in lines
    assert "prog_name,ethscan" in lines


def test_format_completion_report_csv_missing_fields() -> None:
    result: dict[str, str] = {}
    output = format_completion_report_csv(result)
    lines = output.splitlines()
    assert lines[0] == "field,value"
    assert "shell," in lines
    assert "prog_name," in lines


def test_format_completion_report_csv_escaping() -> None:
    result: dict[str, str] = {
        "shell": "bash",
        "prog_name": "ethscan",
        "script": "line,with,commas\nsecond,line",
    }
    output = format_completion_report_csv(result)
    assert '"line,with,commas"' in output


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


def _run_completion_cli(args: list):
    return CliRunner().invoke(cli, ["completion"] + args)


def test_completion_cli_positional_bash() -> None:
    """The documented `ethscan completion bash` form emits the raw bash script."""
    result = _run_completion_cli(["bash"])
    assert result.exit_code == 0, result.output
    assert "_ethscan_completion()" in result.output
    assert not result.output.lstrip().startswith("{")


def test_completion_cli_positional_zsh() -> None:
    result = _run_completion_cli(["zsh"])
    assert result.exit_code == 0, result.output
    assert "#compdef ethscan" in result.output
    assert not result.output.lstrip().startswith("{")


def test_completion_cli_positional_fish() -> None:
    result = _run_completion_cli(["fish"])
    assert result.exit_code == 0, result.output
    assert "function _ethscan_completion" in result.output
    assert not result.output.lstrip().startswith("{")


def test_completion_cli_default_shell() -> None:
    result = _run_completion_cli([])
    assert result.exit_code == 0, result.output
    assert "_ethscan_completion()" in result.output
    assert not result.output.lstrip().startswith("{")


def test_completion_cli_option_still_works() -> None:
    result = _run_completion_cli(["--shell", "zsh"])
    assert result.exit_code == 0, result.output
    assert "#compdef ethscan" in result.output


def test_completion_cli_option_overrides_positional() -> None:
    result = _run_completion_cli(["bash", "--shell", "zsh"])
    assert result.exit_code == 0, result.output
    assert "#compdef ethscan" in result.output


def test_completion_cli_invalid_shell_errors() -> None:
    result = _run_completion_cli(["powershell"])
    assert result.exit_code != 0
def test_completion_cli_output_format_json() -> None:
    result = _run_completion_cli(["bash", "--output-format", "json"])
    assert result.exit_code == 0, result.output
    assert '"shell": "bash"' in result.output
    assert '"script":' in result.output


def test_completion_cli_output_format_markdown() -> None:
    result = _run_completion_cli(["bash", "--output-format", "markdown"])
    assert result.exit_code == 0, result.output
    assert "ethscan Shell Completion" in result.output
    assert "## Script" in result.output


def test_completion_cli_output_format_csv() -> None:
    result = _run_completion_cli(["bash", "--output-format", "csv"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[0] == "field,value"
    assert "shell,bash" in result.output


def test_completion_cli_deprecated_format_still_produces_report() -> None:
    result = _run_completion_cli(["bash", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert '"shell": "bash"' in result.output


def test_completion_cli_out_writes_raw_script(tmp_path) -> None:
    out = tmp_path / "comp.bash"
    result = _run_completion_cli(["bash", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "Completion script written" in result.output
    content = out.read_text(encoding="utf-8")
    assert "_ethscan_completion()" in content
    assert not content.lstrip().startswith("{")


def test_completion_cli_out_with_output_format_writes_report(tmp_path) -> None:
    out = tmp_path / "comp.json"
    result = _run_completion_cli(["bash", "--output-format", "json", "--out", str(out)])
    assert result.exit_code == 0, result.output
    import json

    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["shell"] == "bash"
    assert "_ethscan_completion" in parsed["script"]
