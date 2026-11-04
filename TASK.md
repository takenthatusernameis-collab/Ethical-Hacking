# Task
Date: Wed Nov 04 2026

## Current state
- HEAD `1c41318` pushed to origin/main; working tree has one unstaged change (tests/test_ftp.py fix, not committed).
- Tests: 5561 passed, 50 skipped (was 5560 passed + 1 failed before fix); ruff clean; mypy clean (59 files).

## Blockers
- `.github/workflows/test.yml` blocked by token lacking `workflows` permission (403).

## Next task
If a workflows-scoped token becomes available: author `.github/workflows/test.yml` (ruff + mypy + pytest on push/PR), commit/push, re-verify. Otherwise repo green and feature-complete.
