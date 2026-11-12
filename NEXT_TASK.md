# Next Task

## Status
Repository is fully green: `python -m pytest -q` → 6106 passed, 53 skipped, 1 warning, 0 failed; `python -m mypy ethscan/ tests/` → clean except 2 pre-existing errors in `tests/test_smb.py:1437,1443` (unrelated); `python -m ruff check ethscan/ tests/` → all checks passed.

`ethscan/cli.py` was brought to 100% in session 105 (CLI-focused coverage suite: `tests/test_cli.py` + `tests/test_cli_cov_gaps.py`). Previously completed to 100% include `oracle.py`, `ldap.py`, `subtake.py`, `smtp.py`, `snmp.py`, `smb.py`, `redis.py`, `postgresql.py`, `mysql.py`, `mssql.py`, `s3.py`, `trace.py`, `ntp.py`, `dnssec.py`, `mongodb.py`, `wifi.py`, and others per history.

## One precise next task
Reproduce project-wide coverage with `python -m pytest -q --cov=ethscan --cov-report=term-missing` to confirm there are no remaining modules below 100%. If any module is <100%, pick ONE such module, reproduce its exact uncovered lines, then add focused offline/mock-based tests to close them (do not batch modules). If all modules are at 100%, there is no pending coverage task—pick a single high-value, verifiable improvement only if reproduced from evidence; otherwise leave a no-work handoff.

## Notes
- `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes` intentionally uses `runpy.run_module` and emits a `RuntimeWarning`; do not "fix" by weakening the test without evidence-based need.
- `tests/test_smb.py:1437,1443` mypy errors are pre-existing/unrelated.
