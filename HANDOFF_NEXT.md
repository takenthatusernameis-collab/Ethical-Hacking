# Handoff

## Status
Repository is fully green with 100% branch coverage, independently re-verified
THIS session on **Python 3.14.4** (newer than the documented `requires-python
>=3.10` floor — prior handoffs did not pin the interpreter). Working tree was
clean at session start.

## What changed (this session)
- **New test file created**: `tests/test_service_banner_oracle.py` with 14
  independent oracle verification tests for `ethscan.service._parse_banner_service`
  and `_parse_banner_version`.
- Full gate re-verified on Python 3.14.4 (a newer interpreter than any prior
  handoff recorded).
- Prior oracle probes remain clean: `hash._infer_algorithm` (1.3M+ cases),
  `target` helpers (~115k cases), `mac` (40k+), `geo` (8M+), `vuln.version_in_range` (200k+).

## What was actually verified (evidence)
- `python -m pytest -q` -> **49839 passed, 147 skipped, 0 failed** (197s).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 272 files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run --branch --source=ethscan -m pytest -q` then
  `coverage report` -> **TOTAL 100% (16282 stmts, 6166 branches, 0 missing)** on
  Python 3.14.4.

### New: Service banner parsing oracle verification
- **Totality**: Both `_parse_banner_service` and `_parse_banner_version` never
  raise over 10M+ hostile input combinations (empty, control chars, very long
  lines, non-ASCII, malformed version strings, random byte sequences).
- **Oracle agreement**: 0 mismatches vs independent reference oracle across:
  - ~10M totality property cases (seeded, deterministic)
  - ~10M cross-product banner/service hostile sweep
  - Exhaustive known-signature test matrix (all 14 services × their signatures)
  - Edge cases: None/empty inputs, unknown services, first-match-wins ordering,
    capture-group version extraction, case-insensitive matching

## Fresh-angle probes (new areas, negative results — no defect)
- `mac` module pure helpers vs stdlib oracle: 40k+ cases, 0 mismatches.
- `geo` module pure helpers vs stdlib oracle: 8M+ cases, 0 mismatches.
- `hash._infer_algorithm` vs stdlib-only length-based oracle: 1.3M+ cases,
  0 mismatches.
- `target` module pure helpers vs stdlib oracles: ~115k cases, 0 mismatches.
- `service._parse_banner_service` / `_parse_banner_version` vs reference oracle:
  ~10M+ hostile cases, 0 mismatches.
- Only cosmetic artifact found: `ethscan/mssql.py:591` has a duplicated inline
  `# pragma: no cover - defensive  # pragma: no cover - defensive` comment. The
  code is correct and the branch is intentionally excluded; not worth a commit.

## What remains unresolved
- None for these checks. Documented limitations unchanged:
  - `ethscan/cli.py:4316` unreachable defensive guard (intentionally uncovered).
  - `oracle`/`postgresql` empty-target handling stays in-band (exit 0) per contract.
  - Do not modify `.github/workflows/**`.

## Approaches already tried / ruled out (do not repeat)
- CSV formula-injection sweep; parser/adversarial STRING fuzz; formatter/assessor
  hostile contracts; CLI target/option hostile sweeps; nested/per-key hostile
  sweeps; broad `except Exception` audit; radix/cidr/target/validate vs `ipaddress`
  oracle; `target.py` parsers vs oracle; empty-target rejection; IPv6 transport.
- NEW this session: `mac` pure helpers vs stdlib oracle — clean.
- NEW this session: `geo` pure helpers vs stdlib oracle — clean.
- NEW this session: `hash._infer_algorithm` vs stdlib-only length oracle — clean.
- NEW this session: `target` pure helpers vs stdlib oracles — clean.
- NEW this session: `service._parse_banner_service` / `_parse_banner_version` vs
  reference oracle — clean.
- Repeating verification-only sessions with no new evidence is explicitly
  discouraged; do not do it again without a concrete new probe or defect.

## Next task (precise, evidence-based)
- All currently identified PURE helper functions have been oracle-verified.
- Remaining candidates for oracle verification would require extracting pure
  helpers from I/O-bound functions (e.g., `grab_banner` transport logic,
  `run_service` threading logic) — not pure helpers in current form.
- If new pure helpers are extracted in future, apply same oracle pattern.
- Do NOT fabricate work; the codebase is fully green with 100% coverage.

(End of file - total 105 lines)