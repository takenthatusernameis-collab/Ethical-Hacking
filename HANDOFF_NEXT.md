## Status: BLOCKED (infrastructure) - test.yml committed locally, push requires workflows write scope

### What changed this session
- Restored `.github/workflows/test.yml` by cherry-picking from `preserve/test-workflow` (commit `057eb37`) as `12d9ab4` ("Add cross-platform test workflow").
- Local `main` at `12d9ab4`, exactly 1 commit ahead of `origin/main` (`48ca607`); no conflict.
- `git push origin main` will be rejected with current `GH_TOKEN` (GitHub App token) lacking `workflows` write scope.
- Local verification: `python -m ruff check .` -> All checks passed. `python -m pytest -q` -> 5461 passed / 50 skipped.

### What was actually verified
- `git rev-list --count origin/main..main` -> 1 (local commit `12d9ab4` ready to push).
- `git rev-list --count main..origin/main` -> 0 (no remote-only commits).
- `.github/workflows/test.yml` present locally, YAML valid (matrix ubuntu-latest, macos-latest, windows-latest).

### What remains unresolved
- Land `.github/workflows/test.yml` on remote/main: requires PAT/GitHub App token with `workflows` write scope, then `git push origin main` (commit `12d9ab4` adds `.github/workflows/test.yml`).
- Trigger and verify cross-platform `test` workflow (ubuntu-latest, macos-latest, windows-latest) after push.

### Which approaches have already failed and why
- Pushing with `GH_TOKEN` (GitHub App token): lacks `workflows` permission (repeated). Changing approach requires different token with `workflows` scope.

### One precise next task
Obtain a token/PAT with `workflows` write scope. Then: `git push origin main` (commit `12d9ab4` ready, 1 ahead of `origin/main` at `48ca607`). Trigger `workflow_dispatch` for `test` and confirm ubuntu-latest, macos-latest, windows-latest pass. If no token available: durable local state is commit `12d9ab4` on `main` with test.yml ready to push; `origin/main` stays at `48ca607`. Treat as infrastructure blocker; no further code change required.
