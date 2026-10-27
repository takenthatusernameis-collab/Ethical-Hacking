## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/dnsbrute.py` (6 errors -> 0) via cast narrowing: `records_count` int cast, `axfr_total_records`/`recursive_total_records` int casts, and `sorted` key lambdas cast to str.

### What was actually verified
- `python -m mypy ethscan/dnsbrute.py` -> Success: no issues found in 1 source file (remaining errors are in imported `dns.py`).
- `python -m ruff check ethscan/dnsbrute.py` -> All checks passed.
- `python -m pytest tests/test_dnsbrute.py -q` -> 102 passed, 2 skipped.

### What remains unresolved
- Remaining mypy errors in other modules (~187 across 36 files).

### One precise next task
Fix mypy errors in next module with most errors; inspect `python -m mypy ethscan/` to pick.
