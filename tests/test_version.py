"""Tests for the version module."""

from __future__ import annotations

from ethscan.version import _collect_version_data, format_version_report_json, format_version_report_markdown, format_version_report_csv


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
