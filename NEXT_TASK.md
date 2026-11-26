## Next task
Extend independent-oracle verification to the remaining not-yet-oracle-checked
PURE helpers (prior oracle set: radix/cidr/target/validate; this session added
vuln.version_in_range — 200k cases vs `packaging`, 0 mismatches; mac — 5
functions, 40k+ cases vs stdlib, 0 mismatches; geo — 3 functions + column
consistency, 8M+ cases vs stdlib, 0 mismatches; hash._infer_algorithm — 1.3M+
cases vs stdlib length oracle, 0 mismatches; target — 8 functions, ~115k cases
vs stdlib oracles, 0 mismatches):

1. `ethscan.service._parse_banner_service` / `_parse_banner_version` — verify
   banner parsing is total over hostile inputs (empty, control chars, very long
   lines, non-ASCII, malformed version strings) and never raises.
   Note: These functions do not yet exist in the codebase; they would need to
   be extracted from `grab_banner`/`run_service` logic first, or the verification
   would target the inline parsing logic in `grab_banner` (lines 162-173).

## Baseline (independently re-verified THIS session on Python 3.14.4)
- `pytest -q` -> 49799 passed, 147 skipped, 0 failed.
- `mypy ethscan/ tests/` -> Success (271 files).
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `check_readme.py` -> 54 commands, 0 drift, exit 0.
- coverage -> TOTAL 100% (16271 stmts, 6160 branches, 0 missing) on 3.14.4.
- No source/test changes made; no demonstrated defect; working tree clean at start.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py:4316` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check or
  oracle mismatch), then rerun the full gate. If nothing reproduces, record the
  new negative result and stop — do not fabricate work or repeat verification-only
  sessions without new evidence.
- Note: `ethscan/mssql.py:591` has a duplicated `# pragma: no cover` comment
  (cosmetic only; code is correct). Not worth a commit on its own.

(End of file - total 43 lines)