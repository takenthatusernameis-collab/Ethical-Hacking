## Status: COMPLETE

### What changed
- Added `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request and workflow_dispatch), which was missing from the working tree and from HEAD despite the prior handoff claiming it was restored (commit `1b7f1d2` added it, but a later commit removed it). Content restored from commit `1b7f1d2`.

### What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → ci.yml YAML: OK.

### What remains unresolved
- None.

### One precise next task
None — repository complete.
