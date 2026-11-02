# Next Task

Obtain a token/PAT with `workflows` (write) scope for this repository, then:

1. Land `.github/workflows/test.yml` on remote/main: `git push origin main`
   - Local commit `ec824d7` on `main` already adds `.github/workflows/test.yml` (from `preserve/test-workflow` @ `057eb37`).
   - `origin/main` at `043c93e`; local `main` is exactly 1 commit ahead; dnspython already on remote/main, no conflict.
   - `git merge --ff-only preserve/test-workflow` will NOT work (main advanced independently); do not use it.
2. Trigger the `test` workflow via `workflow_dispatch`.
3. Confirm the `test` job passes on ubuntu-latest, macos-latest, windows-latest.

Evidence/constraints:
- Push attempt rejected: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (token lacks `workflows` write scope).
- `gh pr create` blocked (403 insufficient scope); `act` not installed.
- Local verification: workflow YAML valid; `ruff check .` clean; prior `pytest` 5461 passed / 50 skipped; `mypy ethscan/` clean (59 files). Source unchanged by `ec824d7`.
- If no token available: durable local state is commit `ec824d7` (test.yml ready to push); `origin/main` stays at `043c93e`. Treat as infrastructure blocker; no further code change required.
