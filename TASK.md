## Status: COMPLETE

### What changed
- Added `LICENSE` (MIT).

### What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.

### What remains unresolved
None.

### Which approaches have already failed and why
- None in this session.

### One precise next task
None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.
