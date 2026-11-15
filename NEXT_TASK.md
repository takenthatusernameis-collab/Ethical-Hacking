# Next Task

## Status
Sun Nov 15 2026: ntp partial-branch task completed. Measured `ethscan/ntp.py` at 7 partial/missing items initially (`61->74,245->243,393->400,424,436,473->499,540`) with branch coverage over `tests/test_ntp.py`, `tests/test_ntp_hostile_sweep.py`, `tests/test_ntp_formatter_hostile_sweep.py`; closed all reachable arcs/statements with focused tests in `tests/test_ntp_branch_gaps.py`. `ethscan/ntp.py` now 314 stmts, 0 miss, 104 branches, 3 defensive BrPart remaining (`61->74,245->243,393->400`) — 99% branch-covered. Repo fully green.

## Baseline / verification this session
- `python -m pytest -q` → 32063 passed, 146 skipped, 0 failed (1 preexisting warning: `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 240 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.
- Targeted branch coverage (`python -m coverage run --branch -m pytest tests/test_ntp.py tests/test_ntp_hostile_sweep.py tests/test_ntp_formatter_hostile_sweep.py tests/test_ntp_branch_gaps.py -q` + `coverage report --include='ethscan/ntp.py'`): 314 stmts, 0 miss, 104 branch, 3 BrPart (`61->74,245->243,393->400`).

## What changed
- Added `tests/test_ntp_branch_gaps.py` (6 tests), test-only/reversible:
  - `63->74`: bracketed host with non-digit port suffix in `_normalize_target`
  - `68->74`: unbracketed host with non-digit port suffix in `_normalize_target`
  - `424`: `_normalize_peers` non-list/tuple input
  - `436`: `format_ntp_report_markdown` non-dict input
  - `473->499`: markdown monlist-error path without `extra`/`more` note
  - `540`: `format_ntp_report_csv` non-dict input
- No production-code changes.

## What remains unresolved
- `ethscan/ntp.py` has 3 defensive/unreachable partial branches (coverage cannot mark them taken):
  - `61->74`: inside `startswith("[") and "]:" in host`, `find("]:")` cannot be `<= 0` (absent is excluded by guard; index 0 impossible when string starts with `[`)
  - `245->243`: peer data sliced to exactly `count*8` after length guard and iterated in 8-byte steps, so chunk length is always 8
  - `393->400`: `_build_monlist_request()` is a constant 12-byte packet, so `req_len > 0` always

## Approaches already tried / ruled out
- Forcing `61->74`: not reachable because guard conditions are logically contradictory for `bracket_end <= 0`.
- Forcing `245->243`/`393->400`: not reachable given current slicing/constant request construction; changing production code solely to make defensive arcs testable is not justified.
- `smtp` (5 arcs) remains documented unreachable — do not re-attempt. `oracle`/`postgresql` empty-target handling remains out of scope per contract.

## Next task
- Continue one module per session by partial-branch count (reproduce each with branch coverage first; classify reachable vs defensive/unreachable before editing tests; do not batch modules).
- Per prior full-suite measurement, next candidates after ntp: `netbios` (5), `subdomains` (5), then `ldap`/`mongodb`/`nmap`/`snmp`/`vuln` (4 each). Re-measure candidate module branch coverage in-session before acting.
- Precise next task: reproduce `ethscan/netbios.py` partial branches with `python -m coverage run --branch -m pytest tests/test_netbios.py tests/test_netbios_hostile_sweep.py -q` (include formatter/related netbios tests if present) and `coverage report --show-missing --include='ethscan/netbios.py'`, then add focused tests for reachable arcs or document unreachable ones with arc-level evidence.
