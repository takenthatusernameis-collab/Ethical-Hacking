## Status: COMPLETE (this session)

### What changed
- `tests/test_dnssec.py`: added `test_format_dnssec_report_markdown_ds_records_skip_non_dict` and `test_format_dnssec_report_csv_ds_records_skip_non_dict`, covering `ethscan/dnssec.py:614` and `ethscan/dnssec.py:824` (the `if not isinstance(record, dict): continue` branches in the DS-records formatting loops). Test-only; no source modifications.

### What was actually verified
- `pytest tests/test_dnssec.py -q` -> 111 passed.
- `python -m ruff check tests/test_dnssec.py ethscan/dnssec.py` -> All checks passed.
- `coverage report --include="ethscan/dnssec.py" -m` -> `ethscan/dnssec.py` 100% (0 miss; was 99%, 2 miss at 614, 824).
- Full suite: `python -m pytest -q` -> 5392 passed, 48 skipped, 0 failed.
- Total coverage: 99% (83 miss; was 85).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss; not test-only-feasible).
- `ethscan/cve.py` lines 348-349 (dead code, requires source change).
- `ethscan/ntp.py` line 392 (dead code, requires source refactor).
- Other small misses in cli.py, hash.py, mongodb.py, mssql.py, mysql.py, oracle.py, osdetect.py, postgresql.py.

### Which approaches failed and why
- `ntp.py:392`, `cve.py:348-349`, `radix.py`: dead / not test-only-feasible without a source change; prior test-based attempts failed. `web.py:318`, `wifi.py:328`, `dnssec.py:614`, `dnssec.py:824` confirmed test-only feasible and now covered.

### One precise next task
- All test-only-feasible small coverage gaps are closed. Remaining gaps require a source change that does not fix a bug. Recommended next bounded task: `ethscan/ntp.py:392` (single miss) — refactor the monlist-response handling so the error-check is reachable without changing behavior, add a test in `tests/test_ntp.py`, verify ntp.py -> 100% coverage and ruff + ntp tests pass; otherwise defer and record the gap as out of scope for test-only work.
