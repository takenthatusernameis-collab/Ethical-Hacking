# Next Task
Date: Mon Nov 16 2026

## Status
`ethscan/memcached.py` partial-branch task completed this session.
- `ethscan/memcached.py`: 263 stmts, 0 miss, 132 branch, **2 BrPart** (was 5: `53->64`, `60->64`, `144->133`, `151->133`, `357->365`). 3 reachable branches closed via existing tests in `tests/test_memcached_branch_gaps.py`; 2 unreachable branches classified and documented in same file.
- `ethscan/ntp.py` previously measured: 314 stmts, 0 miss, 104 branch, **3 BrPart** (`61->74`, `245->243`, `393->400`), 99%. All 3 documented unreachable in `tests/test_ntp_branch_gaps.py` → ntp fully classified, done.
- Full suite: 32128 passed, 146 skipped, 1 preexisting warning. mypy clean (253 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- Targeted memcached tests: `tests/test_memcached.py tests/test_memcached_hostile_sweep.py tests/test_memcached_branch_gaps.py` → **85 passed**; memcached coverage 99% (2 BrPart, both documented unreachable).
- `python -m coverage run --branch -m pytest -q` → **32128 passed, 146 skipped**.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 253 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Updated `tests/test_memcached_branch_gaps.py` (test-only/reversible):
  - Confirmed 3 reachable branch tests pass (53->64, 60->64, 357->365).
  - Removed 2 ineffective tests for unreachable branches (144->133, 151->133).
  - Added docstring classification of 2 unreachable branches with static invariant explanation.
- No production-code changes.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` and `ethscan/subdomains.py` `240->239` remain documented unreachable from prior sessions (not re-measured this session).
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) remain fully classified; no further snmp/nmap work.
- `ethscan/trace.py`, `ethscan/urlcheck.py`, `ethscan/subtake.py`, `ethscan/osdetect.py`, and `ethscan/memcached.py` are now at 0 reachable BrPart (memcached has 2 documented unreachable).

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md history); no test possible.
- `memcached` `144->133` / `151->133`: unreachable by `strip()` invariant (this session).

## Next task
- Continue one module per session by partial-branch count; re-measure with targeted branch coverage before acting; classify reachable vs defensive/unreachable; do not batch modules.
- Precise next: **`ethscan/vuln.py`** (1 BrPart candidate `1036->1029`). Reproduce command:
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.vuln -m pytest tests/test_vuln.py tests/test_vuln_hostile_sweep.py -q && python -m coverage report --show-missing --include='ethscan/vuln.py'`
- If vuln branch is already documented unreachable, classify and move to next candidate (`subdomains.py`).

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.

(End of file - total 43 lines)