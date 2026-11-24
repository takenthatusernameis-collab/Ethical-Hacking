"""Tests for the version module."""

from __future__ import annotations

import subprocess
import sys
from importlib import metadata

from unittest.mock import MagicMock

from ethscan.version import (
    _collect_version_data,
    _get_git_info,
    format_version_report_csv,
    format_version_report_json,
    format_version_report_markdown,
    get_version_data,
)


def test_collect_version_data_structure():
    """Test that version data has the expected structure."""
    data = _collect_version_data()
    assert isinstance(data, dict)
    assert "version" in data
    assert "python" in data
    assert "platform" in data
    assert "architecture" in data
    assert "dependencies" in data
    assert "config_file" in data
    assert "cache_directory" in data
    assert isinstance(data["dependencies"], dict)
    assert "click" in data["dependencies"]
    assert "pyyaml" in data["dependencies"]
    assert "dnspython" in data["dependencies"]


def test_collect_version_data_git_info():
    """Test that git info is included when available."""
    data = _collect_version_data()
    # Git info may or may not be available depending on environment
    if "git" in data:
        git_info = data["git"]
        assert isinstance(git_info, dict)
        assert "commit" in git_info
        assert "commit_date" in git_info
        assert len(git_info["commit"]) == 40  # Full SHA-1 hash
        assert git_info["commit_date"]


def test_format_version_report_json():
    """Test JSON formatter."""
    data = _collect_version_data()
    output = format_version_report_json(data)
    assert output.startswith("{")
    assert output.endswith("\n")
    assert '"version":' in output
    assert '"python":' in output


def test_format_version_report_markdown():
    """Test Markdown formatter."""
    data = _collect_version_data()
    output = format_version_report_markdown(data)
    assert output.startswith("# ethscan Version Report")
    assert "**Version:**" in output
    assert "## Dependencies" in output
    assert "## Configuration" in output
    # Git section may or may not be present
    if "git" in data:
        assert "## Git" in output
        assert "**Commit:**" in output
        assert "**Commit Date:**" in output


def test_format_version_report_csv():
    """Test CSV formatter."""
    data = _collect_version_data()
    output = format_version_report_csv(data)
    lines = output.strip().splitlines()
    assert lines[0] == "key,value"
    # Check for required fields
    keys = {line.split(",")[0] for line in lines[1:]}
    assert "version" in keys
    assert "python" in keys
    assert "platform" in keys
    assert "architecture" in keys
    assert "config_file" in keys
    assert "cache_directory" in keys
    # Git fields may or may not be present
    if "git" in data:
        assert "git.commit" in keys
        assert "git.commit_date" in keys


def test_formatters_handle_hostile_input():
    """Test that formatters handle hostile input gracefully."""
    # All formatters should handle non-dict input
    for formatter in [format_version_report_json, format_version_report_markdown, format_version_report_csv]:
        result = formatter("not a dict")
        assert isinstance(result, str)
        assert result != ""

    result = formatter(None)
    assert isinstance(result, str)
    assert result != ""

    result = formatter([1, 2, 3])
    assert isinstance(result, str)
    assert result != ""


def test_get_version_data_returns_collect_result():
    """Test that get_version_data delegates to _collect_version_data."""
    data = get_version_data()
    assert isinstance(data, dict)
    assert "version" in data


def test_get_git_info_nonzero_returncode_omits_commit(monkeypatch):
    """Nonzero git return code omits the commit key."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = "deadbeef"
    monkeypatch.setattr("ethscan.version.subprocess.run", lambda *a, **k: mock_result)
    info = _get_git_info()
    assert "commit" not in info


def test_get_git_info_nonzero_returncode_omits_commit_date(monkeypatch):
    """Nonzero git return code omits the commit_date key."""
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stdout = "2024-01-01"
    monkeypatch.setattr("ethscan.version.subprocess.run", lambda *a, **k: mock_result)
    info = _get_git_info()
    assert "commit_date" not in info


def test_get_git_info_subprocess_error_omits_commit(monkeypatch):
    """subprocess.SubprocessError is swallowed and commit is omitted."""
    def _raise(*a, **k):
        raise subprocess.SubprocessError("boom")
    monkeypatch.setattr("ethscan.version.subprocess.run", _raise)
    info = _get_git_info()
    assert "commit" not in info
    assert "commit_date" not in info


def test_get_git_info_oserror_omits_commit(monkeypatch):
    """OSError is swallowed and commit is omitted."""
    def _raise(*a, **k):
        raise OSError("no git")
    monkeypatch.setattr("ethscan.version.subprocess.run", _raise)
    info = _get_git_info()
    assert "commit" not in info
    assert "commit_date" not in info


def test_collect_version_data_omits_git_key_when_empty(monkeypatch):
    """Empty git info omits the git key from version data."""
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert "git" not in data


def test_collect_version_data_includes_git_when_present(monkeypatch):
    """Non-empty git info includes the git key."""
    monkeypatch.setattr(
        "ethscan.version._get_git_info",
        lambda: {"commit": "abc", "commit_date": "2024"},
    )
    data = _collect_version_data()
    assert data["git"] == {"commit": "abc", "commit_date": "2024"}


def test_collect_version_data_click_package_not_found(monkeypatch):
    """click package metadata missing falls back to 'unknown'."""
    def _raise(*a, **k):
        raise metadata.PackageNotFoundError("click")
    monkeypatch.setattr("ethscan.version.metadata.version", _raise)
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert data["dependencies"]["click"] == "unknown"


def test_collect_version_data_click_version_matches_metadata(monkeypatch):
    """click version is read from package metadata, not the deprecated __version__."""
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert data["dependencies"]["click"] == metadata.version("click")


def test_collect_version_data_yaml_import_error(monkeypatch):
    """yaml ImportError falls back to 'unknown'."""
    monkeypatch.setitem(sys.modules, "yaml", None)
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert data["dependencies"]["pyyaml"] == "unknown"


def test_collect_version_data_dns_not_installed(monkeypatch):
    """dns ImportError falls back to 'not installed'."""
    monkeypatch.setitem(sys.modules, "dns", None)
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert data["dependencies"]["dnspython"] == "not installed"


def test_collect_version_data_dns_attribute_error(monkeypatch):
    """dns without __version__ falls back to 'not installed'."""
    module = MagicMock(spec=[])  # no __version__ attribute
    monkeypatch.setitem(sys.modules, "dns", module)
    monkeypatch.setattr("ethscan.version._get_git_info", lambda: {})
    data = _collect_version_data()
    assert data["dependencies"]["dnspython"] == "not installed"


def test_format_version_report_json_handles_empty_git():
    """JSON formatter omits git when absent."""
    data = _collect_version_data()
    data.pop("git", None)
    output = format_version_report_json(data)
    assert '"git"' not in output


def test_format_version_report_csv_handles_empty_git():
    """CSV formatter omits git rows when absent."""
    data = _collect_version_data()
    data.pop("git", None)
    output = format_version_report_csv(data)
    assert "git.commit" not in output
    assert "git.commit_date" not in output


def test_format_version_report_markdown_handles_empty_git():
    """Markdown formatter omits Git section when absent."""
    data = _collect_version_data()
    data.pop("git", None)
    output = format_version_report_markdown(data)
    assert "## Git" not in output
