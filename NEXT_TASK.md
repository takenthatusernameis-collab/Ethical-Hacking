# Next Task
Date: Mon Nov 16 2026

## Status
- `ethscan/vuln.py` and `ethscan/subdomains.py` fully classified this session.
- `ethscan/vuln.py`: 476 stmts, 0 miss, 244 branch, **1 BrPart** (`1036->1029`, documented unreachable). 5 reachable BrPart closed via existing tests in `tests/test_vuln_branch_gaps.py` (950->955, 977->984, 1031->1029) and `tests/test_vuln_formatter_hostile_sweep.py` (1147->1149, 1259->1270).
- `ethscan/subdomains.py`: 178 stmts, 0 miss, 68 branch, **0 BrPart** — 100% branch coverage. The last BrPart (`240->239`) was classified **reachable** and closed with `test_run_subdomains_recursive_duplicate_hostname_skipped`.
- Full suite: 32129 passed, 146 skipped, 1 preexisting warning. mypy clean (253 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- Targeted vuln: `tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_branch_gaps.py tests/test_vuln_formatter_hostile_sweep.py` → **247 passed**; vuln coverage 99% (1 BrPart, documented unreachable).
- Targeted subdomains: `tests/test_subdomains.py tests/test_subdomains_hostile_sweep.py tests/test_subdomains_branch_gaps.py` → **57 passed**; subdomains coverage 100% (0 BrPart).
- `python -m coverage run --branch -m pytest -q` → **32129 passed, 146 skipped**.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 253 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Updated `tests/test_vuln_branch_gaps.py` (test-only/reversible):
  - Rewrote module docstring to reflect final state: 5 reachable branches closed (3 in this file, 2 in the hostile-sweep file), 1 unreachable documented.
  - No test logic changed; the 3 existing tests already covered their branches.
- Updated `tests/test_subdomains_branch_gaps.py` (test-only/reversible):
  - Added `test_run_subdomains_recursive_duplicate_hostname_skipped` covering `240->239`: two depth-0 labels resolve to the same hostname, so the derived `base_domains` list carries a duplicate; on the second depth-1 iteration the emitted hostnames are already in `seen_hostnames`, so the guard at line 240 is False and the branch 240->239 is taken.
  - No production-code changes.

## What remains unresolved
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) remain fully classified; no further snmp/nmap work.
- `ethscan/trace.py`, `ethscan/urlcheck.py`, `ethscan/subtake.py`, `ethscan/osdetect.py`, `ethscan/memcached.py` (2 documented unreachable), `ethscan/vuln.py` (1 documented unreachable), and `ethscan/subdomains.py` (0 BrPart) are now at 0 reachable BrPart.
- `ethscan/smtp.py` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md history); no test possible.
- `memcached` `144->133` / `151->133`: unreachable by `strip()` invariant.
- `vuln` `1036->1029`: unreachable by depth invariant (recursive call only happens when `depth < max_depth`, but callee returns `{}` only when `depth > max_depth` — contradiction).
- `subdomains` `240->239`: reachable; closed this session.

## Next task
- Continue one module per session by partial-branch count; re-measure with targeted branch coverage before acting; classify reachable vs defensive/unreachable; do not batch modules.
- Remaining modules with BrPart candidates to re-measure: `ethscan/snmp.py` (2 BrPart, both documented unreachable), `ethscan/nmap.py` (1 BrPart, documented unreachable). Both are already classified — re-measure to confirm 0 reachable BrPart, then the branch-coverage campaign is complete.
- If both confirm fully classified, the repository is fully green on branch coverage.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.

(End of file - total 47 lines)