"""Tests for the ethscan configuration module."""

from typing import Any

import json

import pytest
import yaml
from click.testing import CliRunner

from ethscan import cli
from ethscan.config import (
    CONFIG_CANDIDATES,
    DEFAULT_CONFIG,
    _candidate_paths,
    _merge,
    _parse_set_value,
    _set_nested,
    build_default_map,
    dump_default_config,
    find_config_file,
    format_config_report_csv,
    format_config_report_json,
    format_config_report_markdown,
    load_config,
    save_config,
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


def test_load_config_yaml_that_nests_too_deeply(tmp_path) -> None:
    """A file whose YAML nests deeper than the parser can read is unusable.

    The YAML parser raises a ``RecursionError`` for such a file, which is not
    a ``yaml.YAMLError``: the file is reported as a file that cannot be
    parsed, like a file with broken YAML.
    """
    path = tmp_path / "ethscan.yaml"
    path.write_text("{a: " * 5000 + "1" + "}" * 5000)
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
    # The documented ``format`` key is remapped to the working ``fmt`` Click
    # dest (the deprecated ``--format`` alias) so config-driven output format
    # actually takes effect while still allowing CLI overrides.
    assert dm == {"timeout": 1.0, "workers": 50, "fmt": "json", "ports": "common"}
    dm2 = build_default_map(config, "subdomains")
    assert dm2 == {"timeout": 5.0, "workers": 50, "fmt": "json"}


def test_build_default_map_format_key_remapped_to_fmt() -> None:
    """The documented ``format`` key must reach the working ``fmt`` dest."""
    config = {"defaults": {"format": "markdown"}, "commands": {}}
    assert build_default_map(config, "ping") == {"fmt": "markdown"}


def test_build_default_map_explicit_output_fmt_not_clobbered() -> None:
    """An explicit ``output_fmt`` in config is preserved alongside ``format``."""
    config = {"defaults": {"format": "json", "output_fmt": "markdown"}, "commands": {}}
    assert build_default_map(config, "ping") == {"output_fmt": "markdown", "fmt": "json"}


def test_build_default_map_command_level_format_remapped() -> None:
    config = {"defaults": {}, "commands": {"scan": {"format": "csv"}}}
    assert build_default_map(config, "scan") == {"fmt": "csv"}


def test_build_default_map_empty() -> None:
    assert build_default_map({"defaults": {}, "commands": {}}, "scan") == {}


def test_validate_config_clean() -> None:
    assert validate_config({"defaults": {}, "commands": {}}) == []


def test_validate_config_no_sections() -> None:
    """A config with neither section is valid; there is nothing to check."""
    assert validate_config({}) == []


def test_validate_config_defaults_with_no_known_options() -> None:
    """When no command accepts any option, defaults are left unchecked."""
    warnings = validate_config(
        {"defaults": {"timeout": 5.0}},
        known_commands=[],
        known_options={"scan": set()},
    )
    assert warnings == []


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


def test_validate_config_unknown_option() -> None:
    """A config option that the command does not accept is warned about."""
    warnings = validate_config(
        {"defaults": {}, "commands": {"scan": {"potrs": "common"}}},
        known_commands=["scan"],
        known_options={"scan": {"ports", "profile", "timeout", "workers"}},
    )
    assert any("potrs" in w and "scan" in w for w in warnings)


def test_validate_config_known_option_clean() -> None:
    """A valid config option for a command produces no warning."""
    warnings = validate_config(
        {"defaults": {}, "commands": {"scan": {"ports": "common"}}},
        known_commands=["scan"],
        known_options={"scan": {"ports"}},
    )
    assert warnings == []


def test_validate_config_format_key_counts_as_fmt() -> None:
    """The documented ``format`` key remaps to the ``fmt`` dest and is known."""
    warnings = validate_config(
        {"defaults": {}, "commands": {"cidr": {"format": "json"}}},
        known_commands=["cidr"],
        known_options={"cidr": {"fmt", "output_fmt", "cidr"}},
    )
    assert warnings == []


def test_validate_config_format_key_without_fmt_is_unknown() -> None:
    """If a command does not accept ``fmt``, ``format`` is flagged as unknown."""
    warnings = validate_config(
        {"defaults": {}, "commands": {"cidr": {"format": "json"}}},
        known_commands=["cidr"],
        known_options={"cidr": {"output_fmt"}},
    )
    assert any("format" in w and "cidr" in w for w in warnings)


def test_validate_config_defaults_are_not_option_checked() -> None:
    """Global defaults are not validated against per-command options, so a
    value valid for one command but not another is not flagged as noise."""
    warnings = validate_config(
        {"defaults": {"timeout": 5.0}, "commands": {}},
        known_commands=[],
        known_options={},
    )
    assert warnings == []


def test_validate_config_unknown_default_option() -> None:
    """A typo in global defaults is flagged, because defaults are merged into
    every command's default map and would otherwise be silently ignored."""
    warnings = validate_config(
        {"defaults": {"timeot": 5.0}, "commands": {}},
        known_commands=[],
        known_options={"scan": {"ports", "profile", "timeout", "workers"}},
    )
    assert any("timeot" in w and "defaults" in w for w in warnings)


def test_validate_config_known_default_option_clean() -> None:
    """A default option accepted by at least one command produces no warning."""
    warnings = validate_config(
        {"defaults": {"timeout": 5.0}, "commands": {}},
        known_commands=[],
        known_options={"scan": {"ports", "profile", "timeout", "workers"}},
    )
    assert warnings == []


def test_validate_config_format_key_in_defaults_is_known() -> None:
    """The documented ``format`` key remaps to ``fmt`` and is known in defaults."""
    warnings = validate_config(
        {"defaults": {"format": "markdown"}, "commands": {}},
        known_commands=[],
        known_options={"scan": {"fmt", "output_fmt", "ports"}},
    )
    assert warnings == []


def test_validate_config_with_real_cli_commands() -> None:
    """The real CLI commands are used to validate configured options."""
    known_options: dict[str, set[str]] = {
        name: {param.name for param in command.params if param.name is not None}
        for name, command in cli.cli.commands.items()
    }
    assert "scan" in known_options
    # A valid option for scan produces no warning.
    warnings = validate_config(
        {"defaults": {}, "commands": {"scan": {"ports": "common"}}},
        known_commands=sorted(known_options),
        known_options=known_options,
    )
    assert not any("scan" in w for w in warnings)
    # An unknown option for scan produces a warning.
    warnings = validate_config(
        {"defaults": {}, "commands": {"scan": {"bogus-option": "x"}}},
        known_commands=sorted(known_options),
        known_options=known_options,
    )
    assert any("bogus-option" in w and "scan" in w for w in warnings)
    # An unknown option in global defaults produces a warning too.
    warnings = validate_config(
        {"defaults": {"bogus-default": 1}, "commands": {}},
        known_commands=sorted(known_options),
        known_options=known_options,
    )
    assert any("bogus-default" in w and "defaults" in w for w in warnings)
    # A valid global default produces no warning.
    warnings = validate_config(
        {"defaults": {"timeout": 5.0}, "commands": {}},
        known_commands=sorted(known_options),
        known_options=known_options,
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
    config: dict[str, Any] = {}
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

def test_format_config_report_json_basic() -> None:
    config = {
        "_path": "/etc/ethscan.yaml",
        "defaults": {"timeout": 3.0},
        "commands": {"scan": {"ports": "common"}},
    }
    output = format_config_report_json(config)
    parsed = json.loads(output)
    assert parsed["config_file"] == "/etc/ethscan.yaml"
    assert parsed["defaults"] == {"timeout": 3.0}
    assert parsed["commands"] == {"scan": {"ports": "common"}}
    assert "parse_error" not in parsed

def test_format_config_report_json_with_parse_error() -> None:
    config = {"_parse_error": "Failed to parse"}
    parsed = json.loads(format_config_report_json(config))
    assert parsed["parse_error"] == "Failed to parse"

def test_format_config_report_markdown_includes_notes() -> None:
    """The markdown report ends with a Notes section explaining precedence.

    Regression guard: the refactor that extracted formatting into
    ``format_config_report_markdown`` initially dropped the Notes section that
    the inline CLI code emitted.
    """
    config = {
        "_path": "/etc/ethscan.yaml",
        "defaults": {"timeout": 3.0},
        "commands": {"scan": {"ports": "common"}},
    }
    output = format_config_report_markdown(config)
    assert "# ethscan Configuration" in output
    assert "## Global Defaults" in output
    assert "## Per-Command Overrides" in output
    assert "## Notes" in output
    assert "CLI arguments always take precedence over config values." in output
    assert "ethscan config --init PATH" in output

def test_format_config_report_markdown_no_file_includes_notes() -> None:
    """Notes render even when no config file is found (built-in defaults)."""
    output = format_config_report_markdown({})
    assert "No config file found" in output
    assert "## Notes" in output
    assert "CLI arguments always take precedence over config values." in output

def test_find_config_file_oserror_on_is_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    class BadPath:
        def is_file(self):
            raise OSError("boom")

    monkeypatch.setattr(
        "ethscan.config._candidate_paths",
        lambda explicit=None: [BadPath()],
    )
    assert find_config_file() is None


def test_load_config_oserror_on_open(tmp_path) -> None:
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults: {}\n")
    import builtins

    import ethscan.config as cfg

    original_open = builtins.open

    def bad_open(*args, **kwargs):
        raise OSError("nope")

    builtins.open = bad_open  # type: ignore[assignment]
    try:
        config = cfg.load_config(str(path))
        assert config["defaults"] == {}
        assert config["commands"] == {}
        assert "_path" in config
        assert "_parse_error" in config
        assert "Failed to read" in config["_parse_error"]
    finally:
        builtins.open = original_open  # type: ignore[assignment]


def test_build_default_map_non_dict_overrides(tmp_path) -> None:
    config = {
        "defaults": {"timeout": 5.0},
        "commands": {"scan": [1, 2, 3]},
    }
    dm = build_default_map(config, "scan")
    assert dm == {"timeout": 5.0}


def test_config_path_string_returns_none() -> None:
    from ethscan.config import config_path_string

    assert config_path_string({}) is None
    assert config_path_string({"_path": 123}) is None
    assert config_path_string({"_path": None}) is None



def test_config_path_string_returns_path() -> None:
    from ethscan.config import config_path_string

    assert config_path_string({"_path": "/etc/ethscan.yaml"}) == "/etc/ethscan.yaml"
def test_format_config_report_csv_includes_parse_error(tmp_path) -> None:
    from ethscan.config import format_config_report_csv

    config = {"_parse_error": "bad parse"}
    output = format_config_report_csv(config)
    assert "parse_error" in output
    assert "bad parse" in output


# ---------------------------------------------------------------------------
# CLI-level ``config --init``
# ---------------------------------------------------------------------------


def test_config_cli_init_writes_a_sample_config(tmp_path) -> None:
    """``config --init`` writes a sample config the config loader can read.

    The written file must be valid YAML that ``load_config`` parses into the
    documented schema, so a user can initialize a config and start using it.
    """
    init_path = tmp_path / "ethscan.yaml"
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["config", "--init", str(init_path)])
    assert result.exit_code == 0, result.output
    assert init_path.is_file()
    assert init_path.read_text() == dump_default_config()
    loaded = load_config(str(init_path))
    assert loaded["defaults"] == {"timeout": 5.0, "workers": 50, "format": "json"}
    assert "scan" in loaded["commands"]
    assert "subdomains" in loaded["commands"]


def test_config_cli_init_creates_missing_parent_dirs(tmp_path) -> None:
    """``config --init`` creates the parent directories of the target path.

    ``config --init`` writes through ``write_text``, so a path whose parents do
    not exist yet is still a valid destination.
    """
    init_path = tmp_path / "deep" / "nested" / "ethscan.yaml"
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["config", "--init", str(init_path)])
    assert result.exit_code == 0, result.output
    assert init_path.is_file()
    assert init_path.parent.is_dir()
    assert load_config(str(init_path))["defaults"] == {
        "timeout": 5.0,
        "workers": 50,
        "format": "json",
    }


def test_config_cli_init_refuses_out_together(tmp_path) -> None:
    """``config --init`` and ``--out`` are mutually exclusive.

    ``--init`` writes a sample config and has no report to redirect, so the two
    options cannot be used together and the command reports a usage error
    instead of silently ignoring ``--out``.
    """
    init_path = tmp_path / "ethscan.yaml"
    out_path = tmp_path / "out.txt"
    runner = CliRunner()
    result = runner.invoke(
        cli.cli, ["config", "--init", str(init_path), "--out", str(out_path)]
    )
    assert result.exit_code == 2, result.output
    assert "--init and --out cannot be used together" in result.output
    assert not init_path.is_file()
    assert not out_path.is_file()


def test_candidate_paths_xdg_base_fallback(tmp_path, monkeypatch) -> None:
    """Cover line 94: when XDG_CONFIG_HOME is unset, ~/.config is used."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    paths = _candidate_paths()
    # The XDG candidates are appended relative to tmp_path/.config.
    assert any(p == tmp_path / ".config" / "ethscan/ethscan.yaml" for p in paths)


def test_load_config_yaml_is_none(tmp_path, monkeypatch) -> None:
    """Cover line 135: when PyYAML is not importable, load_config reports it."""
    path = tmp_path / "ethscan.yaml"
    path.write_text("defaults: {}\n")
    import ethscan.config as cfg

    monkeypatch.setattr(cfg, "yaml", None)
    config = cfg.load_config(str(path))
    assert config["defaults"] == {}
    assert config["commands"] == {}
    assert config["_path"] == str(path)
    assert "_parse_error" in config
    assert "PyYAML is required" in config["_parse_error"]


# ---------------------------------------------------------------------------
# ``config --set`` helpers: _parse_set_value / _set_nested / save_config
# ---------------------------------------------------------------------------


def test_parse_set_value_json_scalars() -> None:
    """``--set`` values are parsed as JSON when possible (numbers/bools/null)."""
    assert _parse_set_value("7.5") == 7.5
    assert _parse_set_value("7") == 7
    assert _parse_set_value("true") is True
    assert _parse_set_value("false") is False
    assert _parse_set_value("null") is None


def test_parse_set_value_json_containers() -> None:
    """JSON lists/objects are decoded into real Python containers."""
    assert _parse_set_value('["a", "b"]') == ["a", "b"]
    assert _parse_set_value('{"k": 1}') == {"k": 1}


def test_parse_set_value_string_fallback() -> None:
    """A value that is not valid JSON falls back to the raw string."""
    assert _parse_set_value("common") == "common"
    assert _parse_set_value("") == ""
    assert _parse_set_value("a=b") == "a=b"


def test_set_nested_defaults_scalar() -> None:
    """Setting ``defaults.<key>`` writes a scalar into the defaults section."""
    config: dict[str, Any] = {"defaults": {}, "commands": {}}
    _set_nested(config, "defaults.timeout", 5.0)
    assert config["defaults"] == {"timeout": 5.0}


def test_set_nested_commands_creates_intermediate() -> None:
    """A missing intermediate command section is created on demand."""
    config: dict[str, Any] = {"defaults": {}, "commands": {}}
    _set_nested(config, "commands.scan.ports", "common")
    assert config["commands"] == {"scan": {"ports": "common"}}


def test_set_nested_deep_key() -> None:
    """Dot notation deeper than one level under a command is honored."""
    config: dict[str, Any] = {"defaults": {}, "commands": {}}
    _set_nested(config, "commands.scan.deep.key", "v")
    assert config["commands"] == {"scan": {"deep": {"key": "v"}}}


def test_set_nested_invalid_section_raises() -> None:
    """Only ``defaults`` and ``commands`` are valid top-level sections."""
    config: dict[str, Any] = {"defaults": {}, "commands": {}}
    with pytest.raises(ValueError, match="must be 'defaults' or 'commands'"):
        _set_nested(config, "other.x", 1)


def test_set_nested_requires_two_segments() -> None:
    """A bare section name (``defaults``) is not a settable key."""
    config: dict[str, Any] = {"defaults": {}, "commands": {}}
    with pytest.raises(ValueError, match="section.option"):
        _set_nested(config, "defaults", 99)


def test_set_nested_replaces_non_dict_section() -> None:
    """A non-dict value in the section slot is replaced by a fresh dict."""
    config: dict[str, Any] = {"defaults": 5, "commands": {}}
    _set_nested(config, "defaults.timeout", 3)
    assert config["defaults"] == {"timeout": 3}


def test_set_nested_replaces_non_dict_intermediate() -> None:
    """A non-dict intermediate is replaced so the value is not dropped."""
    config: dict[str, Any] = {"commands": {"scan": "oops"}}
    _set_nested(config, "commands.scan.ports", "common")
    assert config["commands"]["scan"] == {"ports": "common"}


def test_set_nested_preserves_existing_dict_intermediate() -> None:
    """An existing dict intermediate is reused and keeps its other keys."""
    config: dict[str, Any] = {"commands": {"scan": {"existing": 1}}}
    _set_nested(config, "commands.scan.ports", "common")
    assert config["commands"]["scan"] == {"existing": 1, "ports": "common"}


def test_save_config_roundtrip(tmp_path) -> None:
    """A config saved with ``save_config`` loads back identically."""
    path = tmp_path / "out.yaml"
    save_config(
        {"defaults": {"timeout": 5.0}, "commands": {"scan": {"ports": "common"}}},
        str(path),
    )
    loaded = load_config(str(path))
    assert loaded["defaults"] == {"timeout": 5.0}
    assert loaded["commands"] == {"scan": {"ports": "common"}}


def test_save_config_excludes_metadata(tmp_path) -> None:
    """Metadata keys (_path, _parse_error) are never written to disk."""
    path = tmp_path / "out.yaml"
    save_config(
        {
            "defaults": {"timeout": 1},
            "commands": {},
            "_path": "/some/path",
            "_parse_error": "boom",
        },
        str(path),
    )
    text = path.read_text()
    assert "_path" not in text
    assert "_parse_error" not in text
    assert "boom" not in text


def test_save_config_drops_empty_sections(tmp_path) -> None:
    """Empty sections are omitted but the file still loads as empty config."""
    path = tmp_path / "out.yaml"
    save_config({"defaults": {}, "commands": {}}, str(path))
    loaded = load_config(str(path))
    assert loaded["defaults"] == {}
    assert loaded["commands"] == {}


def test_save_config_requires_yaml(tmp_path, monkeypatch) -> None:
    """``save_config`` refuses to write when PyYAML is unavailable."""
    import ethscan.config as cfg

    monkeypatch.setattr(cfg, "yaml", None)
    with pytest.raises(RuntimeError, match="PyYAML is required"):
        cfg.save_config({"defaults": {}, "commands": {}}, str(tmp_path / "x.yaml"))


# ---------------------------------------------------------------------------
# ``config --set`` CLI behaviour
# ---------------------------------------------------------------------------


def _isolate_config_home(monkeypatch, tmp_path) -> None:
    """Pin cwd, home and XDG so config discovery is fully deterministic."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", "")


def test_config_cli_set_creates_config_when_none(monkeypatch, tmp_path) -> None:
    """``--set`` with no existing config writes a new file in the cwd."""
    _isolate_config_home(monkeypatch, tmp_path)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "defaults.timeout=7.5"])
    assert result.exit_code == 0, result.output
    created = tmp_path / "ethscan.yaml"
    assert created.is_file()
    assert load_config(str(created))["defaults"] == {"timeout": 7.5}


def test_config_cli_set_updates_existing_preserves_other_keys(
    monkeypatch, tmp_path
) -> None:
    """``--set`` updates one value and leaves the rest of the file intact."""
    _isolate_config_home(monkeypatch, tmp_path)
    cfg_path = tmp_path / "ethscan.yaml"
    cfg_path.write_text("defaults:\n  timeout: 1\n  workers: 10\n")
    result = CliRunner().invoke(cli.cli, ["config", "--set", "defaults.timeout=9"])
    assert result.exit_code == 0, result.output
    loaded = load_config(str(cfg_path))
    assert loaded["defaults"]["timeout"] == 9
    assert loaded["defaults"]["workers"] == 10


def test_config_cli_set_multiple_values(monkeypatch, tmp_path) -> None:
    """Multiple ``--set`` options are all applied in one invocation."""
    _isolate_config_home(monkeypatch, tmp_path)
    cfg_path = tmp_path / "ethscan.yaml"
    result = CliRunner().invoke(
        cli.cli,
        ["config", "--set", "defaults.timeout=9", "--set", "commands.scan.ports=common"],
    )
    assert result.exit_code == 0, result.output
    loaded = load_config(str(cfg_path))
    assert loaded["defaults"]["timeout"] == 9
    assert loaded["commands"]["scan"]["ports"] == "common"


def test_config_cli_set_invalid_no_equals(monkeypatch, tmp_path) -> None:
    """A ``--set`` value without ``=`` is a usage error and writes nothing."""
    _isolate_config_home(monkeypatch, tmp_path)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "badvalue"])
    assert result.exit_code == 2, result.output
    assert "expected KEY=VALUE format" in result.output
    assert not (tmp_path / "ethscan.yaml").exists()


def test_config_cli_set_invalid_section(monkeypatch, tmp_path) -> None:
    """A ``--set`` key outside defaults/commands is a usage error."""
    _isolate_config_home(monkeypatch, tmp_path)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "other.x=1"])
    assert result.exit_code == 2, result.output
    assert "must be 'defaults' or 'commands'" in result.output


def test_config_cli_set_empty_key(monkeypatch, tmp_path) -> None:
    """A ``--set`` value with an empty key is a usage error."""
    _isolate_config_home(monkeypatch, tmp_path)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "=value"])
    assert result.exit_code == 2, result.output
    assert "empty key" in result.output


def test_config_cli_set_and_init_mutually_exclusive(tmp_path) -> None:
    """``--init`` and ``--set`` cannot be combined."""
    init_path = tmp_path / "init.yaml"
    result = CliRunner().invoke(
        cli.cli,
        ["config", "--init", str(init_path), "--set", "defaults.timeout=1"],
    )
    assert result.exit_code == 2, result.output
    assert "--init and --set cannot be used together" in result.output
    assert not init_path.is_file()


def test_config_cli_set_refuses_unparseable_config(monkeypatch, tmp_path) -> None:
    """``--set`` refuses to overwrite a config file it cannot parse.

    Overwriting would silently discard the file's (unparseable) contents, so the
    command must fail as a usage error and leave the file byte-for-byte intact.
    """
    _isolate_config_home(monkeypatch, tmp_path)
    bad = tmp_path / "ethscan.yaml"
    original = "defaults: [unclosed\n"
    bad.write_text(original)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "defaults.timeout=3"])
    assert result.exit_code == 2, result.output
    assert "could not be parsed" in result.output
    assert bad.read_text() == original


def test_config_cli_set_respects_config_path(tmp_path) -> None:
    """``--set`` writes back to the file named by ``--config``."""
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text("defaults:\n  timeout: 1\n")
    result = CliRunner().invoke(
        cli.cli,
        ["config", "--config", str(cfg_path), "--set", "defaults.timeout=4"],
    )
    assert result.exit_code == 0, result.output
    assert load_config(str(cfg_path))["defaults"]["timeout"] == 4


def test_config_cli_set_output_reflects_new_value(monkeypatch, tmp_path) -> None:
    """The JSON report printed after ``--set`` shows the new value, no error."""
    _isolate_config_home(monkeypatch, tmp_path)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "defaults.timeout=7.5"])
    assert result.exit_code == 0, result.output
    assert '"timeout": 7.5' in result.output
    assert "parse_error" not in result.output


def test_config_cli_set_reports_write_failure(monkeypatch, tmp_path) -> None:
    """A failing write is reported as a usage error, not a traceback."""
    _isolate_config_home(monkeypatch, tmp_path)
    import ethscan.config as cfg

    def boom(config: dict[str, Any], path: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cfg, "save_config", boom)
    result = CliRunner().invoke(cli.cli, ["config", "--set", "defaults.timeout=3"])
    assert result.exit_code == 2, result.output
    assert "Failed to write config" in result.output
    assert not (tmp_path / "ethscan.yaml").exists()


def test_config_cli_set_missing_config_path_is_usage_error(tmp_path) -> None:
    """A non-existent ``--config`` path stays a usage error even with ``--set``."""
    missing = tmp_path / "nope.yaml"
    result = CliRunner().invoke(
        cli.cli,
        ["config", "--config", str(missing), "--set", "defaults.timeout=4"],
    )
    assert result.exit_code == 2, result.output
    assert "does not exist" in result.output
    assert not missing.exists()


def test_config_cli_set_with_out_writes_report(tmp_path) -> None:
    """``--out`` redirects the post-``--set`` report to a file."""
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text("defaults:\n  timeout: 1\n")
    out_path = tmp_path / "report.json"
    result = CliRunner().invoke(
        cli.cli,
        [
            "config",
            "--config",
            str(cfg_path),
            "--set",
            "defaults.timeout=4",
            "--format",
            "json",
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists()
    import json

    payload = json.loads(out_path.read_text())
    assert payload["defaults"]["timeout"] == 4
    assert payload["config_file"] == str(cfg_path)


def test_config_cli_set_format_csv_reflects_new_value(tmp_path) -> None:
    """CSV output after ``--set`` reflects the updated value."""
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text("defaults:\n  timeout: 1\n")
    result = CliRunner().invoke(
        cli.cli,
        ["config", "--config", str(cfg_path), "--set", "defaults.timeout=9", "--format", "csv"],
    )
    assert result.exit_code == 0, result.output
    assert "9" in result.output
