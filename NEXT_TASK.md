# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5888 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Fixed demonstrated gap: `memcached/mysql/mongodb/postgresql/mssql/oracle` silently accepted unknown `--probes` (exit 0). `ethscan/cli.py` now validates `--probes` against each module's `DEFAULT_PROBES` (case-insensitive) and rejects with `click.UsageError` (exit 2) before recon work. Added aliased `DEFAULT_PROBES` imports per module. Libraries unchanged; `tests/test_oracle.py::test_run_oracle_unknown_probe` preserved.
- Added CLI tests: `test_memcached_unknown_probe_rejected`, `test_mysql_unknown_probe_rejected`, `test_mongodb_unknown_probe_rejected`, `test_postgresql_unknown_probe_rejected`, `test_mssql_unknown_probe_rejected`, `test_oracle_unknown_probe_rejected` in `tests/test_cli.py`.

## Candidate work (only if demonstrated)
- Find/reproduce a validation or side-effect-before-reject gap in a **materially different** area (CLI edge sweep exhausted; `recon --modules` fixed; DB/memcached/redis `--probes` CLI validation now fixed). Stop at first reproduced gap; smallest guard/test only.
- Do not duplicate existing sweeps or treat intentional in-output reporting/contracts as gaps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
