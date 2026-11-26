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
  2. New independent-oracle probe of `ethscan.vuln.version_in_range` /
     `_version_tuple` (an area NOT in the prior oracle-checked set of
     radix/cidr/target/validate).

## What was actually verified (evidence)
- `python -m pytest -q` -> **49799 passed, 147 skipped, 0 failed** (151s).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 271 files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run --branch --source=ethscan -m pytest -q` then
  `coverage report` -> **TOTAL 100% (16271 stmts, 6160 branches, 0 missing)** on
  Python 3.14.4. The handoff's 100% claim is accurate on this interpreter.
- New oracle probe (`/tmp/probe_version.py`, not committed): 200000 randomized
  numeric dotted-version / range cases (min/max, inclusive/exclusive) compared
  `version_in_range` against `packaging.version.Version` -> **0 mismatches**.
  Confirms `_version_tuple` + `_pad_versions` numeric (length-insensitive)
  semantics and the >4300-digit guard behave correctly.

## Fresh-angle probe (new area, negative result — no defect)
- `vuln.version_in_range` / `_version_tuple` vs `packaging` oracle: 200k cases,
  0 mismatches (numeric versions). This extends oracle coverage beyond the prior
  radix/cidr/target/validate set.
- Inspected `mac.py` (`_is_mac_address`/`_strip_mac_port`/`_normalize_target`/
  `_extract_oui`), `hash._infer_algorithm`, `service.py` banner detection: logic
  is correct on manual adversarial review; no discrepancy reproduced.
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
- NEW this session: `vuln.version_in_range` vs `packaging` oracle — clean.
- Repeating verification-only sessions with no new evidence is explicitly
  discouraged; do not do it again without a concrete new probe or defect.

## Next task (precise, evidence-based)
- Extend the independent-oracle verification to the remaining not-yet-oracle-
  checked PURE helpers, in this order:
  1. `ethscan.mac._is_mac_address` / `_strip_mac_port` / `_normalize_target` /
     `_normalize_mac_for_api` / `_extract_oui` — build a stdlib-only oracle
     (separator-stripping + `int(x,16)` length-12 check) over a matrix of
     valid/invalid MACs, MAC:port, URL-wrapped MACs, IPv4/IPv6, bracketed IPv6,
     and garbage. Confirm `_normalize_target` never raises anything but
     `TargetSpecError`.
  2. `ethscan.geo._normalize_hops` / `_geo_csv_row` — verify hop dict
     normalization and CSV row projection are total over hostile inputs.
- Constraints: do NOT modify `.github/workflows/**`; keep `oracle`/`postgresql`
  empty-target in-band behavior; do not weaken the `cli.py:4316` guard or game the
  coverage metric. Any code change must fix a reproduced defect first (focused
  failing check or oracle mismatch), then rerun the full gate
  (pytest/coverage/mypy/ruff/check_readme). If no defect reproduces, record the
  new negative result and stop — do not fabricate.