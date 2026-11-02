## Status: PARTIAL (dnspython fix landed on remote/main; test.yml still local-only)

### What changed this session
- Verified true local state: `.github/workflows/test.yml` is NOT on local `main` (HEAD tracks only `kilo-workflow-audit.yml` and `main.yml`). The prior handoff's claim that `test.yml` was committed on `main` was incorrect — commit `057eb37` ("Add cross-platform test workflow", adds `test.yml`) is not an ancestor of `main`.
- Pushed local `main` (`c76fb52..9b9a571`) to `origin/main` — SUCCESS. This landed `c67f0be` (`dnspython>=2.0` in `requirements.txt`) on remote `main`. Push was NOT blocked because it touches no `.github/workflows/*` files (the workflows-permission gate only rejects pushes that create/update workflow files).
- Preserved the dangling `test.yml` commit on new local branch `preserve/test-workflow` (points to `057eb37`, contains `.github/workflows/test.yml`).

### What was actually verified (this session, 2026-11-02)
- `git push origin main` -> `c76fb52..9b9a571 main -> main` (accepted; no workflows touched).
- `origin/main` == `9b9a571`; `requirements.txt` on origin/main contains `dnspython>=2.0`.
- `python -m pytest -q` -> 5461 passed, 50 skipped (all remaining skips intentional sweep exclusions).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success: no issues in 59 source files.

### What remains unresolved
- `test.yml` not on remote/main. Requires a token with `workflows` write scope to push `.github/workflows/*`.
- `GH_TOKEN` lacks `workflows` write permission (403 on actions/permissions API) and lacks `pull-requests` write scope (403 on createPullRequest).
- Cross-platform CI never triggered; `act` not installed.

### Which approaches have already failed and why
- `git push origin main` with `GH_TOKEN` WHEN main contained `test.yml`: rejected ("refusing to allow a GitHub App to create or update workflow `.github/workflows/test.yml` without `workflows` permission"). No longer relevant — current `main` has no `test.yml` and the push just succeeded.
- Querying actions/permissions with `GH_TOKEN`: 403.
- `gh pr create` with `GH_TOKEN`: 403 (Resource not accessible by integration).
- Local matrix validation via `act`: not installed.

### One precise next task
- Obtain a token/PAT with `workflows` (write) scope for this repository.
- Then: push the `test.yml` work onto `main`, e.g. `git checkout main && git merge --ff-only preserve/test-workflow && git push origin main` (or cherry-pick `057eb37`). This adds `.github/workflows/test.yml` only — `dnspython` is already on remote/main so no conflict.
- Trigger the `test` workflow via `workflow_dispatch` and confirm the `test` job passes on ubuntu-latest, macos-latest, windows-latest.
- If no such token is available: durable remote state is `origin/main` at `9b9a571` with `dnspython>=2.0`; `test.yml` exists only on local branch `preserve/test-workflow` (commit `057eb37`). Document as infrastructure blocker; no further code change required.
