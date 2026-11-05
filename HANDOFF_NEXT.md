# Handoff
Date: Thu Nov 05 2026

## What changed (uncommitted, local working tree)
- `tests/test_cli.py`: added a permanent `click.Choice` validation sweep covering all 126 Choice options across CLI commands (`test_every_choice_option_of_the_cli_is_enumerated`, `test_an_invalid_choice_value_is_a_usage_error`). Uses `__bogus__` + minimal safe base args; asserts Click parse-time rejection (exit 2, `Error: Invalid value for`, `is not one of`, no traceback) before callbacks. Includes positional Choice handling (`completion` shell arg) and `nmap --input-file` base arg. Do not commit unless asked.
- Updated `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.

## Verified (evidence)
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "choice_option"` → 2 passed.
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "completion_invalid_shell"` → 1 passed.
- `python3 -m pytest tests/test_cli.py -q --tb=short -k "an_out_of_range_timeout_option_is_a_usage_error"` → 1 passed.
- `python3 -m pytest -q --tb=no` → `5874 passed, 53 skipped, 0 failed` (101.25s).
- `python3 -m ruff check .` → all checks passed.
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Unresolved / notes
- Working tree is uncommitted (tests + handoff docs); do not commit unless explicitly asked.
- The Choice sweep uses command-specific base args; if a command gains new required options, update `_choice_option_base_args` or make it derive required args safely.

## Approaches that failed / pitfalls
- Initial sweep used `--file` for `nmap` (actual option is `--input-file`) and asserted the raw flag string for the positional `completion` shell (`SHELL` appears uppercased in Click output); fixed by correcting base args and accepting `flag.upper()`/`param_name.upper()` in the option-name assertion.

## Precise next task
- Evidence-driven: scan `ethscan/cli.py` for validation patterns not covered by permanent sweeps (`click.Path`/`click.File` constraints, custom `callback=` validators, required mutually-exclusive groups, or options that can trigger side effects before Click/custom validation). If a real gap is found, add the smallest permanent rejection/no-side-effect test and extend an existing sweep style where appropriate. Do not duplicate IntRange/FloatRange/Choice/ports/CIDR/host/offline-input coverage. Verify targeted pytest + full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`; update handoff docs. Do not commit unless asked.
