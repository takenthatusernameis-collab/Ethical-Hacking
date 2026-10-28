## Status: COMPLETE

### What changed
- Added 3 tests to `tests/test_headers.py`. `ethscan/headers.py` now 100% coverage.

### What was actually verified
- `python -m pytest tests/test_headers.py -q` -> 17 passed.
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5275 passed, 48 skipped.
- `ethscan/headers.py` coverage 100%.

### What remains unresolved
- None. Next candidate: `ethscan/target.py` at 95% (4 miss).

### One precise next task
- Add tests to `tests/test_target.py` to raise `ethscan/target.py` coverage, identifying missing lines via coverage report, keeping ruff and full suite green.

(End of file - total 15 lines)