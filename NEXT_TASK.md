# Next Task
Date: Wed Nov 04 2026

## State
- HEAD on origin/main. Working tree has uncommitted change to tests/test_web.py (+60 lines).
- Tests: 5572 passed, 50 skipped. `ruff` clean. `mypy ethscan` clean (59 files).
- web.py coverage 98% (up from 91%).

## Blocker
- None.

## Next task
- Close remaining coverage gaps, starting with `ethscan/mssql.py` (11 uncovered lines: 391-393, 434-435, 457-458, 492-493, 584-585). Add focused tests, re-run `pytest`, `ruff check .`, `mypy ethscan` to verify. Do not commit unless explicitly asked.
