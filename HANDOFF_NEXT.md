## What changed this session
- Restored `.github/workflows/ci.yml` and committed as `d28fd37`.

  The prior handoff files (`TASK.md`, `NEXT_TASK.md`, `HANDOFF_NEXT.md`) claimed the repository was complete and that `ci.yml` was present and tracked. That was false: `git show HEAD:.github/workflows/ci.yml` failed ("path does not exist in 'HEAD'"), because commit `572dfab` had deleted the file after the earlier restore commit `6fffc1a`. The working tree was also missing the file. This session restored it from `6fffc1a` and committed.

## What was actually verified
- `git ls-files .github/workflows/ci.yml` → tracked.
- `git show HEAD:.github/workflows/ci.yml` → present in `HEAD` (d28fd37).
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → YAML parses; job `lint-test` present.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped.
- `git status --short` → clean working tree; no untracked files.

## What remains unresolved
- None.

## One precise next task
None — repository is in a verified passing state.