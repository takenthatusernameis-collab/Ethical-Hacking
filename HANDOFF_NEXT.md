## Status: COMPLETE

### What changed
- Added 2 hostile and 2 usable targets to `tests/test_target.py` covering the query-only (no slash) branch of `_path_of` (lines 217-222).

### What was actually verified
- `pytest tests/test_target.py -q` -> 230 passed.
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5278 passed, 48 skipped.
- `ethscan/target.py` coverage: 95% -> 100% (78 stmts, 0 miss).

### What remains unresolved
- None. Next candidate: `ethscan/stale.py` at 93% (184 stmts, 12 miss).

### One precise next task
- Raise `ethscan/stale.py` coverage from 93% (184 stmts, 12 miss) by adding tests for its missing branches to `tests/test_stale.py`, keeping `ruff check ethscan/ tests/` and the full pytest suite green. Use `python -m coverage report --include="ethscan/stale.py" -m` to identify missing lines first.
