# Next Task for Agent

## Status
`ethscan/ping.py` coverage task COMPLETE (now 100%: 203 stmts, 0 missing). Only `tests/test_ping.py` was modified (added 5 targeted unit tests); no files under `ethscan/` were modified. `ethscan/cli.py` coverage task is also effectively complete (99%, only unreachable dead code + `__main__` guard remain).

## Current coverage state
Remaining non-100 modules include `ethscan/hash.py` (96%, 9 missing), `ethscan/ldap.py` (96%, 15 missing), `ethscan/snmp.py` (96%, 15 missing), plus several 97-99%. `ethscan/cli.py` at 99% (21 missing, all unreachable without modifying ethscan/).

## Next precise task
Improve coverage on `ethscan/hash.py` (96% coverage, 9 missing statements: lines 34-35, 60, 83, 109, 226, 238, 308, 320) — add targeted unit tests to `tests/test_hash.py` following existing conventions, without modifying files under `ethscan/`. Verification baseline: full suite 3792 passed, 1 skipped.
