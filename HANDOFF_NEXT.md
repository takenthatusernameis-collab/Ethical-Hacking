## What changed this session

Fixed a demonstrated bug: `ethscan config --init PATH --out OUT` silently dropped
the `--out` path (the output file was never created) because the `--init` branch
returned early before reaching the report-writing code. The two options are now
mutually exclusive and reported as a usage error (exit code 2).

- `ethscan/cli.py:3582-3587` — added a `click.UsageError` guard at the top of the
  `config` command body: `--init` and `--out` cannot be used together.
- `tests/test_cli.py:12532` — added `test_config_init_and_out_are_mutually_exclusive`
  regression test (exit 2, "cannot be used together" in output, neither file written).

## What was actually verified

- Reproduced the bug first: `python -m ethscan config --init /tmp/itest/sample.yaml --out /tmp/itest/report.json` exited 0 and created only `sample.yaml`; `report.json` was absent.
- After fix: same invocation now exits 2 with the usage error and writes neither file.
- `python -m pytest tests/test_cli.py -k "config_init_and_out_are_mutually_exclusive or config_init_creates_parent_dirs or config_init_writes_sample or config_init_sample_runs_end_to_end"` → 4 passed.
- `python -m pytest tests/test_config.py tests/test_config_value_sweep.py tests/test_option_sweep.py tests/test_file_content_sweep.py tests/test_file_option_sweep.py` → 213 passed, 48 skipped.
- `python -m pytest tests/ -q` → 5205 passed, 51 skipped, 0 warnings (was 5204; +1 regression test).
- `python -m ruff check ethscan/cli.py tests/test_cli.py` → All checks passed.

## What remains unresolved

None. Working tree clean after commit; branch in sync with origin.

## Which approaches have already failed and why

None in this session. The bug was reproducible and fixed with the smallest change.

## One precise next task

None — repository complete and verified. If a new issue appears, implement the
smallest reversible fix, verify with `python -m pytest tests/ -q` and
`python -m ruff check ethscan/ tests/`, and update `HANDOFF_NEXT.md` with evidence.