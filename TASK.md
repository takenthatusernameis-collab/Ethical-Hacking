# Task
Date: Fri Nov 06 2026

## Current state
- HEAD: working tree modified (uncommitted). Baseline was green before changes.
- Tests: `5888 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session
- **Demonstrated gap (reproduced):** `memcached`, `mysql`, `mongodb`, `postgresql`, `mssql`, and `oracle` accepted unknown `--probes` values (exit 0) and silently ignored them — `memcached --probes bogus` produced a zero-probe report with no error (and `--probes version,bogus` still ran `version`), while DB probes skipped unknowns and often still executed the default probe path. Contrast: `redis --probes bogus` already rejected at CLI (exit 2). `run_oracle(..., probes=["bogus"])` library behavior (no probes run, `error=None`) was codified by `tests/test_oracle.py::test_run_oracle_unknown_probe` and preserved.
- **Fix (smallest reversible, CLI-only):** In `ethscan/cli.py`, validate `--probes` for `memcached/mysql/mongodb/postgresql/mssql/oracle` against each module's `DEFAULT_PROBES` (case-insensitive; mixed-case probe tokens like `buildInfo` accepted) and raise `click.UsageError` (exit 2) before any recon work. Added aliased imports of `DEFAULT_PROBES` per module. Library modules unchanged.
- **Tests:** Added `tests/test_cli.py` cases: `test_memcached_unknown_probe_rejected`, `test_mysql_unknown_probe_rejected`, `test_mongodb_unknown_probe_rejected`, `test_postgresql_unknown_probe_rejected`, `test_mssql_unknown_probe_rejected`, `test_oracle_unknown_probe_rejected` (assert exit 2, error text, and recon function not called). Updated CLI probe pass-through tests unaffected except MongoDB now receives canonical-lowercased token as before (`buildInfo` → `buildinfo` path via normalization; test asserts `["buildinfo"]`).

## Verified (evidence)
- Repro before fix: `memcached --probes bogus` / `mysql|mongodb|postgresql|mssql|oracle --probes bogus` → exit 0 (JSON output). `redis --probes bogus` → exit 2 (`Unknown probes: bogus. Valid probes: ping, info, config`).
- After fix: each of the 6 commands rejects `--probes bogus` with exit 2, `Unknown probes: bogus. Valid probes: <defaults>`, and no recon call (CLI tests).
- `python3 -m pytest tests/test_oracle.py -q --tb=no` → `116 passed` (library unknown-probe contract preserved).
- `python3 -m pytest tests/test_memcached.py tests/test_mysql.py tests/test_mongodb.py tests/test_postgresql.py tests/test_mssql.py -q --tb=no` → `332 passed`.
- `python3 -m pytest tests/test_cli.py -q -k "memcached or mysql or mongodb or postgresql or mssql or oracle or redis" --tb=no` → `70 passed, 963 deselected`.
- `python3 -m pytest -q --tb=no` → `5888 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Blockers
- None.

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection (or a silent-accept validation gap like recon modules / DB probes) in an area **different** from the exhausted CLI edge sweep and now-fixed `recon --modules` and `--probes` validation for `memcached/mysql/mongodb/postgresql/mssql/oracle`. If scanning, choose a materially different surface and stop at first reproduced gap; add the smallest permanent guard/test. Keep baseline green; do not commit unless asked. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.
