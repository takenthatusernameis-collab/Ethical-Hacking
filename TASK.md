## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `c99d0ff`. Committed at HEAD.

### What was actually verified
- `git show HEAD:.github/workflows/ci.yml` -> file present and tracked in HEAD.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python -m pytest tests/ -q` -> 5225 passed, 51 skipped.
- `git status --short` -> clean working tree after commit.

### What remains unresolved
- None.

### One precise next task
None — repository in verified passing state with `.github/workflows/ci.yml` restored and committed. Do NOT delete `.github/workflows/ci.yml`; it is the verified baseline.
