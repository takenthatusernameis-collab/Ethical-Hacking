# Next Task for Agent

## Status
`ethscan/ldap.py` coverage task DONE (96% → 100%, 362 stmts, 0 missing). Added 16 targeted tests to `tests/test_ldap.py` covering BER edge cases, parsing branches, _send_recv paths, _build_banner, and markdown referral; ruff passes. Full suite 3813 passed, 1 skipped.

Repository coverage: 12681 statements, 124 missing (99%). No obvious trivial coverage gap stands out immediately (memcached already 100%).

## Next precise task
Identify a specific small module with uncovered lines (e.g. `ethscan/snmp.py` 15 missing, `ethscan/passwords.py` 4, `ethscan/radix.py` 9) and add minimal targeted unit tests to its corresponding test file following existing conventions, without modifying files under `ethscan/`. Prioritize the smallest missing set.

Verification: tests for that module pass; ruff on modified test files passes; full suite remains green (3813 passed, 1 skipped).
