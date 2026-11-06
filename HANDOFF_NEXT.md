# Handoff
Date: Fri Nov 06 2026

## What changed
- Added `test_config_path_must_name_a_readable_file` to `tests/test_cli.py` (tests/test_cli.py:12769).
- Gap closed: the `--config` option is a `click.Path()` declared on the CLI group (`ethscan/cli.py:402`) and validated by `_check_config_path` (`ethscan/cli.py:680`). Every permanent sweep iterates `cli.cli.commands` (subcommands), so the group's `--config` path validation had no permanent test. The new test walks a nonexistent path, a directory, and an unreadable file and asserts exit 2 + `Error: Invalid value for '--config'` + expected message fragment + no traceback + `SystemExit`.

## Verified
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "config_path_must_name_a_readable_file"` → 1 passed.
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Unresolved
- None new.

## Next task
- Continue evidence-driven scan for any non-Choice/non-Range option that can reach side effects before rejection. Add smallest permanent guard only with evidence. Do not duplicate existing IntRange/FloatRange/Choice/ports/CIDR/host/offline-input sweeps. Do not commit unless asked.
