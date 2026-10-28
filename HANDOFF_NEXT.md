## Status: COMPLETE

### What changed
- Added 10 tests to `tests/test_validate.py`. `ethscan/validate.py` now 100% coverage.

### What was actually verified
- `python -m pytest tests/test_validate.py -q` -> 79 passed.
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5272 passed, 48 skipped.
- `ethscan/validate.py` coverage 100%.

### What remains unresolved
- None. Next candidate: `ethscan/headers.py` at 97% (2 miss).

### One precise next task
- Add tests to `tests/test_headers.py` to raise `ethscan/headers.py` coverage, identifying missing lines via coverage report, keeping ruff and full suite green.

(End of file - total 15 lines)