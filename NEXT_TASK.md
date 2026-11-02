# Next Task

Obtain a token/PAT with `workflows` (write) and `pull-requests` (write) scope for this repository, then:

1. Land `.github/workflows/test.yml` on remote/main (currently committed locally as `057eb37` but push-blocked).
2. Merge the already-pushed branch `fix/dnspython-requirements` (commit `c67f0be`) into `main` — it carries the `dnspython>=2.0` requirements addition that un-skips 3 DNS tests on CI.
3. Trigger the `test` workflow via `workflow_dispatch`.
4. Confirm the `test` job passes on ubuntu-latest, macos-latest, windows-latest.

Evidence/constraints:
- `requirements.txt` now includes `dnspython>=2.0`; local full suite 5461 passed / 50 skipped (all remaining skips are intentional sweep exclusions).
- Local verification: `ruff check .` clean; `mypy ethscan/` clean (59 files).
- `test.yml` restored locally from git history (deleted at `35feae0`), valid YAML, matrix configured.
- `GH_TOKEN` lacks `workflows` write permission (403 on actions/permissions) — pushes to `.github/workflows/*` rejected.
- `GH_TOKEN` lacks `pull-requests` write scope (403 on `createPullRequest`) — `gh pr create` fails.
- `fix/dnspython-requirements` is already on the remote (no workflows touched), so only a token with `pull-requests` write is needed to merge it.
- `act` not installed; cannot validate the matrix locally.

If no such token is available, the durable remote state is the `fix/dnspython-requirements` branch; `test.yml` remains local-only on `main`. Treat as infrastructure blocker.

(End of file - total 24 lines)