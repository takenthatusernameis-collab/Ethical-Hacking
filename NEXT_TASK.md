# Next Task for Agent

## Status
- `ethscan/main.py` coverage → 100% (3/3), added 1 test to `tests/test_main.py` using `runpy.run_module("ethscan.main", run_name="__main__")` with `ethscan.cli.cli` patched. Full suite: 3860 passed, 1 skipped. ruff on modified test files introduces no new errors.
- Overall coverage: 81 missing statements across audited modules (down from previous baseline).

## Provably dead code (intentionally left uncovered — do not retest)
- `ethscan/ntp.py:387` — `if mon_resp.get("error"):` inside `else` of same check at line 367; `mon_resp` never mutated between checks → always False.
- `ethscan/postgresql.py:201` — `if not msg_type: break` where `msg_type = data[pos:pos + 1]` and loop condition is `pos < n`; 1-byte slice always truthy.
- `ethscan/smtp.py:222` — `sock.close()` in outer `except`; `sock` non-None only if `_connect()` succeeded, but then only inner try/except runs (catches `socket.timeout`/`OSError` and returns). Nothing between can raise those exceptions.

## Next precise task
Select the module with the smallest number of missing lines among remaining achievable (non-dead-code) gaps: ftp.py (2 missing: lines 145-146), mongodb.py (2 missing: 205-206), oracle.py (2 missing: 304-305), redis.py (2 missing: 55-56), mysql.py (3 missing: 107, 111, 150), snmp.py (5 missing: 247, 319, 324, 357, 406), hash.py (5 missing: 34-35, 60, 83, 226), s3.py (6 missing: 136, 145-146, 234-236), dnssec.py (6 missing: 11-16), ssl.py (4 missing: 133-136), resolve.py (4 missing: 11-13, 188), mssql.py (8 missing: 389-391, 404, 432-433, 455-456), radix.py (9 missing: 149-150, 153-154, 158-161, 219-220), netbios.py (10 missing: 275, 342, 383, 390, 410-416, 615, 645). Add minimal targeted unit tests to the corresponding test file without modifying `ethscan/`, focusing on practical paths. For truly unreachable defensive branches, document in test context but prefer achievable coverage.

Verification: targeted module tests pass; ruff on modified test files passes; full suite remains ≥3860 passed, 1 skipped.