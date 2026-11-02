# Next Task

Obtain a PAT/token with `workflows` write permission for this repository, then:

- Commit `.github/workflows/test.yml` (currently untracked; restored locally after being deleted at HEAD `35feae0`).
- Push to `main` (`git push origin main`). The workflow runs pytest, `ruff check .`, and `mypy ethscan/` on ubuntu-latest, macos-latest, and windows-latest, triggered by push/PR to main plus `workflow_dispatch`.
- Trigger the workflow via `workflow_dispatch`.
- Confirm the `test` job passes on all three platforms.

Evidence/constraints:
- `test.yml` created locally and verified: YAML parses (single `test` job, 3-OS matrix); `ruff check .` clean; `mypy ethscan/` clean (59 files); `pytest -q` 5458 passed / 53 skipped.
- `test.yml` is NOT committed and NOT pushed.
- `GH_TOKEN` returns 403 on `actions/permissions` — no `workflows` write permission. Prior push rejected for the same reason.
- `act` is not available in this environment, so the matrix cannot be validated locally.
- No token with `workflows` write permission is available in this environment.

If a token cannot be obtained, leave `test.yml` untracked/local and document as an infrastructure blocker; no further code change is required.
