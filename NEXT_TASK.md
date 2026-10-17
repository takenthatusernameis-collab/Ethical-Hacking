# Next Task for Agent

## Status (current)
- `ethscan/__main__.py` → 100%; `ethscan/main.py` → 100%.
- `ethscan/snmp.py` → 100%; `ethscan/netbios.py` → 100% (covered by tests added/committed).
- `ethscan/mssql.py` → 98% (7 missing, provably unreachable; line 404 covered).
- `ethscan/radix.py` → 97% (9 missing, provably unreachable).
- `ethscan/cli.py` → 99% (21 missing, unreachable-in-tests).
- `ethscan/hash.py` → 84% (39 missing) after this session's test addition.
- Full suite: **3888 passed, 1 skipped** (confirmed).
- Working tree: `tests/test_cli.py` modified (62 insertions), **not committed** (do not commit unless explicitly asked).

## Provably dead / unreachable-in-tests (do not retest; avoid `ethscan/` source changes)
As previously documented:
- `mssql.py`: 389-391, 432-433, 455-456
- `radix.py`: 149-150, 153-154, 158-161, 219-220
- `cli.py`: 607-635 (superseded hash function; active is `hash_cmd`), 4639 (`__main__` guard not triggered by tests)
- `hash.py`: 226, 238 — **newly confirmed provably unreachable**. `_compute_pbkdf2_hash` (line 167) raises `ValueError("Algorithm 'ntlm' does not support PBKDF2 (no hashlib name).")` *before* the HMAC layer at 226/238 is reached, because NTLM has no hashlib name. Verified empirically: running the new test in isolation does NOT execute lines 226/238. Do not attempt to cover them.

## Environment-dependent gaps (not coverable here)
Missing optional deps confirmed absent: `paramiko` (affects `brute.py:15`, `smb.py` SSH paths), `dnspython` (affects `dns.py:155`, `dnssec.py:11-16`). These `except ImportError` branches cannot be exercised without installing those packages. Do not install them unless the task explicitly requires it.

## This session's change
- Added `test_hash_check_ntlm_iterations_pepper_error` at `tests/test_cli.py:13401` (62 lines). Exercises the reachable defensive error path in `ethscan.hash.run_check` where PBKDF2 iterations + pepper are combined with a non-hashlib-backed algorithm (NTLM). Covers 8 genuinely reachable lines in `hash.py` (217, 223-225, 229-233, 235-250 region). No source change, no behavior change.
- Verified: new test passes; full suite 3888 passed/1 skipped; `ruff check tests/test_cli.py` shows no new violations (all 12 errors are pre-existing).

## Next precise task
**Recommended:** Add a small targeted test for a *reachable* defensive path in `ethscan/vuln.py`, which still has 9 missing lines (37, 57-62, 555-556, 904, 1047). Evidence-based reachability findings:
- **Lines 904 and 1047 are reachable.** Line 904 is `return {}` inside `_recursive_scan` when `depth > max_depth`; line 1047 is the final `return ""` fallback in a finding-description helper. Both are defensive guards that can be triggered via the `vuln` CLI with `--recursive` and appropriate inputs.
- **Lines 37, 57-62** are the `_hashlib_name`/`_compute_peppered_hash` guards — provably unreachable (same reasoning as `hash.py:226/238`); NTLM/pepper edge cases raise earlier. Do not target these.
- **Lines 555-556** — need verification of reachability before targeting.

Suggested test: invoke `vuln` via `CliRunner` with `--recursive` and a `--max-depth` of 0 (or inputs that force `depth > max_depth`) to cover line 904, and a vuln finding lacking all description fields to cover line 1047. Bound to <100 lines. Verify with focused tests; run full suite if safe.

Alternative (lower priority): audit `cli.py` for a single concrete reachable edge case not currently tested (e.g. a specific validation error or option combination), avoiding the documented unreachable regions (607-635, 4639).

## Verification approach
- Run targeted tests for the chosen module/feature.
- Ensure no new ruff violations in modified files only.
- Do not modify `ethscan/` source unless strictly necessary and with justification.
- Full suite not required if change is localized and safe, but acceptable.

Constraints: Preserve working baseline. Smallest reversible change. No parallel redesign. Proportionate handling.