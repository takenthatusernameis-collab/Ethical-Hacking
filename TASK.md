# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `931c706`; `test.yml` ABSENT on remote/main (deleted in commit `931c706`).
- Restored `.github/workflows/test.yml` locally and committed `c977570` ("Restore cross-platform test workflow").
- Local `main` at `c977570`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN` lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Prior: `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files). Source unchanged by `c977570`.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `c977570` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `c977570` (test.yml ready to push); `origin/main` stays at `931c706`. No further code change needed.

## Evidence
- Push rejection message (this session, env `GH_TOKEN`): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `c977570` ready to push).
- `git log --oneline -3`: c977570, 931c706, e6cb154
