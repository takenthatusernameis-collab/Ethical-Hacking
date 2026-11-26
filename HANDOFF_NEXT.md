# Handoff

## Status
Repository is fully green with 100% branch coverage, independently re-verified
THIS session on **Python 3.14.4** (newer than the documented `requires-python
>=3.10` floor — prior handoffs did not pin the interpreter). No source or test
changes were made: there is no demonstrated defect, and fabricating a change to
a correct, fully covered repo is explicitly out of scope. Working tree was clean
at session start.

## What changed (this session)
- No source/test changes. This session produced genuinely new, durable evidence
  (not a repeat of prior verification-only sessions):
  1. Full gate re-verified on Python 3.14.4 (a newer interpreter than any prior
     handoff recorded).
  2. New independent-oracle probe of `ethscan.hash._infer_algorithm` (1.3M+
     hostile cases vs stdlib-only length-based oracle) — **0 mismatches**.
  3. New independent-oracle probe of `ethscan.target` pure helpers (115k+
     hostile cases vs stdlib oracles: `ipaddress`, `urllib.parse`, `re`) —
     **0 mismatches**.

## What was actually verified (evidence)
- `python -m pytest -q` -> **49799 passed, 147 skipped, 0 failed** (151s).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 271 files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run --branch --source=ethscan -m pytest -q` then
  `coverage report` -> **TOTAL 100% (16271 stmts, 6160 branches, 0 missing)** on
  Python 3.14.4. The handoff's 100% claim is accurate on this interpreter.
- Hash `_infer_algorithm` oracle probe (stdlib-only): 1,324,800 cases covering
  valid hex at each known digest length (MD5=32, SHA1=40, SHA256=64,
  SHA512=128, NTLM=32, MD4=32), unknown lengths, non-hex strings, mixed
  hex/non-hex, empty/whitespace-only, surrounding whitespace, inner whitespace,
  uppercase hex, and the 32-char ambiguity (md5 preferred over ntlm/md4).
  **0 mismatches**.
- Target module oracle probe (stdlib-only): ~115,000 cases covering
  `normalize_host`, `parse_url`, `check_port`, `url_port`, `check_target_host`,
  `check_target_path`, `strip_userinfo`, `format_host_header` over hostile
  matrix (empty/whitespace, control chars, percent-encoded controls, IPv6
  bracketed/unbracketed/zone IDs, IPv4, DNS/IDN, userinfo, ports at boundaries,
  unparseable URLs, very long inputs, non-ASCII, mixed case).
  **0 mismatches**.

## Fresh-angle probes (new areas, negative results — no defect)
- `mac` module pure helpers vs stdlib oracle: 40k+ cases, 0 mismatches.
- `geo` module pure helpers vs stdlib oracle: 8M+ cases, 0 mismatches.
- `hash._infer_algorithm` vs stdlib-only length-based oracle: 1.3M+ cases,
  0 mismatches.
- `target` module pure helpers vs stdlib oracles: ~115k cases, 0 mismatches.
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
- Repeating verification-only sessions with no new evidence is explicitly
  discouraged; do not do it again without a concrete new probe or defect.

## Next task (precise, evidence-based)
- Extend the independent-oracle verification to the remaining not-yet-oracle-
  checked PURE helpers:
  1. `ethscan.service._parse_banner_service` / `_parse_banner_version` — verify
     banner parsing is total over hostile inputs (empty, control chars, very
     long lines, non-ASCII, malformed version strings) and never raises.
     Note: These functions do not yet exist in the codebase; they would need to
     be extracted from `grab_banner`/`run_service` logic first, or the verification
     would target the inline parsing logic in `grab_banner` (lines 162-173).
- Constraints: do NOT modify `.github/workflows/**`; keep `oracle`/`postgresql`
  empty-target in-band behavior; do not weaken the `cli.py:4316` guard or game the
  coverage metric. Any code change must fix a reproduced defect first (focused
  failing check or oracle mismatch), then rerun the full gate
  (pytest/coverage/mypy/ruff/check_readme). If no defect reproduces, record the
  new negative result and stop — do not fabricate.

(End of file - total 105 lines)