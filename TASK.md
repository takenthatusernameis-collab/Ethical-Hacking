# Task
Date: Wed Nov 04 2026

## Current state
- HEAD on origin/main; working tree clean except uncommitted `tests/test_web.py` (+60 lines, new coverage tests).
- Tests: 5572 passed, 50 skipped; `ruff` clean; `mypy ethscan` clean (59 files).
- web.py coverage 98% (up from 91%).

## Blockers
- None.

## Next task
- Close remaining coverage gaps, starting with `ethscan/mssql.py` (11 uncovered lines). Add focused tests, re-run checks, verify green. Repo is otherwise feature-complete.
