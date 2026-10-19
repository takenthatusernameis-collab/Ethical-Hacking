# Task
Date: 2026-10-19T03:55:00Z
Status: test_hash.py restored (green)
Branch: main

Completed
- Restored `tests/test_hash.py` (1174 lines, 126 tests) deleted in commit ef8c549. Recovered byte-identical from the `tests/test_hash.py,cover` coverage artifact committed alongside the deletion.
- Verified baseline: 3904 passed, 1 skipped; 53 CLI commands register; `python -m ethscan --help` and `--version` OK; py_compile clean; ruff still 44 intentional errors (test_hash.py itself is ruff-clean).
- `ethscan/hash.py` coverage improved from 84% (39 miss) to 98% (5 miss) — remaining misses are MD4-unavailable platform branches (lines 34-35, 60, 83) and the NTLM+PBKDF2+pepper HMAC error path (line 226), all environment-dependent.

Current state
- Working tree: clean except for the restored untracked `tests/test_hash.py`.
- Lint: 44 intentional errors (unchanged, none in restored file).
- Coverage: ethscan source ~99% overall; hash.py now 98%.

Notes
- Next: await a genuine new issue/requirement. Do not touch the 44 documented lint violations.