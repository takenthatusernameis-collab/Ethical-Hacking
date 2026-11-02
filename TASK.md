# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `48ca607`; `test.yml` ABSENT on remote/main.
- Cherry-picked commit `057eb37` from `preserve/test-workflow` as `12d9ab4` ("Add cross-platform test workflow") - adds `.github/workflows/test.yml`.
- Local `main` at `12d9ab4`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. `pytest` 5461 passed / 50 skipped.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `12d9ab4` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `12d9ab4` (test.yml ready to push); `origin/main` stays at `48ca607`. No further code change needed.

## Evidence
- Push rejection expected (missing `workflows` permission).
- `git rev-list --count origin/main..main` -> 1 (local commit `12d9ab4` ready to push).
- `git log --oneline -2`: 12d9ab4, 48ca607
