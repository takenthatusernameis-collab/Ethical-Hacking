## What changed this session
- Restored `.github/workflows/ci.yml` (ruff lint + pytest on push/pull_request), which had been deleted in commit `521e664` — a regression that left the project without its own CI gate while prior handoffs claimed CI verification had passed.

## What was actually verified
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- Restored `ci.yml` matches the version from commit `3fdd2ba` exactly (verified via `git show 3fdd2ba:.github/workflows/ci.yml`).

## What remains unresolved
- None.

## Which approaches have already failed and why
- The "repository is complete, nothing to do" handoff was itself unreliable: it asserted CI verification while the CI workflow file was missing from the tree. Always re-verify claims against the actual working tree, not prior handoff files.

## One precise next task
None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.