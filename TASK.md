# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `ed7a958`; `test.yml` ABSENT on remote/main (deleted in commit `ed7a958`).
- Restored `.github/workflows/test.yml` locally and committed `9bb0c34` ("Restore .github/workflows/test.yml").
- Local `main` at `9bb0c34`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Tests: `pytest` 5461 passed / 50 skipped.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `9bb0c34` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `9bb0c34` (test.yml ready to push); `origin/main` stays at `ed7a958`. No further code change needed.

## Evidence
- Push rejection message (this session): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `9bb0c34` ready to push).
- `git log --oneline -2`: 9bb0c34, 7a33135
