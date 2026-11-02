# Next Task

Obtain a token/PAT with `workflows` (write) scope for this repository, then:

1. Land `.github/workflows/test.yml` on remote/main: `git checkout main && git merge --ff-only preserve/test-workflow && git push origin main` (test.yml is on local branch `preserve/test-workflow`, commit `057eb37`; dnspython is already on remote/main so no conflict).
2. Trigger the `test` workflow via `workflow_dispatch`.
3. Confirm the `test` job passes on ubuntu-latest, macos-latest, windows-latest.

Evidence/constraints:
- `origin/main` == `9b9a571`; `requirements.txt` on remote/main contains `dnspython>=2.0` (pushed this session, unblocked — no workflows touched).
- `test.yml` preserved locally on branch `preserve/test-workflow` (commit `057eb37`, not yet on any remote).
- Local verification: `pytest` 5461 passed / 50 skipped; `ruff check .` clean; `mypy ethscan/` clean (59 files).
- `GH_TOKEN` lacks `workflows` write permission (403) and `pull-requests` write scope (403); `gh pr create` blocked.
- `act` not installed; cannot validate matrix locally.
- Pushing `main` now works because current `main` contains no `.github/workflows/*` changes.

If no such token is available: durable remote state is `origin/main` at `9b9a571` with `dnspython>=2.0`; `test.yml` remains local-only on `preserve/test-workflow`. Treat as infrastructure blocker; no further code change required.
