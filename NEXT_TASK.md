# Next Task

Obtain a PAT/token with `workflows` write permission for this repository, then:

- Push the existing local commit `c2c43d2` (`.github/workflows/test.yml`) to `main` (`git push origin main`). It runs pytest, `ruff check .`, and `mypy ethscan/` on ubuntu-latest, macos-latest, and windows-latest, triggered by `workflow_dispatch` (plus push/PR to main).
- Trigger the workflow via `workflow_dispatch`.
- Confirm the `test` job passes on all three platforms.

Evidence/constraints:
- `test.yml` created and committed locally as `c2c43d2`; working tree otherwise clean. YAML validated with pyyaml: parses OK.
- Baseline CI steps verified locally this session: `ruff check .` clean; `mypy ethscan/` clean (59 files); `pytest -q` 5458 passed / 53 skipped.
- `act` is not available in this environment, so the matrix cannot be validated locally.
- No token with `workflows` write permission is available in this environment.
- Push was attempted and rejected: missing `workflows` permission to create/update the workflow file.

If a token cannot be obtained, leave the local commit `c2c43d2` in place and document it as an infrastructure blocker; no further code change is required.
