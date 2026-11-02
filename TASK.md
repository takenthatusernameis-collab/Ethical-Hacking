# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `ed7a958`; `test.yml` ABSENT on remote/main (deleted in commit `ed7a958`).
- Restored `.github/workflows/test.yml` locally (from commit `1aec5f3`) and committed `24b4ccb` ("Restore .github/workflows/test.yml").
- Local `main` at `24b4ccb`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Tests: `pytest` 5461 passed / 50 skipped (verified this session). Only change is test.yml addition.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `24b4ccb` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `24b4ccb` (test.yml ready to push); `origin/main` stays at `ed7a958`. No further code change needed.

## Evidence
- Push rejection message (this session, env `GH_TOKEN`): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `24b4ccb` ready to push).
- `git log --oneline -3`: 24b4ccb, 105b02a, 1aec5f3
