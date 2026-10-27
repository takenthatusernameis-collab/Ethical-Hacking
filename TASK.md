## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `1b7f1d2` (ruff lint + pytest on push/pull_request/workflow_dispatch). The file was deleted in commit `2b68c9e` and never restored, despite prior handoff claims that it was. Verified missing from working tree and from `HEAD` before restoring.
- Committed as `6fffc1a`.

### What was actually verified
- `git show HEAD:.github/workflows/ci.yml` → file present and tracked.
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → YAML parses.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `git status --short` → clean working tree.

### What remains unresolved
- None.

### One precise next task
None — repository complete.