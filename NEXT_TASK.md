# Next Task

## Status
Sun Nov 15 2026: `mongodb` partial-branch task completed. Measured `ethscan/mongodb.py` at 5 partial branches initially (`59->70, 66->70, 95->97, 196->207, 212->207`) with branch coverage over `tests/test_mongodb.py`, `tests/test_mongodb_hostile_sweep.py`, `tests/test_mongodb_formatter_hostile_sweep.py`. Closed all 5 reachable arcs with focused tests in `tests/test_mongodb_branch_gaps.py`. `ethscan/mongodb.py` now 202 stmts, 0 miss, 74 branches, 0 BrPart — 100% branch-covered. Repo fully green.

## Baseline / verification this session
- `python -m pytest -q` → 32083 passed, 146 skipped, 0 failed (1 preexisting warning: `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 244 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.
- Targeted branch coverage (`python -m coverage run --branch -m pytest tests/test_mongodb.py tests/test_mongodb_hostile_sweep.py tests/test_mongodb_formatter_hostile_sweep.py tests/test_mongodb_branch_gaps.py -q` + `coverage report --include='ethscan/mongodb.py'`): 202 stmts, 0 miss, 74 branch, 0 BrPart.

## What changed
- Added `tests/test_mongodb_branch_gaps.py` (5 tests), test-only/reversible:
  - `59->70`: `_normalize_target("[::1")` (bracketed host with no closing bracket; host returned verbatim).
  - `66->70`: `_normalize_target("host:abc")` (unbracketed host with non-digit port suffix; host returned verbatim).
  - `95->97`: `_send_recv` with empty `request` skips `sendall`; asserts sendall is not called.
  - `196->207`: `_parse_buildinfo_response` with a version field whose 4-byte length prefix straddles the end of the document (`str_start + 4 > len(doc_data)`); version block skipped, jumps to generic field loop.
  - `212->207`: `_parse_buildinfo_response` with a generic field (sysInfo) whose length prefix straddles the end of the document; that field skipped, loop continues.
- No production-code changes.

## What remains unresolved
- None in `ethscan/mongodb.py` (100% branch-covered). All 5 arcs were input-reachable and are now covered.

## Approaches already tried / ruled out
- `smtp` (5 documented unreachable arcs) — do not re-attempt. `oracle`/`postgresql` empty-target handling remains out of scope per documented contract.
- `subdomains` retains 1 defensive BrPart (`240->239`, recursive dedupe false branch) — documented unreachable under current control flow; do not re-attempt.

## Next task
- Continue one module per session by partial-branch count (reproduce each with branch coverage first; classify reachable vs defensive/unreachable before editing tests; do not batch modules).
- Re-measure per-module counts before acting: `python -m coverage erase && python -m coverage run --branch -m pytest -q` then `python -m coverage report | awk '$0 ~ /^ethscan\// && $5+0>0 {print $5"\t"$1}' | sort -rn`.
- Current ordering (BrPart / 99% coverage): `smtp`=5 (unreachable, skip), `vuln`=4, `snmp`=4, `nmap`=4, `wifi`=3, `urlcheck`=3, `trace`=3, `subtake`=3, `postgresql`=3, `osdetect`=3, `ntp`=3, `memcached`=3, `whois`=2, `s3`=2, `redis`=2, `oracle`=2, `ftp`=2, `dnsbrute`=2, `netbios`=1, `hash`=1.
- Precise next task: reproduce `ethscan/vuln.py` partial branches with `python -m coverage run --branch -m pytest tests/test_vuln.py tests/test_vuln_hostile_sweep.py tests/test_vuln_formatter_hostile_sweep.py -q` then `python -m coverage report --show-missing --include='ethscan/vuln.py'`.
  - Pre-measured this session: 4 BrPart. Reproduce arc-level evidence before editing tests.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Preexisting warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- Caches (`.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`) are gitignored; commit only source/test/handoff files.

(End of file - total 41 lines)