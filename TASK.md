# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified this session)
- `HEAD` = `origin/main` = `49c409e8ed332531e20258a60fd091386afc7007`; working tree clean; in sync, nothing to push.
- `.github/workflows/test.yml` is ABSENT from HEAD. `.github/workflows/` contains only `kilo-workflow-audit.yml` and `main.yml` (confirmed via `git ls-tree` and the GitHub API which lists exactly 2 workflows).
- `test.yml` content is PRESERVED in git history at commits `4686103`, `b4d5c13`, `7769aaa`, `2404ba2` (identical 32-line cross-platform ubuntu/macos/windows Python 3.12 workflow, `permissions: contents: read`, runs `python -m pytest -q`).
- `GH_TOKEN` and `GITHUB_TOKEN` are set; `gh` is logged in as `github-actions[bot]` (GitHub App token). The token lacks `workflows` write scope: `GET /repos/takenthatusernameis-collab/Ethical-Hacking/actions/permissions` returns HTTP 403 "Resource not accessible by integration". No PAT with `workflows` write scope is available; no `.git-credentials` with a different token (the configured git-credentials file contains the same `ghs_15368_...` App token).
- `git push origin main` for test.yml would be REJECTED: GitHub App lacks `workflows` permission to create/update `.github/workflows/test.yml`. `workflow_dispatch` POST also 403s. Deterministic; do not retry without a new token.
- Baseline health (verified this session): `python -m ruff check ethscan tests` clean ("All checks passed!"); `python -m pytest -q` 5472 passed, 50 skipped (exit 0).

## Next actions
1. Obtain a PAT/GitHub App token with `workflows` (write) scope for `takenthatusernameis-collab/Ethical-Hacking`. (GH_TOKEN/GITHUB_TOKEN lack it; confirmed.)
2. If available: restore `test.yml` from git history (`git show 4686103:.github/workflows/test.yml > .github/workflows/test.yml`), `git commit`, `git push origin main`, then trigger `test` via `workflow_dispatch` (`gh workflow run test.yml -R takenthatusernameis-collab/Ethical-Hacking --ref main`) and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable state is `test.yml` content in git history (`4686103`/`b4d5c13`) + local verification (ruff clean, pytest 5472 passed/50 skipped); `origin/main` stays at `49c409e8` without test.yml. No further code change needed without a token.

## Evidence
- `git rev-parse HEAD` -> `49c409e8ed332531e20258a60fd091386afc7007`; `git rev-parse origin/main` -> same (in sync).
- `git ls-tree HEAD .github/workflows/` -> only `kilo-workflow-audit.yml` and `main.yml`; no `test.yml`.
- `git show 4686103:.github/workflows/test.yml` -> exists (32 lines, identical to `b4d5c13`).
- `git log --oneline --all -- .github/workflows/test.yml` -> includes `75199d3` (removal), `b4d5c13`, `4686103`, `7769aaa`, `2404ba2` (adds).
- API `GET /repos/takenthatusernameis-collab/Ethical-Hacking/actions/workflows` -> HTTP 200, exactly 2 workflows (kilo-workflow-audit.yml, main.yml), no test.yml.
- API `GET /repos/takenthatusernameis-collab/Ethical-Hacking/actions/permissions` -> HTTP 403 "Resource not accessible by integration" (no `workflows` write scope).
- `python -m ruff check ethscan tests` -> exit 0 "All checks passed!".
- `python -m pytest -q` -> exit 0 "5472 passed, 50 skipped".
