# Next Task
Date: Tue Nov 17 2026

## Status
- No prior queued task existed. Inspected the repo and found that the most recent commit (`dee9844`, empty message) had added an undocumented, untested `config --set KEY=VALUE` feature after the previous handoff, which also silently broke the 100% branch-coverage invariant.
- Completed/verified that feature: fixed three real defects (silent data loss on unparseable config, stale `parse_error` in the report, and `_set_nested` silently dropping values on a non-dict intermediate), added 26 tests, and documented `--set` in the README. Coverage restored to 100%.

## What changed
- `ethscan/cli.py` (`config` command): refuse `--set` when the loaded config has a parse error (exit 2, no write); refresh `parse_error` after the post-write reload; removed dead/redundant branches (redundant `find_config_file` re-lookup and identical `if path != config_path` arms).
- `ethscan/config.py`: `_set_nested` now requires `section.option` form (ValueError otherwise), replaces non-dict section/intermediate values with a fresh dict so the value is not dropped, and drops the dead `if not parts: return`.
- `README.md`: documented `--set KEY=VALUE` (feature bullet + Configuration section).
- `tests/test_config.py`: +26 tests (unit tests for `_parse_set_value`/`_set_nested`/`save_config`, plus CLI `--set` integration incl. unparseable-config refusal, write-failure, `--config` path, and output correctness).

## What was verified
- `pytest -q` -> 32214 passed, 146 skipped, 0 failed (baseline 32188; +26 new tests).
- Branch coverage -> 100% (5916/5916 branches, 0 missing, 0 partial); statements 15659/15659.
- `mypy ethscan/ tests/` -> Success, no issues in 259 source files.
- `ruff check ethscan/ tests/` -> All checks passed.
- `check_readme.py` -> 54/54, 0 drift.
- End-to-end smoke: basic/nested `--set` writes valid YAML and updates in place; broken config -> exit 2 with file unchanged.
- `git diff --check` clean; only 4 files modified; changes left uncommitted for the harness/reviewer.

## Next task
- One precise next task: audit `config --set` interaction with `--out`/`--format` and with a `--config` path that does not yet exist. Currently `--config` must name an existing file (`_check_config_path`), so only the discovered/cwd `ethscan.yaml` is created fresh by `--set`; decide whether a missing `--config` file should be created (and parent dirs) or continue to be a usage error, then implement the chosen behavior with tests + a README note. Reproduce current behavior first; keep it minimal.
- If no further work is desired: repository is fully green (32214 passed, 146 skipped, 0 failed; mypy/ruff/README clean; 100% statement and branch coverage). Do not weaken the parse-error guard or other safety controls.

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change. Do not commit unless explicitly asked.
- Pre-existing flaky test: `tests/test_file_option_sweep.py::test_every_file_option_refuses_hostile_values[ntp]` (network-dependent, 5s timeout) — passed in isolation and on re-run; not caused by this work.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error). `passwords.py` salted/peppered audit intentionally evaluates the derived hash.
- Dev deps: pytest, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4. No pytest-cov plugin — use `python -m coverage run --branch --source=ethscan -m pytest` for coverage.