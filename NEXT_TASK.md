# Next Task
Date: Wed Nov 04 2026

## State
- HEAD on origin/main. Working tree has uncommitted change to tests/test_ntp.py (+2 lines/tests).
- Tests: 5576 passed, 50 skipped. `ruff` clean. `mypy ethscan` clean (59 files).
- ntp.py coverage 100% (up from 97%).

## Blocker
- None.

## Next task
- Close remaining coverage gaps, starting with `ethscan/mysql.py` (reachable lines 110/307/309/312; unreachable defensives 114/153). Add focused tests, re-run `pytest`, `ruff check .`, `mypy ethscan` to verify. Do not commit unless explicitly asked.

(End of file - total 13 lines)
