## Status: BLOCKED (infrastructure) - test.yml committed locally, push requires workflows write scope

### What changed this session
- Restored `.github/workflows/test.yml` from git history (`git show 1aec5f3:.github/workflows/test.yml`), added and committed `9bb0c34` ("Restore .github/workflows/test.yml").
- Local `main` at `9bb0c34`, exactly 1 commit ahead of `origin/main` (`ed7a958`); no conflict. Previous attempt removed it (commit `7a33135`); now restored again.
- `git push origin main` rejected: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` lacks `workflows` write scope). Fresh evidence this session.
- Local verification: `python -m ruff check .` -> All checks passed. `python -m pytest -q` -> 5461 passed / 50 skipped.

### What was actually verified
- `git rev-list --count origin/main..main` -> 1 (local commit `9bb0c34` ready to push).
- `git rev-list --count main..origin/main` -> 0 (no remote-only commits).
- `.github/workflows/test.yml` present locally, YAML valid (matrix ubuntu-latest, macos-latest, windows-latest).

### What remains unresolved
- Land `.github/workflows/test.yml` on remote/main: requires PAT/GitHub App token with `workflows` write scope, then `git push origin main` (commit `9bb0c34` adds `.github/workflows/test.yml`).
- Trigger and verify cross-platform `test` workflow (ubuntu-latest, macos-latest, windows-latest) after push.

### Which approaches have already failed and why
- Pushing with `GH_TOKEN` (GitHub App token): 403 / missing `workflows` permission (repeated). Changing approach requires different token with `workflows` scope.
- Deleting/restoring cycle observed; cannot push without proper token.

### One precise next task
Obtain a token/PAT with `workflows` write scope. Then: `git push origin main` (commit `9bb0c34` ready, 1 ahead of `origin/main` at `ed7a958`). Trigger `workflow_dispatch` for `test` and confirm ubuntu-latest, macos-latest, windows-latest pass. If no token available: durable local state is commit `9bb0c34` on `main` with test.yml ready to push; `origin/main` stays at `ed7a958`. Treat as infrastructure blocker; no further code change required.
