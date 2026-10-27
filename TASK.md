## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request), deleted in commit `521e664`.

### What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- Restored `ci.yml` matches commit `3fdd2ba` exactly.

### What remains unresolved
- None.

### Which approaches have already failed and why
- Trusting prior handoff claims without re-checking the working tree: the handoff asserted CI verification while `ci.yml` was absent.

### One precise next task
None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.