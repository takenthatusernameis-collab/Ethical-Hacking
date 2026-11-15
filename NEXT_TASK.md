# Next Task
Date: Sun Nov 15 2026

## Status
`ethscan/wifi.py` partial-branch task completed this session.
- `ethscan/wifi.py`: 282 stmts, 0 miss, 128 branch, **0 BrPart** (was 3). All 3 branches classified reachable and closed via `tests/test_wifi_branch_gaps.py` (8 tests).
- Full suite: 32100 passed, 146 skipped. mypy clean (248 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- `ethscan/wifi.py` targeted tests: `tests/test_wifi.py tests/test_wifi_hostile_sweep.py tests/test_wifi_formatter_hostile_sweep.py tests/test_wifi_branch_gaps.py` → 393 passed.
- wifi branch coverage after new tests: 0 BrPart remaining (100% branch coverage).
- `python -m mypy ethscan/ tests/` → Success.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Added `tests/test_wifi_branch_gaps.py` (8 tests, test-only/reversible). No production-code changes.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` and `ethscan/subdomains.py` `240->239` remain documented unreachable from prior sessions (not re-measured this session).
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) are fully classified; no further snmp/nmap work.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md for evidence); no test possible.

## Next task
- One module per session by partial-branch count; re-measure with targeted coverage before acting; classify reachable vs unreachable; do not batch modules.
- Precise next: `ethscan/urlcheck.py` (3 BrPart; next highest not ruled out):
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.urlcheck -m pytest tests/test_urlcheck.py tests/test_urlcheck_hostile_sweep.py -q && python -m coverage report --show-missing --include='ethscan/urlcheck.py'`
- Then continue down the 3-BrPart list: trace, subtake, osdetect, ntp (already has test_ntp_branch_gaps.py — check its state first), memcached.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.

(End of file - total 37 lines)