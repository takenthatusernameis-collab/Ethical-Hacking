# Task
Date: Fri Nov 06 2026

## Current state
- HEAD: clean working tree, up to date with `origin/main` (no uncommitted changes this session).
- Tests: `5878 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session (scan only, no code change)
- Evidence-driven scan for demonstrated gaps in CLI option validation (non-Choice/non-Range `click.Path`/file-content cases reaching side effects before rejection).
- Verified coverage:
  - All 20 `click.Path(exists=True, readable=True, dir_okay=False)` subcommand file-input options are enumerated in `FILE_OPTIONS` (`tests/test_cli.py:24317`) and covered by `test_a_file_option_with_a_missing_file_is_a_usage_error` / `test_a_file_option_with_a_directory_is_a_usage_error` (introspection cross-check matched exactly).
  - Group `--config` path validation (nonexistent, directory, unreadable) covered by `test_config_path_must_name_a_readable_file` (`tests/test_cli.py:12769`, 1 passed). `config --config` (subcommand) missing path and `config --init` unusable parent return exit 2 with `BadParameter`/no traceback (verified manually).
  - `--out` writable paths: 56 `_write_output(out_path, ...)` call sites catch `OSError`/`ValueError` → `click.BadParameter("'--out'")` (parent dir created when missing). `test_an_unusable_output_path_is_a_usage_error` / missing-parent-created / writable-success tests exist; manual check of file-as-parent case returned exit 2, no traceback.
  - JSON/XML/UTF-8 hostile file-content cases have dedicated usage-error tests (`JSON_FILE_OPTIONS`, XML, credential UTF-8).
- No new demonstrated gap found (no option observed to reach side effects before clean rejection).

## Verified (evidence)
- `python3 -m pytest tests/test_cli.py -q --tb=no -k "config_path_must_name_a_readable_file"` → 1 passed.
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Blockers
- None.

## Next task
- Continue evidence-driven scan only for a *demonstrated* gap (an option/callback that reaches side effects before rejection with a reproducible case). Do not duplicate existing IntRange/FloatRange/Choice/ports/CIDR/host/offline-input/file-input (`FILE_OPTIONS`)/JSON-content/`--out`/`--config` sweeps. Add the smallest permanent guard/test only with evidence. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
