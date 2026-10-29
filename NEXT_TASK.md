## Status: COMPLETE (this session)

### What changed
- `tests/test_osdetect.py`: added `test_run_osdetect_invalid_max_workers_reports_probes`, covering `ethscan/osdetect.py:424-425` (outer `except` around the `ThreadPoolExecutor` block). Reached via `run_osdetect(..., max_workers=0)` which raises `ValueError` at executor construction; real inputs, no mocking. Test-only; no source modifications.

### What was actually verified
- `pytest tests/test_osdetect.py -q` -> 82 passed.
- Full suite: `pytest -q` -> 5394 passed, 48 skipped, 0 failed.
- `coverage report --include="ethscan/osdetect.py" -m` -> 100% (was 99%, 2 miss at 424-425).
- `ruff check ethscan/osdetect.py tests/test_osdetect.py` -> All checks passed.

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss): lines 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324. All defensive/fallback branches confirmed unreachable with real `ipaddress` inputs; requires pathological fake objects or a source refactor that fixes no bug. Out of scope for test-only work.

### Which approaches failed and why
- `ethscan/radix.py` defensive branches: unreachable with real `ipaddress` objects (verified empirically). Not test-only feasible; no source change made.

### One precise next task
- Pick ONE remaining small coverage gap from a full-suite coverage report (candidates: cli.py, hash.py, mongodb.py, mssql.py, mysql.py, oracle.py, postgresql.py, redis.py, resolve.py, smtp.py, ssh.py). Verify the missed lines are reachable with REAL inputs before writing any test. Add a test only if reachable without disproportionate complexity; verify coverage improves to 100% for that module and `ruff check` + full suite pass. If unreachable defensive code, document evidence and defer.
