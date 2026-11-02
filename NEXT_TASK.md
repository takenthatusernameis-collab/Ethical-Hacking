# Next Task

Obtain a PAT/token with `workflows` write permission for this repository, then:

1. `git add .github/workflows/test.yml` and commit it (message like "Add cross-platform test workflow").
2. Push to `main` (`git push origin main`). Workflow runs ruff, mypy (ethscan/), pytest on ubuntu-latest/macos-latest/windows-latest on push/PR to main and workflow_dispatch.
3. Trigger via `workflow_dispatch`.
4. Confirm `test` job passes on all three platforms.

Evidence/constraints:
- test.yml restored locally from git history (deleted at 35feae0), valid YAML, matrix configured.
- Local verification: ruff clean; mypy clean (59 files); pytest 5458 passed/53 skipped.
- test.yml untracked, not committed, not pushed.
- GH_TOKEN lacks workflows write permission (403 on actions/permissions). Pushes to .github/workflows/* rejected.
- No PAT with workflows write permission available in this environment.
- act not installed; cannot validate matrix locally.

If unavailable, leave test.yml untracked/local and treat as infrastructure blocker.
