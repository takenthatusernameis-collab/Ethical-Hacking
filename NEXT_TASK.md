# Next Task

Obtain a token/PAT with `workflows` (write) scope for this repository, then:

1. Land `.github/workflows/test.yml` on remote/main: `git push origin main`
   - Local commit `9bb0c34` on `main` already adds `.github/workflows/test.yml`.
   - `origin/main` at `ed7a958`; local `main` is exactly 1 commit ahead; no conflict.
   - `origin/main` at `ed7a958`; `test.yml` absent on remote/main.
2. Trigger the `test` workflow via `workflow_dispatch`.
3. Confirm the `test` job passes on ubuntu-latest, macos-latest, windows-latest.

Evidence/constraints:
- Push rejected: `refusing to allow a GitHub App to create or update workflow .github/workflows/test.yml without workflows permission` (env `GH_TOKEN`/`GITHUB_TOKEN` is a GitHub App token lacking `workflows` write scope).
- `gh pr create` blocked (403 insufficient scope) per prior sessions; `act` not installed.
- Local verification: workflow YAML valid (test job, matrix ubuntu/macos/windows); `ruff check .` All checks passed. `pytest` 5461 passed / 50 skipped. Only change is test.yml addition.
- If no token available: durable local state is commit `9bb0c34` on `main` (test.yml ready to push); `origin/main` stays at `ed7a958`. Treat as infrastructure blocker; no further code change required.
