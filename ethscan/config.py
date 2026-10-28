"""Configuration file support for ethscan.

Loads an optional ``ethscan.yaml`` configuration file that persists default
options across commands. The file may live in the current working directory
(``ethscan.yaml``), in the user's home directory (``~/.ethscan.yaml``),
or in the XDG Base Directory (``$XDG_CONFIG_HOME/ethscan/`` or
``~/.config/ethscan/``).

The YAML schema is::

    # Global defaults applied to every command
    defaults:
      timeout: 5.0
      workers: 50
      format: json

    # Per-command overrides (keys are Click option dest names)
    commands:
      scan:
        ports: common
        profile: normal
        timeout: 1.0
        workers: 100
      subdomains:
        timeout: 3.0
        resolver: 8.8.8.8

Only options explicitly listed in the config take effect; CLI arguments always
take precedence over config values. The config is purely optional and the
toolkit works unchanged when no config file is present.
"""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any

from ethscan.fileio import read_text

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml is a declared dependency
    yaml = None  # type: ignore

# Candidate locations searched in order. The first existing file wins.
# Evaluated lazily (see ``_candidate_paths``) so that ``Path.home()`` reflects
# the current environment (useful for tests that monkeypatch the home dir).
CONFIG_CANDIDATES: list[str] = [
    "ethscan.yaml",
    "ethscan.yml",
    ".ethscan.yaml",
    ".ethscan.yml",
]

XDG_CONFIG_CANDIDATES: list[str] = [
    "ethscan/ethscan.yaml",
    "ethscan/ethscan.yml",
    "ethscan.yaml",
    "ethscan.yml",
]

# Default config used when no file is found.
DEFAULT_CONFIG: dict[str, Any] = {
    "defaults": {},
    "commands": {},
}


def _candidate_paths(explicit: str | None = None) -> list[Path]:
    """Return the list of config file paths to search.

    When ``explicit`` is provided it is prepended to the standard candidates.
    The first two candidates are relative to the current working directory;
    the next two are relative to the user's home directory (``Path.home()``);
    XDG Base Directory locations are also searched if ``XDG_CONFIG_HOME`` is
    set or ``~/.config`` exists.
    """
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit))
    home = Path.home()
    for candidate in CONFIG_CANDIDATES:
        if candidate.startswith("."):
            paths.append(home / candidate)
        else:
            paths.append(Path(candidate))

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        xdg_base = Path(xdg_config_home)
    else:
        xdg_base = home / ".config"
    for candidate in XDG_CONFIG_CANDIDATES:
        paths.append(xdg_base / candidate)
    return paths


def find_config_file(explicit: str | None = None) -> Path | None:
    """Locate the first existing config file.

    Args:
        explicit: Optional explicit path to check first.

    Returns:
        Path to the config file, or None when none exists.
    """
    for candidate in _candidate_paths(explicit):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def load_config(explicit: str | None = None) -> dict[str, Any]:
    """Load and validate the ethscan configuration.

    Args:
        explicit: Optional explicit path to a config file.

    Returns:
        A dict with ``defaults`` and ``commands`` keys. Missing keys are
        filled in with empty dicts so callers can safely index into them.
        A ``_parse_error`` key is set to a human-readable message when the
        file exists but could not be parsed; it is absent otherwise.
    """
    path = find_config_file(explicit)
    if path is None:
        return dict(DEFAULT_CONFIG)

    if yaml is None:
        return {
            "defaults": {},
            "commands": {},
            "_path": str(path),
            "_parse_error": f"Failed to parse {path}: PyYAML is required to load configuration files",
        }

    try:
        data = yaml.safe_load(read_text(path))
    # A file whose YAML nests deeper than the parser can read raises a
    # ``RecursionError``, which is not a ``yaml.YAMLError``: it is a file
    # that cannot be parsed, and it is reported like a file with broken YAML.
    except (yaml.YAMLError, RecursionError) as exc:
        return {
            "defaults": {},
            "commands": {},
            "_path": str(path),
            "_parse_error": f"Failed to parse {path}: {exc}",
        }
    except OSError as exc:
        return {
            "defaults": {},
            "commands": {},
            "_path": str(path),
            "_parse_error": f"Failed to read {path}: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "defaults": {},
            "commands": {},
            "_path": str(path),
            "_parse_error": f"Config root must be a mapping in {path}",
        }

    defaults = data.get("defaults") or {}
    commands = data.get("commands") or {}

    if not isinstance(defaults, dict):
        defaults = {}
    if not isinstance(commands, dict):
        commands = {}

    return {
        "defaults": defaults,
        "commands": commands,
        "_path": str(path),
    }


def _merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge command-level defaults with global defaults.

    Command-level values take precedence over global defaults.
    """
    merged: dict[str, Any] = {}
    merged.update(defaults)
    merged.update(overrides)
    return merged


# Click option dest names that the documented ``format`` config key maps to.
# The user-facing ``--output-format`` option uses the ``output_fmt`` dest, while
# the deprecated ``--format`` alias uses ``fmt``. Config values are applied via
# Click's ``default_map``, which is keyed by dest, so the documented ``format``
# key must be remapped to a dest that actually controls output. We map it to
# ``fmt`` (the deprecated ``--format`` alias dest) rather than ``output_fmt``
# because the runtime precedence rule is
# ``chosen = output_fmt if output_fmt is not None else fmt``. Mapping to
# ``output_fmt`` instead would make config values sticky and ignore the
# deprecated ``--format`` CLI flag, breaking the documented override contract.
_FORMAT_DEST = "fmt"


def _normalize_format_key(options: dict[str, Any]) -> dict[str, Any]:
    """Remap the documented ``format`` key to the working ``fmt`` Click dest.

    Click's ``default_map`` is keyed by option *dest* names. The documented
    config schema (see ``dump_default_config`` and the README) uses ``format``,
    but every command's working format dest is ``fmt`` (the deprecated
    ``--format`` alias). Without this remap a user's ``format: markdown``
    setting is silently ignored and output stays JSON. ``fmt`` is used rather
    than ``output_fmt`` so that CLI ``--format``/``--output-format`` flags still
    override the config value.
    """
    if not isinstance(options, dict):
        return options
    if "format" not in options:
        return options
    normalized = dict(options)
    value = normalized.pop("format")
    # Do not clobber an explicit output_fmt already present in the config.
    normalized.setdefault(_FORMAT_DEST, value)
    return normalized


def build_default_map(
    config: dict[str, Any],
    command: str,
) -> dict[str, Any]:
    """Build the Click ``default_map`` for a single command.

    Args:
        config: Parsed configuration dict (as returned by ``load_config``).
        command: Command name (e.g. ``"scan"``).

    Returns:
        A dict mapping option dest names to config values. Empty when the
        command has no configured defaults. The documented ``format`` key is
        remapped to the working ``fmt`` dest so it actually takes effect.
    """
    defaults = _normalize_format_key(config.get("defaults") or {})
    commands = config.get("commands") or {}
    overrides = _normalize_format_key(commands.get(command) or {})
    if not isinstance(overrides, dict):
        overrides = {}
    return _merge(defaults, overrides)


def config_path_string(config: dict[str, Any]) -> str | None:
    """Return the path of the loaded config file, or None."""
    path = config.get("_path")
    if isinstance(path, str):
        return path
    return None


def validate_config(
    config: dict[str, Any],
    known_commands: list[str] | None = None,
    known_options: dict[str, set[str]] | None = None,
) -> list[str]:
    """Validate a config dict and return a list of human-readable warnings.

    An empty list means the config is structurally valid. Warnings are
    non-fatal and do not prevent the toolkit from running.

    When ``known_options`` is given, it maps a command name to the set of
    option dest names that command accepts, and each configured option that
    is not accepted by its command is reported as a warning. A typo in a
    config option name would otherwise be silently ignored.
    """
    warnings: list[str] = []
    parse_error = config.get("_parse_error")
    if isinstance(parse_error, str):
        warnings.append(parse_error)
        return warnings

    defaults = config.get("defaults")
    commands = config.get("commands")

    if defaults is not None and not isinstance(defaults, dict):
        warnings.append("'defaults' must be a mapping")

    if commands is not None:
        if not isinstance(commands, dict):
            warnings.append("'commands' must be a mapping")
        else:
            if known_commands is not None:
                for cmd in commands:
                    if cmd not in known_commands:
                        warnings.append(
                            f"Unknown command '{cmd}' in config (no such command)"
                        )
            for cmd, opts in commands.items():
                if not isinstance(opts, dict):
                    warnings.append(
                        f"command '{cmd}' must be a mapping of option names to values"
                    )
                    continue
                if known_options is not None:
                    options = known_options.get(cmd)
                    if options is not None:
                        for key in opts:
                            if not _option_is_known(key, options):
                                warnings.append(
                                    f"Unknown option '{key}' for command '{cmd}' "
                                    f"(no such option)"
                                )

    return warnings


def _option_is_known(key: str, options: set[str]) -> bool:
    """Return whether a config option key is accepted by a command.

    The documented config key ``format`` is remapped to the working ``fmt``
    Click dest (see ``_normalize_format_key``), so it counts as known when
    ``fmt`` is accepted.
    """
    return key in options or (key == "format" and "fmt" in options)


def dump_default_config() -> str:
    """Return a YAML string documenting the supported config schema."""
    sample = """\
# Global defaults applied to every command that does not override them.
defaults:
  timeout: 5.0
  workers: 50
  format: json

# Per-command overrides (keys are Click option dest names).
commands:
  scan:
    ports: common
    profile: normal
    timeout: 1.0
    workers: 100
  subdomains:
    timeout: 3.0
    resolver: 8.8.8.8
"""
    return sample


def format_config_report_csv(config: dict[str, Any]) -> str:
    """Format config as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["section", "option", "value"])

    # Config file path
    path = config.get("_path")
    if path:
        writer.writerow(["config", "path", path])

    # Parse error
    parse_error = config.get("_parse_error")
    if parse_error:
        writer.writerow(["config", "parse_error", parse_error])

    # Global defaults
    defaults = config.get("defaults") or {}
    for key, value in sorted(defaults.items()):
        writer.writerow(["defaults", key, value])

    # Per-command overrides
    commands = config.get("commands") or {}
    for cmd, opts in sorted(commands.items()):
        if isinstance(opts, dict):
            for key, value in sorted(opts.items()):
                writer.writerow([f"commands.{cmd}", key, value])

    return output.getvalue().rstrip("\r\n")