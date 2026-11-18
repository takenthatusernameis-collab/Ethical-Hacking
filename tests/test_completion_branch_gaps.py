"""Branch-coverage gap tests for the ethscan completion module.

Each test targets a specific partially-covered branch in
``ethscan/completion.py`` that the rest of the suite does not reach. The
gaps are defensive/edge paths that the CLI-level tests cannot hit directly:

* ``detect_shell`` returning ``None`` when ``$SHELL`` is set but names an
  unrecognized shell (the CLI tests only cover an *unset* ``$SHELL``).
* ``install_completion`` raising ``ValueError`` for an explicitly supplied
  unsupported shell. The CLI cannot reach this because ``click.Choice``
  rejects the value first; only a direct caller can.
* ``install_completion`` appending to an RC file that already exists but does
    not yet contain the source line (and does not end in a newline). The
    existing install tests either start with no RC file or with the source line
    already present.
* The non-install ``completion`` command's ``"Shell argument is required when
    not using --install"`` guard (cli.py) is unreachable via the CLI because the
    positional ``SHELL`` argument defaults to ``"bash"`` and is validated by
    ``click.Choice``. Covered by an invariant guard test rather than by
    reaching the branch directly.
"""
from __future__ import annotations

import os
from pathlib import Path

import click
import pytest

from ethscan.completion import (
    _SHELL_RC_INFO,
    DEFAULT_PROG_NAME,
    detect_shell,
    install_completion,
)


def _make_cli() -> click.Command:
    """A minimal click command group to generate completions for."""

    @click.group()
    def grp() -> None:
        pass

    @grp.command()
    @click.option("--target", required=True)
    def scan(target: str) -> None:
        pass

    return grp


def _monkeypatch_home(monkeypatch, fake_home: Path) -> None:
    """Redirect ``~`` expansion to ``fake_home`` for the duration of a test."""
    original_expanduser = os.path.expanduser

    def fake_expanduser(path: str) -> str:
        if path.startswith("~/"):
            return str(fake_home / path[2:])
        if path == "~":
            return str(fake_home)
        return original_expanduser(path)

    monkeypatch.setattr(os.path, "expanduser", fake_expanduser)


def test_detect_shell_returns_none_for_unknown_shell(monkeypatch) -> None:
    """A set-but-unrecognized ``$SHELL`` yields ``None`` (line 77).

    ``install_completion`` relies on this to produce a helpful "specify
    --shell" error instead of silently doing nothing.
    """
    monkeypatch.setenv("SHELL", "/usr/bin/definitely-not-a-supported-shell")
    assert detect_shell() is None


def test_detect_shell_returns_name_for_known_shell(monkeypatch) -> None:
    """A recognized ``$SHELL`` returns its base name (complements the gap above)."""
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert detect_shell() == "zsh"


def test_install_completion_rejects_unsupported_shell_directly() -> None:
    """``install_completion`` raises ``ValueError`` for an unknown shell (line 237).

    The CLI validates ``--shell`` with ``click.Choice`` before this is
    reached, so the direct-call guard is only exercised here.
    """
    with pytest.raises(ValueError, match="Unsupported shell"):
        install_completion(_make_cli(), shell="powershell")


def test_install_completion_appends_to_existing_rc_without_source_line(
    monkeypatch, tmp_path
) -> None:
    """Appending to an existing RC file that lacks the source line.

    Covers the ``source_line not in rc_content`` branch (257->261) together
    with the "existing file without a trailing newline" path (265-267):
    the original content is preserved, a newline is added, then the source
    line is appended.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _monkeypatch_home(monkeypatch, fake_home)

    info = _SHELL_RC_INFO["bash"]
    rc_file = fake_home / ".bashrc"
    original = "export EDITOR=vim"  # deliberately no trailing newline
    rc_file.write_text(original, encoding="utf-8")

    result = install_completion(_make_cli(), shell="bash", prog_name=DEFAULT_PROG_NAME)

    assert result["installed"] is True
    assert result["already_installed"] is False
    assert result["shell"] == "bash"

    rc_text = rc_file.read_text(encoding="utf-8")
    assert rc_text.startswith(original + "\n")
    assert info["source_line"] in rc_text

    script_path = Path(result["script_path"])
    assert script_path.exists()
    assert "_ethscan_completion" in script_path.read_text(encoding="utf-8")


def test_install_completion_preserves_empty_existing_rc(monkeypatch, tmp_path) -> None:
    """An existing but empty RC file (no source line) is appended to.

    Complements the non-empty case above: with empty content the
    "ensure trailing newline" guard (266) is false, so the source line is
    appended directly to the empty file.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _monkeypatch_home(monkeypatch, fake_home)

    info = _SHELL_RC_INFO["zsh"]
    rc_file = fake_home / ".zshrc"
    rc_file.write_text("", encoding="utf-8")

    result = install_completion(_make_cli(), shell="zsh")

    assert result["installed"] is True
    assert result["already_installed"] is False

    rc_text = rc_file.read_text(encoding="utf-8")
    assert info["source_line"] in rc_text


def test_completion_non_install_shell_default_never_raises_usage_error() -> None:
    """The positional SHELL default ("bash") makes the non-install UsageError unreachable.

    The ``completion`` command's positional ``SHELL`` argument defaults to
    ``"bash"`` and is validated by ``click.Choice``, so ``effective_shell`` is
    never ``None`` in non-install mode. This guard test documents that
    invariant: invoking ``completion`` with no shell must succeed and must not
    hit the ``"Shell argument is required when not using --install"`` branch
    (cli.py:4313). A regression that removes the default or makes the argument
    required would surface here as either a different error or a failure.
    """
    from click.testing import CliRunner

    from ethscan.cli import cli

    result = CliRunner().invoke(cli, ["completion"])
    assert result.exit_code == 0, result.output
    assert "_ethscan_completion" in result.output