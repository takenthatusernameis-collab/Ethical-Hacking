## Next task
Extend independent-oracle verification to the remaining not-yet-oracle-checked
PURE helpers (prior oracle set: radix/cidr/target/validate; this session added
vuln.version_in_range — 200k cases vs `packaging`, 0 mismatches):

1. `ethscan.mac._is_mac_address` / `_strip_mac_port` / `_normalize_target` /
   `_normalize_mac_for_api` / `_extract_oui` — stdlib-only oracle over a matrix
   of valid/invalid MACs, MAC:port, URL-wrapped MACs, IPv4/IPv6, bracketed IPv6,
   garbage. Assert `_normalize_target` raises only `TargetSpecError`.
2. `ethscan.geo._normalize_hops` / `_geo_csv_row` — totality over hostile inputs.

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