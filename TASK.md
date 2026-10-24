# TASK

## Status: COMPLETE

Made `validate_config` warn about unknown config options per command (previously it only warned about unknown commands; an unknown option such as `scan: { potrs: common }` was silently ignored).

### What was done

- `ethscan/config.py`: `validate_config` gained an optional `known_options: dict[str, set[str]]` parameter mapping a command name to the set of option dest names it accepts. Each configured option not accepted by its command is now reported as a warning. The documented config key `format` (remapped to the `fmt` Click dest by `_normalize_format_key`) counts as known when `fmt` is accepted, via a new `_option_is_known` helper.
- `ethscan/cli.py:410`: the startup call now passes `known_options` built from `cli.commands` (each click command's parameter dest names), so every real CLI command is covered.
- `tests/test_config.py`: added `test_validate_config_unknown_option`, `test_validate_config_known_option_clean`, `test_validate_config_defaults_are_not_option_checked`, `test_validate_config_with_real_cli_commands`, `test_validate_config_format_key_counts_as_fmt`, and `test_validate_config_format_key_without_fmt_is_unknown`.

### What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed (0 errors).
- `python -m pytest tests/ -q` → 5204 passed, 48 skipped, 3 warnings (pre-existing `test_main.py` runpy warnings).
- End-to-end: `python -m ethscan --config <bogus-option config> config` emits
  `Warning: Unknown option 'potrs' for command 'scan' (no such option)`;
  a valid `format: json` config emits no warning.

### What remains unresolved

None from this task.

### Approaches that failed and why

- The first version of the option check treated `format` as unknown for every command, breaking `test_cli.py::test_config_explicit_overrides_config` (which configures `cidr: { format: json }`). Fixed by recognizing `format` as an alias for the `fmt` dest.
- The end-to-end CLI tests `test_config_option_unknown_bogus_warning` and `test_config_option_format_key_no_warning` already existed but were broken: their YAML placed `cidr:` at the top level (parsed as an unknown *command*, not an unknown *option*), and they accessed `result.stderr` on a default `CliRunner` (mix_stderr=True), which raises `ValueError: stderr not separately captured`. Fixed by wrapping the config in `commands:` and using `CliRunner(mix_stderr=False)`.

### One precise next task

None. The next task from the handoff is complete.

(End of file - total 31 lines)