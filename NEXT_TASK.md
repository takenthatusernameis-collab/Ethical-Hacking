# Next Task

## Status: CLOSED (Sun Nov 08 2026)
No actionable prior assignment. README `hash --iterations`/PBKDF2 doc gap fixed (evidence-based); baseline re-verified green.

## Candidate
None pending. If future work is needed, pick a single high-value, verifiable improvement only when reproduced/justified (do not speculate).

## Constraints
- Do not re-audit `--out`/`--init` routing or revisit closed flakiness without a reproduction.
- Do not weaken safety controls or turn maintenance into an infrastructure project.
- Do not make speculative changes; preserve the working baseline.
- If order-dependent flakiness reappears: reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups.

(End of file - total 15 lines)
