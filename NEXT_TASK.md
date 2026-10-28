## Status: COMPLETE

### What changed
- Added 2 hostile and 2 usable targets to `tests/test_target.py` covering the query-only (no slash) branch of `_path_of` (lines 217-222).
- No source changes to `ethscan/target.py`.

### What was actually verified
- `pytest tests/test_target.py -q` -> 230 passed.
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5278 passed, 48 skipped.
- `ethscan/target.py` coverage: 95% -> 100% (78 stmts, 0 miss).

### What remains unresolved
- None. `ethscan/stale.py` reached 100% in a prior session; `ethscan/dns.py` reached 100% in this session.

### One precise next task
- Raise `ethscan/radix.py` coverage from 94% (340 stmts, 19 miss: lines 181-182, 200-202, 206-209, 267-268, 296, 444, 448, 473, 488, 521, 558, 561, 575) by adding tests to `tests/test_radix.py`, keeping `ruff check ethscan/ tests/` and the full pytest suite green. Use `python -m coverage report --include="ethscan/radix.py" -m` to identify missing lines first.
