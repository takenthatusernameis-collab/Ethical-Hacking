## Status: COMPLETE (this session)

### What changed
- `tests/test_dnssec.py`: added `test_format_dnssec_report_markdown_ds_records_skip_non_dict` and `test_format_dnssec_report_csv_ds_records_skip_non_dict`, covering the `if not isinstance(record, dict): continue` branches in the DS-records formatting loops at `ethscan/dnssec.py:614` and `ethscan/dnssec.py:824`. Test-only; no source modifications.

### What was actually verified
- `pytest tests/test_dnssec.py -q` -> 111 passed (incl. the 2 new tests).
- `python -m ruff check tests/test_dnssec.py ethscan/dnssec.py` -> All checks passed.
- `coverage report --include="ethscan/dnssec.py" -m` -> `ethscan/dnssec.py` 100% (0 miss; was 99%, 2 miss at 614, 824).
- Full suite: `python -m pytest -q` -> 5392 passed, 48 skipped, 0 failed (was 5390; +2 new tests).
- Total coverage: 99% (83 miss; was 85).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss: defensive/fallback branches at 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324; previously deemed not test-only-feasible).
- `ethscan/cve.py` lines 348-349: `if isinstance(items, dict):` is unreachable because `items` is always a list at that point; requires a source change to reach.
- `ethscan/ntp.py` line 392: dead defensive code — `if mon_resp.get("error"):` inside the `else` branch of `if mon_resp.get("error"):` (line 372); unreachable without a source refactor.
- Additional small misses in cli.py, hash.py, mongodb.py, mssql.py, mysql.py, oracle.py, osdetect.py, postgresql.py (not part of the prior 1-miss-gap focus).

### Which approaches failed and why
- `ethscan/ntp.py:392`: previously attempted via a test; logically dead because the outer `if/else` on `mon_resp.get("error")` already consumes the truthy case. Not test-only feasible; source refactor required.
- `radix.py`/`cve.py` defensive lines: previously deemed not test-only-feasible; `cve.py:348-349` confirmed dead by inspection (`items` always a list).
- `web.py:318`, `wifi.py:328`, `dnssec.py:614`, `dnssec.py:824`: all confirmed test-only feasible and now covered (100%).

### One precise next task
- All test-only-feasible small coverage gaps are closed. Remaining gaps (`cve.py:348-349`, `ntp.py:392`, `radix.py` 20) are dead code or defensive branches not reachable without a source change that does not fix a bug. Next bounded task: pick ONE remaining gap and decide definitively. Recommended: `ethscan/ntp.py:392` (single miss) — restructure the monlist-response handling so the error-check is reachable without changing observable behavior, then add a test in `tests/test_ntp.py`; verify `coverage report --include="ethscan/ntp.py" -m` -> 100% and `ruff check ethscan/ntp.py tests/test_ntp.py` pass. If the refactor risks behavior, defer and record the gap as out of scope for test-only work.
