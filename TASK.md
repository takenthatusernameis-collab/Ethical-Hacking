# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `main` == `origin/main` == `fe5022f` (fully in sync; `git rev-list` both directions = 0).
- `.github/workflows/test.yml` is ABSENT on both local and remote (deleted in commit `fe5022f`).
- Workflow content is recoverable from git history commit `581d4f9` ("Add cross-platform test workflow"): `git show 581d4f9:.github/workflows/test.yml`.
- `git push origin main` blocked: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` lacks `workflows` write scope).
- Local verification: `ruff check .` All checks passed. `pytest -q` -> 5459 passed / 2 failed / 50 skipped; the 2 failures (`tests/test_file_option_sweep.py` hostile `--out` timeouts for `recon`/`whois`) are pre-existing and unrelated to the workflow task.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope.
2. If available: re-create `.github/workflows/test.yml` from commit `581d4f9`, commit it, `git push origin main` (adds test.yml since `main` == `origin/main`), then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable state is `test.yml` content in git history commit `581d4f9`; `main` == `origin/main` == `fe5022f` with test.yml absent. No further code change needed without a token.

## Evidence
- `git rev-parse main origin/main HEAD` all resolve to `fe5022f`.
- `git show main:.github/workflows/test.yml` -> path does not exist.
- `GH_TOKEN`/`GITHUB_TOKEN` is a GitHub App token without `workflows` write scope.
- `git log --all --oneline -- .github/workflows/test.yml` shows `581d4f9` as the commit that added it.
