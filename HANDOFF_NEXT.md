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
- Review modules with low coverage via `python -m coverage report -m` and add targeted tests for one module (smallest area of missing coverage first) while keeping `ruff check ethscan/ tests/` and the full pytest suite green.
