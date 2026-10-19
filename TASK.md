# Task
Date: 2026-10-19T07:06:00Z
Status: dead-code removal in ethscan/vuln.py (working tree, uncommitted)
Branch: main

Completed
- Removed provably-dead duplicate `_hashlib_name`/`_compute_peppered_hash` definitions in `ethscan/vuln.py` (committed 5e2fe0f).
- Removed provably-dead IPv4 loop + `ipv4_pattern` in `_extract_hosts_from_banner` (`ethscan/vuln.py:498-513`): `hostname_pattern` matches all IPv4 dotted-quads and adds them to `seen` first, so the `if ip not in seen` body never executed. Behavior-preserving; IPs still captured via the hostname loop. 10 deletions, vuln.py only.
- Verified: `__code__.co_firstlineno` reports live definitions; full suite `python -m pytest -q` -> 3906 passed, 1 skipped; `python -m ruff check ethscan tests` -> 44 errors unchanged; `python -m py_compile ethscan/*.py` -> clean; `git diff --stat` -> only vuln.py, 10 deletions.
- NOT committed (no explicit commit request). Change sits in working tree.

Current state
- Working tree: modified (ethscan/vuln.py, -10 lines).
- Lint: 44 intentional errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — unchanged.
- Coverage: ethscan source ~99%; hash.py 98%.

Notes
- No new task assigned. Await a genuine new issue/requirement. Do not touch the 44 documented lint violations.
- All remaining ethscan coverage gaps are environmental, network-dependent, unreachable defensive code (catalogued in HANDOFF_NEXT.md). No bounded, behavior-preserving, verifiable task remains within constraints other than further provably-dead-code removal with definitive proof.