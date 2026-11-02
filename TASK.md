# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `origin/main` and `main` both at `043c93e`; `test.yml` ABSENT on remote/main.
- `test.yml` exists on local branch `preserve/test-workflow` @ `057eb37`.
- `git merge --ff-only preserve/test-workflow` NOT possible: `main` (`043c93e`) not an ancestor of `preserve/test-workflow`.
- `.github/workflows/test.yml` landed on local `main` at commit `ec824d7` ("Add cross-platform test workflow"); source unchanged.
- `git push origin main` REJECTED: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission`.
- Local verification: workflow YAML valid; `ruff check .` clean; `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files).

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: `git push origin main` (commit `ec824d7` ready, 1 commit ahead of `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable local state is commit `ec824d7` (test.yml ready to push); `origin/main` stays at `043c93e`. No code change needed.

## Evidence
- Push rejection message (this session): missing `workflows` permission.
- `git rev-list --count origin/main..main` -> 1 (local commit `ec824d7` ready to push).
- `git log --oneline -3`: ec824d7, 043c93e, 448519f
