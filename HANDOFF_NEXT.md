## Status: COMPLETE

### What changed
- Created `.github/workflows/ci.yml` with ruff lint + pytest on push/pull_request (previously missing despite handoff claims).

### What was actually verified
- YAML parses; job `lint-test` present.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.

### What remains unresolved
- None.

### One precise next task
None — repository in verified passing state.
