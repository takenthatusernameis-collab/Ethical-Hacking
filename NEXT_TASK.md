# Next Task

Obtain a PAT/token with `workflows` write permission for this repository, then:

- Commit `.github/workflows/test.yml` (restored this session; uncommitted). It runs pytest, `ruff check .`, and `mypy ethscan/` on ubuntu-latest, macos-latest, and windows-latest, triggered by `workflow_dispatch` (plus push/PR to main).
- Push to main and trigger the workflow via `workflow_dispatch`.
- Confirm the `test` job passes on all three platforms.

Evidence/constraints:
- `test.yml` restored exactly as deleted (was removed in `e3d6653`, never restored). YAML validated with pyyaml: parses OK.
- Baseline CI steps verified locally this session: `ruff check .` clean; `mypy ethscan/` clean (59 files); `pytest -q` 5461 passed / 50 skipped.
- `act` is not available in this environment, so the matrix cannot be validated locally.
- No token with `workflows` write permission is available in this environment.
- Do not commit unless explicitly asked; the restored file is intentionally left uncommitted pending a token.

If a token cannot be obtained, leave the restored file in place and document it as an infrastructure blocker; no further code change is required.
