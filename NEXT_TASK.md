# Next Task for Agent

## Status (current)
- Working tree: **clean**. Nothing uncommitted.
- Full suite: **3890 passed, 1 skipped** (confirmed). No regressions.
- Project coverage: **99%** (12681 stmts, 70 missed). All remaining misses are provably dead code or require uninstalled optional deps (`paramiko`, `dnspython`).
- `ruff check tests/test_ntp.py`: 4 pre-existing lint issues (unused imports, unsorted block, `SIM222`). Not introduced this session.

## Provably dead / unreachable-in-tests (do not retest; avoid `ethscan/` source changes)
- `ethscan/ntp.py:387` — **dead code**, not reachable. See HANDOFF_NEXT.md for the branch-trace proof.
- `ethscan/mysql.py:107, 111, 150`, `postgresql.py:201`, `resolve.py:188`, `smtp.py:222`, `redis.py:55-56`, `mongodb.py:205-206`, `oracle.py:304-305`, `mssql.py:389-391, 432-433, 455-456`, `radix.py:149-150, 153-154, 158-161, 219-220`, `vuln.py:37, 57-62, 555-556` — all provably unreachable or environment-dependent.

## Next precise task
- **None.** No reachable, dependency-free coverage gap remains.
- Coverage-hunting has reached diminishing returns. Any future task should be a bounded feature or bug fix with evidence, not a coverage gap.