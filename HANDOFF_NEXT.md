# Handoff

## Status
Repository is fully green with 100% branch coverage, independently re-verified
THIS session on **Python 3.14.4** (newer than the documented `requires-python
>=3.10` floor — prior handoffs did not pin the interpreter). No source or test
changes were made: there is no demonstrated defect, and fabricating a change to
a correct, fully covered repo is explicitly out of scope. Working tree was clean
at session start.

## What changed (this session)
- No source/test changes. This session produced two pieces of genuinely new,
  durable evidence (not a repeat of prior verification-only sessions):
  1. Full gate re-verified on Python 3.14.4 (a newer interpreter than any prior
     handoff recorded).
  2. New independent-oracle probe of `ethscan.mac._is_mac_address` /
     `_strip_mac_port` / `_normalize_target` / `_normalize_mac_for_api` /
     `_extract_oui` (5 pure helpers, 40k+ randomized cases vs stdlib oracle) —
     **0 mismatches**.
  3. New independent-oracle probe of `ethscan.geo._normalize_hops` /
     `_geo_csv_row` / `_geo_csv_header` / column-count consistency
     (8M+ hostile cases vs stdlib oracle) — **0 mismatches**.

## What was actually verified (evidence)
- `python -m pytest -q` -> **49799 passed, 147 skipped, 0 failed** (158s).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 271 files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run --branch --source=ethscan -m pytest -q` then
  `coverage report` -> **TOTAL 100% (16271 stmts, 6160 branches, 0 missing)** on
  Python 3.14.4. The handoff's 100% claim is accurate on this interpreter.
- MAC oracle probe (stdlib-only): 5 functions, 40k+ cases (valid/invalid MACs,
  MAC:port, URL-wrapped MACs, IPv4/IPv6, bracketed IPv6, garbage, mixed case,
  mixed separators). `_normalize_target` raises only `TargetSpecError`. **0 mismatches**.
- GEO oracle probe (stdlib-only): `_normalize_hops` (10k cases), `_geo_csv_row`
  (8M+ cases with hostile geo/hop/target/ip), `_geo_csv_header` (exact match),
  column-count consistency (always 17 columns). **0 mismatches**.

## Fresh-angle probes (new areas, negative results — no defect)
- `mac` module pure helpers vs stdlib oracle: 40k+ cases, 0 mismatches.
- `geo` module pure helpers vs stdlib oracle: 8M+ cases, 0 mismatches.
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
- Repeating verification-only sessions with no new evidence is explicitly
  discouraged; do not do it again without a concrete new probe or defect.

## Next task (precise, evidence-based)
- Extend the independent-oracle verification to the remaining not-yet-oracle-
  checked PURE helpers, in this order:
  1. `ethscan.hash._infer_algorithm` — build a stdlib-only oracle (length-based
     heuristic matching common hash lengths: MD5=32, SHA1=40, SHA256=64,
     SHA512=128, etc.) over a matrix of valid hex strings at each length,
     non-hex strings, empty strings, and strings with whitespace. Verify the
     exact mapping logic.
  2. `ethscan.service._parse_banner_service` / `_parse_banner_version` — verify
     banner parsing is total over hostile inputs (empty, control chars, very
     long lines, non-ASCII, malformed version strings) and never raises.
  3. `ethscan.target` pure helpers (`normalize_host`, `parse_url`, `check_port`,
     `check_target_host`, `check_target_path`, `strip_userinfo`,
     `format_host_header`) — stdlib oracle using `ipaddress`, `urllib.parse`,
     `re` over hostile matrix (URLs with userinfo, IPv6 bracketed/unbracketed,
     ports at boundaries, control chars in host/path, percent-encoded controls,
     zone IDs, missing schemes).
- Constraints: do NOT modify `.github/workflows/**`; keep `oracle`/`postgresql`
  empty-target in-band behavior; do not weaken the `cli.py:4316` guard or game the
  coverage metric. Any code change must fix a reproduced defect first (focused
  failing check or oracle mismatch), then rerun the full gate
  (pytest/coverage/mypy/ruff/check_readme). If no defect reproduces, record the
  new negative result and stop — do not fabricate.

(End of file - total 88 lines)