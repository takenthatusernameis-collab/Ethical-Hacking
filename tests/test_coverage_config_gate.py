"""Regression guard keeping the 100% coverage gate genuinely enforced.

coverage.py only reads the ``[tool.coverage.run]`` and
``[tool.coverage.report]`` subsections of ``pyproject.toml``. The project
claims 100% coverage, but for a long time ``fail_under``, ``source`` and
``exclude_lines`` were placed directly under ``[tool.coverage]``, where
coverage silently ignored them: ``coverage debug config`` reported
``fail_under: 0.0`` and no ``source``, so the gate never actually ran. That
regression was invisible because nothing in the suite checked it.

This module turns the invariant into a permanent, deterministic test. It asks
coverage itself for its *resolved* configuration (``coverage debug config``)
rather than scraping the TOML, so it catches the exact inert-config failure
mode no matter how the file is (mis)structured. If the gate is ever disabled
again -- keys moved back to the top level, ``fail_under`` lowered, or
``source`` dropped -- this test fails instead of the guarantee silently
disappearing.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# The repository root: coverage resolves its config relative to the working
# directory, so the check must run from here regardless of where pytest was
# invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolved_coverage_config() -> str:
    """Return the authoritative, resolved coverage configuration as text.

    ``coverage debug config`` prints the configuration coverage.py actually
    uses after merging every discovered config file. Parsing that output (as
    opposed to the raw TOML) means the test observes the same values coverage
    will enforce, so a misplaced key cannot hide.
    """
    pytest.importorskip("coverage")
    proc = subprocess.run(
        [sys.executable, "-m", "coverage", "debug", "config"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "could not read the resolved coverage configuration:\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return proc.stdout


def _scalar(config_text: str, key: str) -> str | None:
    """Extract a single-value ``key: value`` line from the config dump.

    Only matches a bare ``key:`` token (letters/underscores immediately
    followed by a colon), so indented continuation values such as
    ``pragma: no cover`` or ``if TYPE_CHECKING:`` are never mistaken for keys.
    """
    match = re.search(rf"^\s*{re.escape(key)}:\s?(.*)$", config_text, re.MULTILINE)
    return match.group(1).strip() if match else None


def test_coverage_config_parser_is_not_vacuous() -> None:
    """Guard the parser: a broken parse must fail loudly, not pass silently."""
    config_text = _resolved_coverage_config()
    assert config_text.strip(), "coverage debug config produced no output"
    # The dump always reports the config file it read; if this is missing the
    # output format changed and the assertions below would be meaningless.
    config_file = _scalar(config_text, "config_file")
    assert config_file, (
        "could not find a 'config_file:' entry in the coverage config dump; "
        "the parser or the coverage output format has changed"
    )
    assert config_file.endswith("pyproject.toml"), (
        f"coverage is not reading pyproject.toml (config_file={config_file!r}); "
        "the gate would be checking the wrong configuration"
    )
    # The keys the gate depends on must be present at all.
    assert _scalar(config_text, "source") is not None
    assert _scalar(config_text, "fail_under") is not None


def test_coverage_source_includes_ethscan() -> None:
    """coverage must measure the ``ethscan`` package, or 100% is meaningless."""
    config_text = _resolved_coverage_config()
    source = _scalar(config_text, "source")
    assert source, (
        "coverage has no 'source' configured; the 100% gate would measure "
        "nothing. Set source = [\"ethscan\"] under [tool.coverage.run]."
    )
    assert "ethscan" in source, (
        f"coverage source does not include 'ethscan' (source={source!r}); "
        "set source = [\"ethscan\"] under [tool.coverage.run]"
    )


def test_coverage_fail_under_is_one_hundred() -> None:
    """The gate must fail below 100%, so ``fail_under`` has to be 100."""
    config_text = _resolved_coverage_config()
    raw = _scalar(config_text, "fail_under")
    assert raw is not None, "coverage config has no 'fail_under' value"
    try:
        fail_under = float(raw)
    except ValueError:  # pragma: no cover - defensive against format drift
        pytest.fail(f"could not parse fail_under={raw!r} as a number")
    assert fail_under == 100.0, (
        f"coverage fail_under is {fail_under}, not 100; the 100% gate is "
        "disabled. Set fail_under = 100 under [tool.coverage.report]."
    )


def test_coverage_excludes_type_checking_block() -> None:
    """The statically-unreachable ``if TYPE_CHECKING:`` imports stay excluded.

    Two runtime-unreachable ``from typing import NotRequired`` lines guarded by
    ``if TYPE_CHECKING:`` (ethscan/cidr.py, ethscan/radix.py) are excluded from
    coverage by the canonical idiom. Without this exclusion the now-real gate
    would fail on lines that can never execute at runtime.
    """
    config_text = _resolved_coverage_config()
    assert "if TYPE_CHECKING:" in config_text, (
        "the 'if TYPE_CHECKING:' exclusion is missing from the coverage "
        "config; the 100% gate would fail on statically-unreachable imports. "
        "Add it to exclude_lines under [tool.coverage.report]."
    )