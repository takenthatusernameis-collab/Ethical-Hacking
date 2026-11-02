# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `9343135`; `test.yml` ABSENT on remote/main (removed in commit `9343135`, whose parent is `ec824d7`).
- Restored `.github/workflows/test.yml` from `ec824d7` and committed `1b125be` on local `main`.
- Local `main` at `1b125be`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` REJECTED (this session): `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (token lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Prior: `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files). Source unchanged by `1b125be`.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `1b125be` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `1b125be` (test.yml ready to push); `origin/main` stays at `9343135`. No further code change needed.

## Evidence
- Push rejection message (this session): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `1b125be` ready to push).
- `git log --oneline -3`: 1b125be, 9343135, ec824d7
