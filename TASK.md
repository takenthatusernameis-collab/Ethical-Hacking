# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` at `8ceee44`; `test.yml` ABSENT on remote/main (deleted in commit `8ceee44`).
- Restored `.github/workflows/test.yml` from `1b125be` and committed `23b3ce0` on local `main`.
- Local `main` at `23b3ce0`, exactly 1 commit ahead of `origin/main` (`git rev-list --count origin/main..main` -> 1).
- `git push origin main` blocked (prior session): `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (token lacks `workflows` write scope).
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. Prior: `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files). Source unchanged by `23b3ce0`.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `23b3ce0` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `23b3ce0` (test.yml ready to push); `origin/main` stays at `8ceee44`. No further code change needed.

## Evidence
- Push rejection message (prior session): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `23b3ce0` ready to push).
- `git log --oneline -3`: 23b3ce0, 8ceee44, 7ec8e35
