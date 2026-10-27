## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request), which was missing from the working tree again.

### What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.

### What remains unresolved
- None.

### One precise next task
None — repository complete.
