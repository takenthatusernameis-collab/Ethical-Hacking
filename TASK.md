# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off.

## Current state (verified)
- `main` and `origin/main` at `448519f` (merged PR #2 for dnspython fix).
- `requirements.txt` on remote/main contains `dnspython>=2.0` (already present).
- `test.yml` exists only on local branch `preserve/test-workflow` at commit `057eb37` (`.github/workflows/test.yml`).
- Local verification: `python -m pytest -q` -> 5461 passed, 50 skipped; `python -m ruff check .` clean; `python -m mypy ethscan/` clean (59 files).
- Cannot push workflow files with current `GH_TOKEN` (403: missing `workflows` write scope). `gh pr create` also blocked (403). `act` not installed.

## Next actions
1. Obtain a PAT with `workflows` (write) scope for this repo.
2. If available: `git checkout main && git merge --ff-only preserve/test-workflow && git push origin main`, then trigger `test` workflow via `workflow_dispatch` and confirm ubuntu/macos/windows pass.
3. If not available: treat as infrastructure blocker. Durable remote state is correct; `test.yml` remains local-only. No code change needed.

## Evidence
- `git log --oneline -3`: 448519f, 9b9a571, c76fb52
- `git branch -a`: preserve/test-workflow local; remotes/origin/main, remotes/origin/fix/dnspython-requirements
- Push attempts show workflows permission required to create/update `.github/workflows/*`.
