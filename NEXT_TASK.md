# Next Task for Agent

## Status
- `ethscan/passwords.py` coverage → 100% (135/135), added 6 new tests to `tests/test_passwords.py`. Full suite: 3849 passed, 1 skipped. ruff passes on modified tests.
- Overall coverage: 110 missing statements (down from 124).

## Next precise task
Select the module with the smallest number of missing lines among remaining: trace.py (1), postgresql.py (1), smtp.py (1), redis.py (2), service.py (3), resolve.py/ssl.py (4), snmp.py (5), s3.py (6), radix.py (9), vuln.py (9). Add minimal targeted unit tests to the corresponding test file without modifying `ethscan/`, focusing on practical paths. For truly unreachable defensive branches, document in test context if needed but prefer achievable coverage.

Verification: targeted module tests pass; ruff on modified test files passes; full suite remains ≥3849 passed, 1 skipped.
