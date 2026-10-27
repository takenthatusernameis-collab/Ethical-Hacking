## What changed this session
- Restored `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request) from commit `3fdd2ba`. The workflow was missing from the working tree (deleted in `521e664`).

## What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- Restored `ci.yml` matches the version from commit `3fdd2ba` exactly.

## What remains unresolved
- None.

## Which approaches have already failed and why
- Trusting prior handoff claims without re-checking the working tree: earlier handoffs asserted CI verification while `ci.yml` was absent from the tree.

## One precise next task
None — repository is in a verified passing state. If new requirements arrive, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` and `python -m ruff check ethscan/ tests/` before committing.
