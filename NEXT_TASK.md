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

## Next precise task
No remaining work on the vuln coverage assignment. Remaining coverage gaps across other `ethscan/` modules (from `python -m pytest -q --cov=ethscan --cov-report=term-missing`):

- `ethscan/oracle.py`: 92% (18 missing: 218-220, 239-241, 272-274, 292-294, 304-305, 315-316, 412-413) — lowest percentage.
- `ethscan/vuln.py`: 98% (9 missing, all unreachable as noted above).
- `ethscan/netbios.py`: 95% (16 missing).
- `ethscan/ntp.py`: 95% (12 missing).
- `ethscan/recon.py`: 95% (11 missing).
- `ethscan/urlcheck.py`: 95% (10 missing).
- `ethscan/web.py`: 95% (10 missing).
- `ethscan/wifi.py`: 95% (11 missing).
- `ethscan/smb.py`: 96% (19 missing).
- `ethscan/snmp.py`: 96% (15 missing).
- `ethscan/ping.py`: 96% (9 missing).
- `ethscan/radix.py`: 97% (9 missing).
- `ethscan/passwords.py`: 97% (4 missing).
- `ethscan/resolve.py`: 97% (4 missing).
- `ethscan/s3.py`: 97% (6 missing).
- `ethscan/service.py`: 97% (3 missing).
- `ethscan/mssql.py`: 98% (8 missing).
- `ethscan/mysql.py`: 99% (3 missing).
- `ethscan/postgresql.py`: 99% (1 missing).
- `ethscan/trace.py`: 99% (1 missing).
- `ethscan/redis.py`: 99% (2 missing, intentionally uncovered).
- `ethscan/mongodb.py`: 99% (2 missing, intentionally uncovered).

Pick one bounded, high-value task: improve coverage on `ethscan/oracle.py` (lowest % at 92%) or `ethscan/smb.py` (largest absolute gap at 19 lines), following existing test conventions. Or select a new command per TASK.md conventions. No prior handoff is pending.
