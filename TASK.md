# Task
Date: Thu Nov 05 2026

## Current state
- HEAD (committed): `b6c024f` (working tree has uncommitted local changes in `tests/test_cli.py` and handoff docs; do not commit unless asked).
- Tests: 5874 passed, 53 skipped, 0 failed.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session (demonstrated gap + fix)
- Gap: `ethscan/cli.py` declares 126 `click.Choice` options (format choices + 18 non-format choices like `--profile`, `--protocol`, `--algorithm`, `--sort`, `--severity/--min-severity`, `--ldap-version`, `completion` shell), but only `tests/test_cli.py::test_completion_invalid_shell_errors` asserted invalid-choice rejection. No permanent sweep existed to catch a `Choice` replaced by a plain string type or loosened validation.
- Change (small, reversible): added `test_every_choice_option_of_the_cli_is_enumerated` and `test_an_invalid_choice_value_is_a_usage_error` to `tests/test_cli.py`. The sweep walks every `click.Choice` param, supplies minimal safe base args per command, invokes with `__bogus__`, and asserts Click exit 2 + `Error: Invalid value for` + `is not one of` + no traceback before command callbacks (no network/probe side effects).

## Verified (evidence)
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "choice_option"` → 2 passed.
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "completion_invalid_shell"` → 1 passed.
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "an_out_of_range_timeout_option_is_a_usage_error"` → 1 passed (sanity).
- `python3 -m pytest -q --tb=no` → `5874 passed, 53 skipped in 101.25s (0:01:41)`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Blockers
- None.

## Next task
- Re-scan for demonstrated CLI validation gaps not covered by permanent sweeps: bounded `click.Path`/`click.File`/custom callbacks, required-option interactions, or non-Choice/non-Range options that can reach side effects before rejection. Add only the smallest permanent guard when a real gap is found (with evidence). Do not duplicate existing IntRange/FloatRange/Choice/ports/CIDR/host/offline-input sweeps.
- Run: targeted pytest for new tests, then `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

(End of file)
