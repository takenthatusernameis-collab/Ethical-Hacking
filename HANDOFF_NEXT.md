## Status: BLOCKED (infrastructure) - test.yml ready locally, push requires workflows write scope

### What changed this session
- Restored `.github/workflows/test.yml` locally (from commit `c977570`) and committed `1aec5f3` ("Restore test.yml for push").
- Local `main` at `1aec5f3`, exactly 1 commit ahead of `origin/main` (`c07f1ad`).
- `origin/main` at `c07f1ad`; `test.yml` ABSENT on remote/main (deleted in `c07f1ad`).
- Working tree clean; `python -m ruff check .` All checks passed. `pytest` 5461 passed / 50 skipped.
- `git push origin main` attempted with env `GH_TOKEN`: rejected `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (token lacks `workflows` write scope).

### What was actually verified
- `git rev-list --count origin/main..main` -> 1 (local commit `1aec5f3` ready to push).
- `git rev-list --count main..origin/main` -> 0 (no remote-only commits).
- `.github/workflows/test.yml` parses as valid YAML; runs test on ubuntu-latest, macos-latest, windows-latest.
- `python -m ruff check .` -> All checks passed.
- `pytest` 5461 passed / 50 skipped (this session).
- Push with `GH_TOKEN`: 403 / missing `workflows` permission (fresh evidence, this session).

### What remains unresolved
- Land `.github/workflows/test.yml` on remote/main: requires PAT/GitHub App token with `workflows` write scope, then `git push origin main` (commit `1aec5f3` is local and ready).
- Trigger and verify cross-platform `test` workflow (ubuntu-latest, macos-latest, windows-latest).

### Which approaches have already failed and why
- Pushing `.github/workflows/test.yml` with `GH_TOKEN`: 403 / "without workflows permission" (workflows write scope missing). Repeated failure across sessions - same approach cannot work without different token.
- `gh pr create`: 403 (insufficient scope) per prior session.
- `act`: not installed; cannot validate matrix locally.

### One precise next task
Obtain a token/PAT with `workflows` write scope. Then: `git push origin main` (local commit `1aec5f3` adds `.github/workflows/test.yml`; `origin/main` at `c07f1ad`, no conflict). Trigger `workflow_dispatch` for `test` and confirm ubuntu-latest, macos-latest, windows-latest pass. If no token available: durable local state is commit `1aec5f3` on `main` (test.yml ready to push); `origin/main` stays at `c07f1ad`. Treat as infrastructure blocker; no further code change required.
