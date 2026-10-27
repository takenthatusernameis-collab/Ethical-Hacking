## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `fef4156` and committed as `c99d0ff`. The file had been deleted again in `25427ec` after the previous session's handoff claimed completion — the delete/restore cycle is the recurring failure mode.

### What was actually verified
- `git show HEAD:.github/workflows/ci.yml` -> file present and tracked in `HEAD` (c99d0ff).
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` -> YAML parses; job `lint-test` present.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python -m pytest tests/ -q` -> 5225 passed, 51 skipped.
- `git status --short` -> clean working tree.

### What remains unresolved
- None.

### One precise next task
None — repository in verified passing state. Do NOT delete `.github/workflows/ci.yml`; it is the verified baseline.