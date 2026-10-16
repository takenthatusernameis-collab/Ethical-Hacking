# Next Task for Agent

## Status
The `ethscan/vuln.py` coverage task is COMPLETE.

- `tests/test_vuln.py`: 81 → 98 tests (13 added), all pass.
- `ethscan/vuln.py` coverage: 93% → **98%** (369 stmts, 9 missing).
- Only 9 lines remain missing, all provably unreachable/dead code:
  - Lines 37, 57-62: First definitions of `_hashlib_name`/`_compute_peppered_hash` overridden by later duplicates; never called.
  - Lines 555-556: IPv4 addresses always captured by hostname regex first in `_extract_hosts_from_banner`; IPv4-specific `seen.add`/`hosts.append` unreachable.
  - Line 904: `if depth > max_depth: return {}` in `_recursive_scan` unreachable (recursion gated by `depth < max_depth`).
  - Line 1047: Final `return ""` fallback in `_finding_detail` unreachable (all four finding kinds handled earlier).
- Same class as intentionally-uncovered `redis.py:55-56` and `mongodb.py:205-206`; no source modification permitted, so left uncovered.
- Full suite: **3679 passed, 1 skipped** (baseline: 3666). `ruff check tests/test_vuln.py`: 4 errors, all pre-existing; zero new issues introduced.
- No files under `ethscan/` were modified.

## What was verified
1. `python -m pytest tests/test_vuln.py -q` — 98 passed (was 81).
2. `python -m pytest -q --cov=ethscan.vuln --cov-report=term-missing` — 98%, missing only 37, 57-62, 555-556, 904, 1047.
3. `python -m pytest -q` — full suite 3679 passed, 1 skipped, no regressions.
4. `python -m ruff check tests/test_vuln.py` — no new linting issues.

## What was verified (this session)

- `ethscan/smb.py` coverage improved from 96% (19 missing lines: 215-230, 367, 375, 646, 857) to **100%** (0 missing) by adding 8 targeted unit tests to `tests/test_smb.py`:
  - `_send_recv` real-socket path: success, `socket.timeout`, `OSError`/connection-refused, and `close()`-error-swallowed branches (patched `ethscan.smb.socket.socket` with a fake, following `tests/test_mongodb.py` convention).
  - `_build_banner`: non-SMB1 early return and `signing="enabled"` branch.
  - `_build_smb2_banner`: `signing="disabled"` branch.
  - `format_smb_report_markdown`: SMB2 negotiate context entry with `detail=None`.
- `tests/test_smb.py`: 103 passed (was 95).
- `python -m pytest -q` full suite: **3717 passed, 1 skipped** (was 3709 + 8 new); no regressions.
- `python -m ruff check tests/test_smb.py`: 1 error, pre-existing import-sorting (I001); zero new issues.

## Current coverage state (from `python -m pytest -q --cov=ethscan --cov-report=term-missing`)

- `ethscan/smb.py`: **100%** (was 96%, 19 missing lines closed this session).
- `ethscan/oracle.py`: **99%** (2 missing: 304-305 — `except Exception` after `decode(..., errors="replace")`, provably unreachable; same class as intentionally-uncovered `redis.py:55-56` and `mongodb.py:205-206`; left uncovered).
- `ethscan/vuln.py`: 98% (9 missing, all unreachable/dead code).
- Remaining 95% modules: `ntp.py` (12 missing), `recon.py` (11), `wifi.py` (11), `urlcheck.py` (10), `web.py` (10); plus `netbios.py` 97%, `snmp.py` 96%, `ldap.py` 96%, `ping.py` 96%, `hash.py` 96%, `mssql.py` 98%, `dnssec.py` 98%, `ftp.py` 98%.
- Full suite: 98% total coverage, 3717 passed, 1 skipped.

## Next precise task

Improve coverage on one of the 95% modules — e.g. `ethscan/wifi.py` (11 missing lines: 35, 54-55, 113, 176, 180, 197, 378-381) or `ethscan/ntp.py` (12 missing: 249, 252-253, 303-304, 340-341, 357-359, 368, 387) — adding targeted unit tests following existing test conventions (`tests/test_wifi.py` / `tests/test_ntp.py`), without modifying files under `ethscan/`. Alternatively select a new command per the TASK.md conventions (`run_*`, `format_*_report_json/markdown`, CLI registration, unit + CLI integration tests, stdlib only). No prior handoff is pending. Verification baseline: full suite 3717 passed, 1 skipped; `smb.py` at 100%.
