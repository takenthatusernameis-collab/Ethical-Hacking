"""Tests for the ethscan configuration module."""

import json

import pytest
import yaml

from ethscan.config import (
    CONFIG_CANDIDATES,
    DEFAULT_CONFIG,
    _candidate_paths,
    _merge,
    build_default_map,
    dump_default_config,
    find_config_file,
    format_config_report_csv,
    load_config,
    validate_config,
)


def test_default_config_shape() -> None:
    assert DEFAULT_CONFIG == {"defaults": {}, "commands": {}}


def test_candidate_paths_explicit_first(tmp_path) -> None:
    explicit = tmp_path / "explicit.yaml"
    paths = _candidate_paths(str(explicit))
    assert paths[0] == explicit
    assert CONFIG_CANDIDATES[0] in [str(p) for p in paths[1:]]


def test_find_config_file_none(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    assert find_config_file() is None


def test_find_config_file_explicit(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults: {}\n")
    assert find_config_file(str(path)) == path


def test_find_config_file_cwd(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / "ethscan.yaml").write_text("defaults: {}\n")
    found = find_config_file()
    assert found is not None
    assert found.name == "ethscan.yaml"


def test_find_config_file_home(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".ethscan.yaml").write_text("defaults: {}\n")
    found = find_config_file()
    assert found is not None
    assert found.name == ".ethscan.yaml"


def test_load_config_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    config = load_config()
    assert config == {"defaults": {}, "commands": {}}


def test_load_config_explicit(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults:\n  timeout: 5.0\ncommands:\n  scan:\n    ports: common\n")
    config = load_config(str(path))
    assert config["defaults"] == {"timeout": 5.0}
    assert config["commands"] == {"scan": {"ports": "common"}}
    assert config["_path"] == str(path)


def test_load_config_invalid_yaml(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("{{{\n")
    config = load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}
    assert "_parse_error" in config
    assert "Failed to parse" in config["_parse_error"]


def test_load_config_non_dict_root(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("- a\n- b\n")
    config = load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}
    assert "_parse_error" in config


def test_load_config_defaults_not_dict(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults: [1, 2]\ncommands: {}\n")
    config = load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}


def test_load_config_commands_not_dict(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults: {}\ncommands: [1, 2]\n")
    config = load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}


def test_load_config_missing_keys_filled(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("timeout: 5.0\n")
    config = load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}


def test_merge_global_and_command() -> None:
    merged = _merge({"timeout": 5.0, "workers": 50}, {"timeout": 1.0})
    assert merged == {"timeout": 1.0, "workers": 50}


def test_build_default_map_merges() -> None:
    config = {
        "defaults": {"timeout": 5.0, "workers": 50, "format": "json"},
        "commands": {"scan": {"timeout": 1.0, "ports": "common"}},
    }
    dm = build_default_map(config, "scan")
    assert dm == {"timeout": 1.0, "workers": 50, "format": "json", "ports": "common"}
    dm2 = build_default_map(config, "subdomains")
    assert dm2 == {"timeout": 5.0, "workers": 50, "format": "json"}


def test_build_default_map_empty() -> None:
    assert build_default_map({"defaults": {}, "commands": {}}, "scan") == {}


def test_validate_config_clean() -> None:
    assert validate_config({"defaults": {}, "commands": {}}) == []


def test_validate_config_parse_error() -> None:
    cfg = {"defaults": {}, "commands": {}, "_parse_error": "boom"}
    warnings = validate_config(cfg)
    assert len(warnings) == 1
    assert "boom" in warnings[0]


def test_validate_config_defaults_not_dict() -> None:
    warnings = validate_config({"defaults": [1], "commands": {}})
    assert any("defaults" in w for w in warnings)


def test_validate_config_commands_not_dict() -> None:
    warnings = validate_config({"defaults": {}, "commands": [1]})
    assert any("commands" in w for w in warnings)


def test_validate_config_command_opts_not_dict() -> None:
    warnings = validate_config({"defaults": {}, "commands": {"scan": [1]}})
    assert any("scan" in w for w in warnings)


def test_validate_config_unknown_command() -> None:
    warnings = validate_config(
        {"defaults": {}, "commands": {"nonexistentcmd": {"foo": "bar"}}},
        known_commands=["scan"],
    )
    assert any("nonexistentcmd" in w for w in warnings)


def test_validate_config_known_command_clean() -> None:
    warnings = validate_config(
        {"defaults": {}, "commands": {"scan": {"ports": "common"}}},
        known_commands=["scan"],
    )
    assert warnings == []


def test_dump_default_config_is_yaml() -> None:
    sample = dump_default_config()
    parsed = yaml.safe_load(sample)
    assert isinstance(parsed, dict)
    assert "defaults" in parsed
    assert "commands" in parsed
    assert parsed["defaults"]["timeout"] == 5.0
    assert "scan" in parsed["commands"]
    assert "subdomains" in parsed["commands"]


def test_dump_default_config_has_comments() -> None:
    sample = dump_default_config()
    assert "# Global defaults" in sample
    assert "# Per-command overrides" in sample


# ---------------------------------------------------------------------------
# CSV formatter
# ---------------------------------------------------------------------------


def test_format_config_report_csv_basic() -> None:
    config = {
        "_path": "/etc/ethscan.yaml",
        "_parse_error": None,
        "defaults": {"timeout": 3.0, "workers": 50},
        "commands": {
            "scan": {"timeout": 5.0},
            "subdomains": {"workers": 100},
        },
    }
    output = format_config_report_csv(config)
    lines = output.splitlines()
    assert lines[0] == "section,option,value"
    assert "config,path,/etc/ethscan.yaml" in lines
    assert "defaults,timeout,3.0" in lines
    assert "defaults,workers,50" in lines
    assert "commands.scan,timeout,5.0" in lines
    assert "commands.subdomains,workers,100" in lines


def test_format_config_report_csv_empty() -> None:
    config = {}
    output = format_config_report_csv(config)
    lines = output.splitlines()
    assert lines[0] == "section,option,value"
    assert len(lines) == 1


def test_format_config_report_csv_missing_fields() -> None:
    config = {"_path": "/cfg.yaml"}
    output = format_config_report_csv(config)
    lines = output.splitlines()
    assert lines[0] == "section,option,value"
    assert "config,path,/cfg.yaml" in lines


def test_format_config_report_csv_escaping() -> None:
    config = {
        "defaults": {"note": "Hello, World"},
        "commands": {"scan": {"comment": "value, with, commas"}},
    }
    output = format_config_report_csv(config)
    assert '"Hello, World"' in output