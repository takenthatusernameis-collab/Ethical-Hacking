# Task
Date: 2026-10-19T05:20:00Z
Status: dead-code removal committed (5e2fe0f)
Branch: main

Completed
- Removed provably-dead duplicate `_hashlib_name`/`_compute_peppered_hash` definitions in `ethscan/vuln.py` (original lines 34-65, overridden at import by identical live definitions at lines 343/348).
- Verified: `__code__.co_firstlineno` now reports 343/348; full suite `python -m pytest -q` -> 3906 passed, 1 skipped; `python -m ruff check ethscan tests` -> 44 errors unchanged; `git diff --stat` -> only vuln.py, 34 deletions.
- Committed as 5e2fe0f.

Current state
- Working tree: clean.
- Lint: 44 intentional errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — unchanged.
- Coverage: ethscan source ~99%; hash.py 98%.

Notes
- No new task assigned. Await a genuine new issue/requirement. Do not touch the 44 documented lint violations.
- All remaining ethscan coverage gaps are environmental, network-dependent, unreachable defensive code (catalogued in HANDOFF_NEXT.md). No bounded, behavior-preserving, verifiable task remains within constraints.