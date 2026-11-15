# Next Task
Date: Sun Nov 15 2026

## Status
`ethscan/trace.py` partial-branch task completed this session.
- `ethscan/trace.py`: 257 stmts, 0 miss, 108 branch, **0 BrPart** (was 6 BrPart: `42, 45-49, 170->172, 270->263, 310->313, 364->367`). All reachable branches closed via `tests/test_trace_branch_gaps.py` (4 tests).
- Full suite: 32115 passed, 146 skipped, 1 preexisting warning. mypy clean (250 files), ruff clean, check_readme 0 drift.

## Baseline / verification this session
- Targeted trace tests: `tests/test_trace.py tests/test_trace_hostile_sweep.py tests/test_trace_formatter_hostile_sweep.py tests/test_trace_cli.py tests/test_trace_branch_gaps.py` → **600 passed**; trace coverage 100% (0 BrPart).
- `python -m coverage run --branch -m pytest -q` → **32115 passed, 146 skipped**.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 250 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed
- Added `tests/test_trace_branch_gaps.py` (4 tests, test-only/reversible). No production-code changes.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` and `ethscan/subdomains.py` `240->239` remain documented unreachable from prior sessions (not re-measured this session).
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) remain fully classified; no further snmp/nmap work.
- `ethscan/trace.py` and `ethscan/urlcheck.py` are now at 0 BrPart.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`, `nmap` `315->313`: unreachable by static invariant (see HANDOFF_NEXT.md history); no test possible.

## Next task
- Continue one module per session by partial-branch count; re-measure with targeted branch coverage before acting; classify reachable vs defensive/unreachable; do not batch modules.
- Precise next: **`ethscan/subtake.py`** (next in 3-BrPart list per handoff). Reproduce command:
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.subtake -m pytest tests/test_subtake.py tests/test_subtake_hostile_sweep.py -q && python -m coverage report --show-missing --include='ethscan/subtake.py'`
- After subtake is fully classified, proceed down remaining 3-BrPart candidates (`osdetect`, `ntp` — note `tests/test_ntp_branch_gaps.py` exists, re-check state, `memcached`) re-measuring each before acting.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches are gitignored; commit only source/test/handoff files.

(End of file)
