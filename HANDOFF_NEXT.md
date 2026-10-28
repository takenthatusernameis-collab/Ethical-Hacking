## Status: COMPLETE

### What changed
- Added tests to `tests/test_stale.py` covering AAAA/CNAME exceptions in `resolve_domain_all`, A-record exception path, thread-pool exception handling in `run_stale`, and defensive branches in Markdown/CSV formatters (non-dict entries, None lists).

### What was actually verified
- `python -m pytest tests/test_stale.py --cov=ethscan.stale --cov-report=term-missing` -> 47 passed, `ethscan/stale.py` 100% coverage (184 stmts, 0 miss).
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5325 passed, 48 skipped.

### What remains unresolved
- None obvious. Check coverage of remaining modules if desired (e.g. other modules below 100%).

### One precise next task
- COMPLETE: `ethscan/dns.py` is now 100% (144 stmts, 0 miss).
- Next: raise `ethscan/radix.py` coverage from 94% (340 stmts, 19 miss: lines 181-182, 200-202, 206-209, 267-268, 296, 444, 448, 473, 488, 521, 558, 561, 575) by adding tests to `tests/test_radix.py`, keeping `ruff check ethscan/ tests/` and the full pytest suite green. Use `python -m coverage report --include="ethscan/radix.py" -m` to identify missing lines first.
