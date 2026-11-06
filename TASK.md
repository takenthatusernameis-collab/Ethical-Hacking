# Task
Date: Fri Nov 06 2026

## Current state
- HEAD (committed): `b6c024f` (working tree has uncommitted local changes in `tests/test_cli.py` and handoff docs; do not commit unless asked).
- Tests: `5878 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## Prior session (completed)
- Gap: `ethscan/cli.py` declares 126 `click.Choice` options but only `test_completion_invalid_shell_errors` asserted invalid-choice rejection.
- Change: added `test_every_choice_option_of_the_cli_is_enumerated` and `test_an_invalid_choice_value_is_a_usage_error` to `tests/test_cli.py`. Verified: 2 targeted tests + full suite + ruff + mypy all green.

## This session (demonstrated gap + fix)
- Gap: `--config` is a `click.Path()` option declared on the CLI group (`ethscan/cli.py:402`), validated by `_check_config_path` (`ethscan/cli.py:680`). Every permanent sweep iterates `cli.cli.commands` (subcommands), so the group's `--config` path validation (nonexistent path, directory, unreadable file) had no permanent test. Confirmed empirically: `--config /nonexistent` and `--config <directory>` exit 2 with an `Error: Invalid value for '--config'` usage error and no traceback.
- Change (small, reversible): added `test_config_path_must_name_a_readable_file` to `tests/test_cli.py`. It walks a nonexistent path, a directory, and an unreadable file and asserts exit 2, the `--config` usage error, the expected message fragment, no traceback, and `SystemExit` (no callback/side effects before rejection).

## Verified (evidence)
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "config_path_must_name_a_readable_file"` → 1 passed.
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "config"` → 44 passed.
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Blockers
- None.

## Next task
- Continue evidence-driven scan for any non-Choice/non-Range option that can reach side effects before rejection (the `--config` group gap just closed; `click.Path`/`click.File`/custom callbacks/mutually-exclusive groups otherwise have no new findings). Add smallest permanent guard only with evidence. Do not duplicate existing IntRange/FloatRange/Choice/ports/CIDR/host/offline-input sweeps. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
