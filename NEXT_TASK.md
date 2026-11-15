# Next Task
Date: Sun Nov 15 2026

## Status
`ethscan/vuln.py` partial-branch task completed. Measured `ethscan/vuln.py` at 4 partial branches initially (`950->955, 977->984, 1031->1029, 1036->1029`) with branch coverage over `tests/test_vuln.py`, `tests/test_vuln_hostile_sweep.py`, `tests/test_vuln_formatter_hostile_sweep.py`. Closed 3 reachable arcs with focused tests in `tests/test_vuln_branch_gaps.py`. `ethscan/vuln.py` now 476 stmts, 0 miss, 244 branch, 1 BrPart (99%).

## Baseline / verification this session
- `python -m pytest -q` → 32086 passed, 146 skipped, 0 failed (1 preexisting warning: `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 245 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.
- Targeted branch coverage (`python -m coverage run --branch -m pytest tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_formatter_hostile_sweep.py tests/test_vuln_branch_gaps.py -q` + `coverage report --include='ethscan/vuln.py'`): 476 stmts, 0 miss, 244 branch, 1 BrPart.

## What changed
- Added `tests/test_vuln_branch_gaps.py` (3 tests, test-only/reversible):
  - `950->955`: `test_scan_host_skips_non_string_banner` — banner entries whose value is `int`/`None`/`bytes` are skipped at the `continue` (line 948) before `parse_banner` is reached; only the `str` banner (OpenSSH 7.2p2) is matched, so all findings carry `port == 22`.
  - `977->984`: `test_min_severity_unknown_filter_drops_all` — `min_severity="bogus"` yields `min_rank None`, so the filter block is skipped and findings are untouched.
  - `1031->1029`: `test_recursive_scan_skips_already_scanned_host` — a banner advertising the initial host itself is skipped because it is already in `scanned_hosts`.
- No production-code changes.

## What remains unresolved
- `ethscan/vuln.py` `1036->1029` (the `if recursive_result:` false branch) is **unreachable** under the current control flow and is left uncovered. The guard at line 1024 (`if depth < max_depth:`) gates host discovery, so a recursive call can only be made when `depth < max_depth`. That call returns `{}` only when `depth+1 > max_depth`, i.e. `depth >= max_depth` — a contradiction. No input forces the false branch; it is a defensive check, not a reachable arc.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling remains out of scope per documented contract.
- `subdomains` retains 1 defensive BrPart (`240->239`) — documented unreachable under current control flow; do not re-attempt.
- `vuln` `1036->1029`: attempted to force via a discovered host whose banner advertises a further host at `max_depth`; the sub-scan returned a non-empty dict (it still scanned the host at depth 1 before hitting the depth guard), so the true branch was taken. Confirmed unreachable by control-flow analysis.

## Next task
- Continue one module per session by partial-branch count (reproduce each with branch coverage first; classify reachable vs defensive/unreachable before editing tests; do not batch modules).
- Re-measure per-module counts before acting: `python -m coverage erase && python -m coverage run --branch -m pytest -q` then `python -m coverage report | awk '$0 ~ /^ethscan\// && $5+0>0 {print $5"\t"$1}' | sort -rn`.
- Current ordering (BrPart / 99% coverage): `vuln`=1 (unreachable), `snmp`=4, `nmap`=4, `wifi`=3, `urlcheck`=3, `trace`=3, `subtake`=3, `postgresql`=3, `osdetect`=3, `ntp`=3, `memcached`=3, `whois`=2, `s3`=2, `redis`=2, `oracle`=2, `ftp`=2, `dnsbrute`=2, `netbios`=1, `hash`=1.
- Precise next task: reproduce `ethscan/snmp.py` partial branches with `python -m coverage run --branch -m pytest tests/test_snmp.py tests/test_snmp_hostile_sweep.py tests/test_snmp_formatter_hostile_sweep.py -q` then `python -m coverage report --show-missing --include='ethscan/snmp.py'`.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches (`.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`) are gitignored; commit only source/test/handoff files.

(End of file - total 67 lines)