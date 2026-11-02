## Status: BLOCKED (infrastructure) - test.yml ready locally, push requires workflows write scope

### What changed this session
- Re-added `.github/workflows/test.yml` locally (restored from commit `23b3ce0`) and committed `c977570` ("Restore cross-platform test workflow").
- Local `main` at `c977570`, exactly 1 commit ahead of `origin/main` (`931c706`).
- `origin/main` at `931c706`; `test.yml` ABSENT on remote/main (deleted in `931c706`).
- Working tree clean; `python -m ruff check .` All checks passed.
- `git push origin main` attempted with env `GH_TOKEN`: rejected `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (token lacks `workflows` write scope).

### What was actually verified
- `git rev-list --count origin/main..main` -> 1 (local commit `c977570` ready to push).
- `git rev-list --count main..origin/main` -> 0 (no remote-only commits).
- `.github/workflows/test.yml` parses as valid YAML; runs test on ubuntu-latest, macos-latest, windows-latest.
- `python -m ruff check .` -> All checks passed.
- Prior (preserved): `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files).
- Push with `GH_TOKEN`: 403 / missing `workflows` permission (fresh evidence, this session).

### What remains unresolved
- Land `.github/workflows/test.yml` on remote/main: requires PAT/GitHub App token with `workflows` write scope, then `git push origin main` (commit `c977570` is local and ready).
- Trigger and verify cross-platform `test` workflow (ubuntu-latest, macos-latest, windows-latest).

### Which approaches have already failed and why
- Pushing `.github/workflows/test.yml` with `GH_TOKEN`: 403 / "without workflows permission" (workflows write scope missing).
- `gh pr create`: 403 (insufficient scope) per prior session.
- `act`: not installed; cannot validate matrix locally.

### One precise next task
Obtain a token/PAT with `workflows` write scope. Then: `git push origin main` (local commit `c977570` adds `.github/workflows/test.yml`; `origin/main` at `931c706`, no conflict). Trigger `workflow_dispatch` for `test` and confirm ubuntu-latest, macos-latest, windows-latest pass. If no token available: durable local state is commit `c977570` on `main` (test.yml ready to push); `origin/main` stays at `931c706`. Treat as infrastructure blocker; no further code change required.
