# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `c07f1ad`; `test.yml` ABSENT on remote/main (deleted in commit `c07f1ad`).
- Restored `.github/workflows/test.yml` locally (from commit `c977570`) and committed `1aec5f3` ("Restore test.yml for push").
- Local `main` at `1aec5f3`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN` lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Tests: `pytest` 5461 passed / 50 skipped (verified this session). Source unchanged by `1aec5f3`.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `1aec5f3` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `1aec5f3` (test.yml ready to push); `origin/main` stays at `c07f1ad`. No further code change needed.

## Evidence
- Push rejection message (this session, env `GH_TOKEN`): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `1aec5f3` ready to push).
- `git log --oneline -3`: 1aec5f3, c07f1ad, c977570
