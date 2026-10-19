# Task
Date: 2026-10-19T04:00:00Z
Status: clean baseline (test_hash.py restored and committed)
Branch: main

Completed
- Restored `tests/test_hash.py` (1174 lines, 126 tests) deleted in commit ef8c549. Recovered byte-identical from the `tests/test_hash.py,cover` coverage artifact committed alongside the deletion.
- Committed restored test file (d4c45ce); docs updated to reflect state (bef2c0f).
- Verified baseline: 3904 passed, 1 skipped; 53 CLI commands register; `python -m ethscan --help` and `--version` OK; py_compile clean; ruff reports 44 intentional errors (test_hash.py is ruff-clean).
- `ethscan/hash.py` coverage 98% (remaining misses: MD4-unavailable platform branches lines 34-35, 60, 83; NTLM+PBKDF2+pepper HMAC error path line 226 — environment-dependent).

Current state
- Working tree: clean.
- Lint: 44 intentional errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — unchanged, unsafe to fix.
- Coverage: ethscan source ~99%; hash.py 98%.

Notes
- No new task assigned. Await a genuine new issue/requirement. Do not touch the 44 documented lint violations.
