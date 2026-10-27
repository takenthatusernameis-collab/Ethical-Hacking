## Status: COMPLETE

### What changed
- Restored `.github/workflows/ci.yml` from commit `1b7f1d2` (ruff lint + pytest on push/pull_request/workflow_dispatch). The file was missing from working tree despite prior handoff claims.

### What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → ci.yml YAML: OK.

### What remains unresolved
- None.

### One precise next task
None — repository complete.
