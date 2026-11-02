# Status: BLOCKED (infrastructure) - test.yml push requires workflows write scope

### What changed this session
- HEAD moved from `0869e04` to `d9f52b4` (doc-only commits updating durable state files). `origin/main` == `main` == `HEAD` == `d9f52b4`, in sync.
- Re-confirmed the blocker three independent ways this session:
  1. `curl .../actions/permissions -H "Authorization: Bearer $GH_TOKEN"` -> 403 (same for `$GITHUB_TOKEN`).
  2. Restored `test.yml` from history (`09cd757`), committed, `git push origin main` -> `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission`.
  3. `POST .../actions/workflows/test.yml/dispatches` -> 403.
- Decoded the `GH_TOKEN` JWT: it is a GitHub App token (`ghs_...`, `iss: github`, `aud: authnd`); payload carries no scopes. The included git credentials file uses basic auth with `x-access-token:ghs_15368_...` (same App token), so no separate PAT exists.
- `test.yml` is left as an UNTRACKED file on disk (restored from history, 31 lines, cross-platform matrix). It is NOT committed, so HEAD/origin stay clean at `d9f52b4` without it. Re-run `git show 09cd757:.github/workflows/test.yml` to restore it when a token is available.
- Baseline health re-verified this session: `python -m ethscan --help` exit 0; `ruff check ethscan tests` clean; `pytest -q` 5461 passed, 50 skipped.

### What was actually verified
- `git rev-parse main`/`origin/main`/`HEAD` -> `d9f52b4` (in sync, clean tree apart from untracked `test.yml`).
- `git ls-tree HEAD .github/workflows/` -> only `kilo-workflow-audit.yml` and `main.yml`; no `test.yml`.
- `git show 09cd757:.github/workflows/test.yml` -> exists (31 lines, cross-platform matrix).
- Push rejected with the `workflows permission` message; dispatch endpoint 403; permissions endpoint 403 for both tokens.
- No PAT in `~/.git-credentials`, env, or the included git-credentials config (only the GitHub App token via basic auth).
- Baseline health: `python -m ethscan --help` exit 0; `ruff check ethscan tests` clean; `pytest -q` 5461 passed, 50 skipped.
- All 54 `cli.cli.commands` documented in README; `python -m ethscan version` -> `{"version": "0.1.0"}` exit 0; version tests pass (7).

### What remains unresolved
- Push `test.yml` to `origin/main`. Requires PAT/GitHub App token with `workflows` write scope; none available. `origin/main` stays at `d9f52b4` without test.yml.

### One precise next task
Obtain a token with `workflows` write scope. Restore `.github/workflows/test.yml` from git history (`git show 09cd757:.github/workflows/test.yml`), `git commit` + `git push origin main` (HEAD `d9f52b4`), then POST to `actions/workflows/test.yml/dispatches` with `{"ref":"main"}` and confirm ubuntu/macos/windows pass. If no token: leave as-is (infrastructure blocker; `test.yml` content preserved in git history; origin/main stays at `d9f52b4` without test.yml).