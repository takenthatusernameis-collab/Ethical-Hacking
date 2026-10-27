## What changed this session
- Restored `.github/workflows/ci.yml` from commit `06c56a0` and committed as `fef4156`. Commit `9c1e30d` had deleted the file again after the previous session's handoff incorrectly claimed completion.

## What was actually verified
- `git ls-files .github/workflows/ci.yml` → tracked.
- `git show HEAD:.github/workflows/ci.yml` → present in `HEAD` (fef4156).
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → YAML parses; job `lint-test` present.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `git status --short` → clean working tree.

## What remains unresolved
- None.

## One precise next task
None — repository is in a verified passing state.
