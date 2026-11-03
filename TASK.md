# Task
Land `.github/workflows/test.yml` on remote/main if possible; otherwise record durable state and hand off. If the workflows push is blocked, complete a bounded, verifiable code task consistent with repo conventions instead.

## Current state (verified this session)
- `HEAD` = `origin/main` = `7e00221`; working tree clean except uncommitted FTP changes (see below).
- `.github/workflows/test.yml` ABSENT from HEAD; preserved in git history at `c2e6378` (blob `3d7a18f`).
- `GH_TOKEN`/`GITHUB_TOKEN` = GitHub App token lacking `workflows` write scope → deterministic 403 on workflow files. No PAT with `workflows` scope available.
- Baseline health: `ruff check ethscan tests` clean; `pytest` 5512 passed / 53 skipped (exit 0).

## What changed this session (bounded code task, fallback path)
- `ethscan/ftp.py`: FTP version flagging (`_assess_ftp_version`, findings in `run_ftp`, markdown `## Findings`).
- `tests/test_ftp.py`: +11 tests.
- `README.md`: FTP section updated.
- All changes are UNCOMMITTED (working tree dirty).

## Next actions
1. Commit & push the FTP version-flagging changes to `origin/main`.
2. Obtain a `workflows`-write token; if available restore/push `test.yml` from `c2e6378` and trigger it.
3. If no token: infra blocker; durable state = FTP change + verified tests + `test.yml` in git history.
