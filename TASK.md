## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `c99d0ff`. The file had been deleted again from `HEAD` (commit `c4656cf`) after the previous session's handoff claimed it was the verified baseline — the delete/restore cycle is the recurring failure mode.

### What was actually verified
- `git show HEAD:.github/workflows/ci.yml` → file present and tracked in `HEAD`.
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → YAML parses; job `lint-test` present; `permissions.contents: read`.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `git status --short` → clean working tree after commit.

### What remains unresolved
- None.

### One precise next task
None — repository in verified passing state with `.github/workflows/ci.yml` restored and committed. Do NOT delete `.github/workflows/ci.yml`; it is the verified baseline.
