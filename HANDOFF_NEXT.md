## What changed this session
- Added `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request), restored from commit `1b7f1d2`. The workflow was missing from the working tree and from HEAD despite the prior handoff claiming it was restored.

## What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- ci.yml YAML parses cleanly.

## What remains unresolved
- None.

## One precise next task
None — repository is in a verified passing state.
