# Handoff
Date: Mon Nov 16 2026

## This session
- Prior assignment (HANDOFF_NEXT.md / NEXT_TASK.md): `ethscan/vuln.py` (1 BrPart candidate `1036->1029`).
- `ethscan/vuln.py` re-measured with the full targeted test set (branch_gaps + hostile_sweep + formatter_hostile_sweep): **1 BrPart** (`1036->1029`, documented unreachable). 5 reachable BrPart closed via existing tests:
  - `950->955` — `test_scan_host_skips_non_string_banner`
  - `977->984` — `test_min_severity_unknown_filter_drops_all`
  - `1031->1029` — `test_recursive_scan_skips_already_scanned_host`
  - `1147->1149` — `test_vuln_formatters_tolerate_hostile_findings` (port None in service finding)
  - `1259->1270` — `test_vuln_formatters_render_recursive_well_formed` (empty recursive_hosts_scanned)
- `1036->1029` classified **unreachable** by depth invariant: the recursive call at line 1035 is `_recursive_scan(host, depth + 1)`, only reached when `depth < max_depth` (line 1024), so `depth + 1 <= max_depth`. The callee returns `{}` only when `depth > max_depth` (line 1009) — contradiction. No test can cover it; documented in `tests/test_vuln_branch_gaps.py`.
- Moved to the next candidate: `ethscan/subdomains.py` (1 BrPart `240->239`).
- `ethscan/subdomains.py` re-measured: **1 BrPart** (`240->239`), classified **reachable** and closed with `test_run_subdomains_recursive_duplicate_hostname_skipped` in `tests/test_subdomains_branch_gaps.py`. Two depth-0 labels resolve to the same hostname, so the derived `base_domains` list carries a duplicate; on the second depth-1 iteration the emitted hostnames are already in `seen_hostnames`, so the guard at line 240 is False and the branch 240->239 is taken. Subdomains now at **100% branch coverage (0 BrPart)**.

## What changed
- Updated `tests/test_vuln_branch_gaps.py` (test-only/reversible):
  - Rewrote module docstring to reflect final state (5 reachable closed, 1 unreachable documented).
  - No test logic changed.
- Updated `tests/test_subdomains_branch_gaps.py` (test-only/reversible):
  - Added `test_run_subdomains_recursive_duplicate_hostname_skipped` covering `240->239`.
  - No production-code changes.

## What was actually verified
- Targeted vuln: `python -m coverage run --branch --source=ethscan.vuln -m pytest tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_branch_gaps.py tests/test_vuln_formatter_hostile_sweep.py -q && python -m coverage report --show-missing --include='ethscan/vuln.py'` → **247 passed**, 1 BrPart (documented unreachable).
- Targeted subdomains: `python -m coverage run --branch --source=ethscan.subdomains -m pytest tests/test_subdomains.py tests/test_subdomains_hostile_sweep.py tests/test_subdomains_branch_gaps.py -q && python -m coverage report --show-missing --include='ethscan/subdomains.py'` → **57 passed**, 0 BrPart, 100%.
- Full suite: `python -m coverage run --branch -m pytest -q` → **32129 passed, 146 skipped**, 1 warning (baseline 32128).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 253 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What remains unresolved
- `ethscan/snmp.py` (2 BrPart, both unreachable) and `ethscan/nmap.py` (1 BrPart, unreachable) remain fully classified; no further snmp/nmap work.
- `ethscan/trace.py`, `ethscan/urlcheck.py`, `ethscan/subtake.py`, `ethscan/osdetect.py`, `ethscan/memcached.py` (2 documented unreachable), `ethscan/vuln.py` (1 documented unreachable), and `ethscan/subdomains.py` (0 BrPart) are now at 0 reachable BrPart.
- `ethscan/smtp.py` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.

## Approaches already tried and ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling out of scope per contract.
- `snmp` `133->146` / `577->576`: unreachable by string/loop invariant. `nmap` `315->313`: unreachable by severity-domain invariant.
- `memcached` `144->133` / `151->133`: unreachable by `strip()` invariant.
- `vuln` `1036->1029`: unreachable by depth invariant (this session).
- `subdomains` `240->239`: reachable; closed this session.

## Precise next task
- Re-measure `ethscan/snmp.py` and `ethscan/nmap.py` to confirm 0 reachable BrPart (both already documented unreachable):
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.snmp -m pytest tests/test_snmp.py tests/test_snmp_hostile_sweep.py tests/test_snmp_branch_gaps.py -q && python -m coverage report --show-missing --include='ethscan/snmp.py'`
  `python -m coverage erase && python -m coverage run --branch --source=ethscan.nmap -m pytest tests/test_nmap.py tests/test_nmap_hostile_sweep.py tests/test_nmap_branch_gaps.py -q && python -m coverage report --show-missing --include='ethscan/nmap.py'`
- If both confirm 0 reachable BrPart, the branch-coverage campaign is complete and the repository is fully green.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches (`.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`) gitignored; commit only source/test/handoff files.

(End of file - total 55 lines)