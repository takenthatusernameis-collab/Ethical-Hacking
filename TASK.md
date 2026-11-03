# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified this session)
- `HEAD` = `origin/main` = `5b7953c`; working tree clean; in sync, nothing to push.
- `.github/workflows/test.yml` is ABSENT from HEAD (`.github/workflows/` contains only `kilo-workflow-audit.yml` and `main.yml`).
- `test.yml` content is PRESERVED in git history (commit `4686103` "Add test workflow", 32 lines, cross-platform matrix ubuntu/macos/windows, Python 3.12, `permissions: contents: read`).
- `GH_TOKEN` and `GITHUB_TOKEN` are the SAME GitHub App token (identical `ghs_...` JWT). Both return `403 Resource not accessible by integration` on the actions/permissions API. No PAT with `workflows` write scope is available. No other credentials in `~/.git-credentials` or env.
- `git push origin main` for test.yml was REJECTED previously: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission`.
- `workflow_dispatch` POST also returned 403 (same token, same scope gap).
- Baseline health (verified this session): `python -m ethscan --help` exits 0; `python -m ruff check ethscan tests` clean ("All checks passed!"); `python -m pytest -q` 5472 passed, 50 skipped.

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope. (GH_TOKEN/GITHUB_TOKEN lack it; confirmed 403.)
2. If available: restore `test.yml` from git history (`4686103`), `git push origin main`, then trigger `test` via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable state is `test.yml` content in git history (`4686103`) + local verification (ruff clean, pytest 5472 passed/50 skipped); `origin/main` stays at `5b7953c` without test.yml. No further code change needed without a token.

## Evidence
- `git rev-parse HEAD` -> `5b7953c`; `git rev-parse origin/main` -> `5b7953c` (in sync).
- `git ls-tree HEAD .github/workflows/` -> only `kilo-workflow-audit.yml` and `main.yml`; no `test.yml`.
- `git show 4686103:.github/workflows/test.yml` -> exists (32 lines).
- `python -m ruff check ethscan tests` -> All checks passed!
- `python -m pytest -q` -> 5472 passed, 50 skipped.
