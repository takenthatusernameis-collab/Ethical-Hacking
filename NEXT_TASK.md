# Next Task
Date: Sun Nov 15 2026

## Status
`ethscan/snmp.py` and `ethscan/nmap.py` partial-branch tasks completed this session.
- `ethscan/snmp.py`: 388 stmts, 0 miss, 162 branch, 2 BrPart (`133->146, 577->576`), both **proven unreachable** (control-flow invariants; no test possible).
- `ethscan/nmap.py`: 297 stmts, 0 miss, 98 branch, **1 BrPart** (`315->313`), **proven unreachable**. Closed 3 reachable arcs (`138->157, 186->184, 194->200`) via `tests/test_nmap_branch_gaps.py` (4 tests).
- Full suite: 32093 passed, 146 skipped. mypy clean (247 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- `ethscan/nmap.py` targeted tests: `tests/test_nmap.py tests/test_nmap_hostile_sweep.py tests/test_nmap_formatter_hostile_sweep.py tests/test_nmap_branch_gaps.py` → 142 passed.
- nmap branch coverage after new tests: 1 BrPart remaining (`315->313`, classified unreachable).
- `python -m mypy ethscan/ tests/` → Success.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Added `tests/test_nmap_branch_gaps.py` (4 tests, test-only/reversible). No production-code changes.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` and `ethscan/subdomains.py` `240->239` remain documented unreachable from prior sessions (not re-measured this session).

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md for evidence); no test possible.

## Next task
- One module per session by partial-branch count; re-measure with targeted coverage before acting; classify reachable vs unreachable; do not batch modules.
- Precise next: `ethscan/wifi.py` (3 BrPart; next highest not ruled out):
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.wifi -m pytest tests/test_wifi.py tests/test_wifi_hostile_sweep.py tests/test_wifi_formatter_hostile_sweep.py -q && python -m coverage report --show-missing --include='ethscan/wifi.py'`
- Then continue down the 3-BrPart list: urlcheck, trace, subtake, osdetect, ntp (already has test_ntp_branch_gaps.py — check its state first), memcached.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.
