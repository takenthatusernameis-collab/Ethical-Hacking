## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `c99d0ff` and committed it at HEAD. Recurring delete/restore failure mode addressed.

### What was actually verified
- `git show HEAD:.github/workflows/ci.yml` -> file present and tracked in HEAD.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python -m pytest tests/ -q` -> 5225 passed, 51 skipped.
- `git status --short` -> clean working tree.

### What remains unresolved
- None.

### One precise next task
None — repository in verified passing state. Do NOT delete `.github/workflows/ci.yml`; it is the verified baseline.
