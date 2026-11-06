# Handoff
Date: Fri Nov 06 2026

## What changed
- `ethscan/cli.py`: validate `--probes` for `memcached`, `mysql`, `mongodb`, `postgresql`, `mssql`, and `oracle` against each module's `DEFAULT_PROBES` (case-insensitive; accepts mixed-case tokens like `buildInfo`). Unknown probes now raise `click.UsageError` (exit 2) with `Unknown probes: ... Valid probes: ...` before any recon work. Added aliased imports: `DEFAULT_MEMCACHED_PROBES`, `DEFAULT_MYSQL_PROBES`, `DEFAULT_MONGODB_PROBES`, `DEFAULT_POSTGRESQL_PROBES`, `DEFAULT_MSSQL_PROBES`, `DEFAULT_ORACLE_PROBES`. No library module behavior changes.
- `tests/test_cli.py`: added `test_memcached_unknown_probe_rejected`, `test_mysql_unknown_probe_rejected`, `test_mongodb_unknown_probe_rejected`, `test_postgresql_unknown_probe_rejected`, `test_mssql_unknown_probe_rejected`, `test_oracle_unknown_probe_rejected` (exit 2, error text, recon not invoked).

## Demonstrated gap (reproduced, now fixed)
- Before: `memcached --target 127.0.0.1 --port 1 --probes bogus` → exit 0, JSON report (no error about bogus probe). `mysql|mongodb|postgresql|mssql|oracle --probes bogus` → exit 0 (unknown ignored; DB path still reachable depending on probe set). Contrast: `redis --probes bogus` already rejected (exit 2).
- Library contract preserved: `tests/test_oracle.py::test_run_oracle_unknown_probe` still passes (`run_oracle(..., probes=["bogus"])` performs no probes).

## Verified (evidence)
- `python3 -m pytest tests/test_oracle.py -q --tb=no` → `116 passed`.
- `python3 -m pytest tests/test_memcached.py tests/test_mysql.py tests/test_mongodb.py tests/test_postgresql.py tests/test_mssql.py -q --tb=no` → `332 passed`.
- `python3 -m pytest tests/test_cli.py -q -k "memcached or mysql or mongodb or postgresql or mssql or oracle or redis" --tb=no` → `70 passed, 963 deselected`.
- `python3 -m pytest -q --tb=no` → `5888 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Unresolved
- None demonstrated by this change.

## Approaches already tried / not to repeat blindly
- Broad CLI edge-case sweeps — exhausted across sessions; do not repeat unchanged.
- Treating intentional in-output reporting / documented contracts as usage-error gaps — not actionable without a demonstrated mismatch.
- `run_oracle(..., probes=["bogus"])` library behavior is intentionally tested; CLI now rejects before calling library (different boundary).

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection or a silent-accept validation gap in an area **different** from the exhausted CLI edge sweep and fixed `recon --modules` / `--probes` validation for `memcached/mysql/mongodb/postgresql/mssql/oracle`. Materially different scan surface only; stop at first reproduced gap; add smallest permanent guard/test. Keep baseline green; do not commit unless asked.
