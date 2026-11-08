# Next Task

## Status: CLOSED (Sun Nov 08 2026)
No actionable prior assignment; baseline re-verified green this session.

## Candidate
None pending. If a future session needs bounded work, pick a single high-value, verifiable improvement (e.g., a small CLI/doc inconsistency found by evidence, or a focused regression test for an observed gap) — only when reproduced/justified.

## Constraints
- Do not re-audit `--out`/`--init` routing or revisit closed flakiness without a reproduction.
- Do not weaken safety controls or turn maintenance into an infrastructure project.
- Do not make speculative changes; preserve the working baseline.
- If order-dependent flakiness reappears: reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups.

(End of file - total 15 lines)
