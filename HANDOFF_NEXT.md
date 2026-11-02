# Status: BLOCKED (infrastructure) - test.yml push requires workflows write scope

### What changed this session
- Documented the `version` command in README features list (was missing; all 54 CLI commands now documented). Verified: `python -m ethscan version` -> `{"version": "0.1.0"}` exit 0; `tests/test_cli.py` version tests pass (7); ruff clean.
- Confirmed `test.yml` remains ABSENT from HEAD (`10c976d`) but PRESERVED in git history (`461e1e1`, `09cd757`, 31 lines).
- Push to `origin/main` not attempted: GitHub App token lacks `workflows` permission (previously confirmed 403); no token with `workflows` write scope available.

### What was actually verified
- `git rev-parse main`/`origin/main`/`HEAD` -> `10c976d` (in sync, clean tree).
- `git ls-tree HEAD .github/workflows/` -> only `kilo-workflow-audit.yml` and `main.yml`; no `test.yml`.
- `git show 09cd757:.github/workflows/test.yml` -> exists (31 lines, cross-platform matrix).
- All 54 `cli.cli.commands` appear as `` `X` command `` in README.
- Baseline health: `python -m ethscan --help` exit 0; `python -m ruff check ethscan tests` clean; `python -m pytest -q` 5461 passed, 50 skipped.

### What remains unresolved
- Push `test.yml` to `origin/main`. Requires PAT/GitHub App token with `workflows` write scope; none available. `origin/main` stays at `10c976d` without test.yml.

### One precise next task
Obtain a token with `workflows` write scope. Restore `.github/workflows/test.yml` from git history (`09cd757`/`461e1e1`), `git push origin main` (HEAD `10c976d`), then trigger `workflow_dispatch` on `test` and confirm ubuntu/macos/windows pass. If no token: leave as-is (infrastructure blocker; `test.yml` content preserved in git history; origin/main stays without test.yml).
