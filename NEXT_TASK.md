# Next Task
Date: Sun Nov 15 2026

## Status
`ethscan/osdetect.py` partial-branch task completed this session.
- `ethscan/osdetect.py`: 293 stmts, 0 miss, 84 branch, **0 BrPart** (was 4 BrPart: `213->215`, `253->255`, `292->294`, `470->469`; plus missed stmts `428-430`). All reachable branches closed via `tests/test_osdetect_branch_gaps.py` (5 tests).
- `ethscan/ntp.py` re-measured this session (no change made): 314 stmts, 0 miss, 104 branch, **3 BrPart** (`61->74`, `245->243`, `393->400`), 99%. All 3 already documented unreachable in `tests/test_ntp_branch_gaps.py` docstring → ntp fully classified, done.
- Full suite: 32125 passed, 146 skipped, 1 preexisting warning. mypy clean (252 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- Targeted osdetect tests: `tests/test_osdetect.py tests/test_osdetect_hostile_sweep.py tests/test_osdetect_formatter_hostile_sweep.py tests/test_osdetect_branch_gaps.py` → **134 passed**; osdetect coverage 100% (0 BrPart).
- `python -m coverage run --branch -m pytest -q` → **32125 passed, 146 skipped**.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 252 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Added `tests/test_osdetect_branch_gaps.py` (5 tests, test-only/reversible). No production-code changes.
- Re-measured `ethscan/ntp.py`: confirmed 3 BrPart, all pre-documented unreachable in `tests/test_ntp_branch_gaps.py`; no change needed.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` and `ethscan/subdomains.py` `240->239` remain documented unreachable from prior sessions (not re-measured this session).
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) remain fully classified; no further snmp/nmap work.
- `ethscan/trace.py`, `ethscan/urlcheck.py`, `ethscan/subtake.py`, and `ethscan/osdetect.py` are now at 0 BrPart.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md history); no test possible.

## Next task
- Continue one module per session by partial-branch count; re-measure with targeted branch coverage before acting; classify reachable vs defensive/unreachable; do not batch modules.
- Precise next: **`ethscan/ntp.py`** (next in 3-BrPart list per handoff; `tests/test_ntp_branch_gaps.py` exists — re-check state). Reproduce command:
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.ntp -m pytest tests/test_ntp.py tests/test_ntp_hostile_sweep.py tests/test_ntp_branch_gaps.py -q && python -m coverage report --show-missing --include='ethscan/ntp.py'`
- After ntp is fully classified, proceed down remaining 3-BrPart candidates (`memcached`) re-measuring each before acting.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.

(End of file - total 39 lines)