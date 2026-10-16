# Next Task for Agent

## Status
The `ethscan/ntp.py` coverage task is COMPLETE.

- `tests/test_ntp.py`: 41 → 47 tests (6 added), all pass.
- `ethscan/ntp.py` coverage: 95% → **99%** (248 stmts, 1 missing: line 387).
- Only 1 line remains missing, provably unreachable/dead code:
  - Line 387: `if mon_resp.get("error"):` re-check inside the `else` branch of line 367's `if mon_resp.get("error"):`, so it is always False; same class as intentionally-uncovered `redis.py:55-56` and `mongodb.py:205-206`; left uncovered, no source modification permitted.
- Tests added (following existing conventions, no files under `ethscan/` modified):
  - `_send_recv` real-socket path: success (`return data, None`, line 249) and `OSError` branch (lines 252-253), via `patch("ethscan.ntp.socket.socket")` with a fake socket.
  - `run_ntp` time-response parse error (lines 303-304): too-short time packet → `{"error": ...}` early return.
  - `format_ntp_report_markdown`: time-request error branch (lines 340-341), timestamp formatting with non-None ts (lines 357-359), monlist error branch (line 368).
- Full suite: **3730 passed, 1 skipped** (baseline 3724); no regressions.
- `python -m ruff check tests/test_ntp.py`: 4 errors, all pre-existing (I001 import sort, F401 unused `socket`/`DEFAULT_TIMEOUT`, SIM222); zero new issues introduced.

## What was verified
1. `python -m pytest tests/test_ntp.py -q` — 47 passed.
2. `python -m pytest tests/test_ntp.py -q --cov=ethscan.ntp --cov-report=term-missing` — 99%, missing only line 387.
3. `python -m pytest -q` — full suite 3730 passed, 1 skipped, no regressions.
4. `python -m ruff check tests/test_ntp.py` — no new linting issues.

## Current coverage state (from `python -m pytest -q --cov=ethscan --cov-report=term-missing`)

- `ethscan/ntp.py`: **99%** (1 missing: 387 — dead code, left uncovered).
- `ethscan/smb.py`: 100%, `ethscan/vuln.py`: 98%, `ethscan/oracle.py`: 99%, `ethscan/mongodb.py`: 99%, `ethscan/wifi.py`: 100%.
- Remaining 95% modules: `urlcheck.py` (10 missing: 88, 93, 95, 97, 158-161, 170, 270), `web.py` (10 missing: 171-172, 180-181, 204-205, 242, 305-307), `recon.py` (11 missing: 112-113, 125-126, 139-140, 154-155, 274, 276, 282).
- Plus `hash.py` 96%, `netbios.py` 97%, `snmp.py` 96%, `ldap.py` 96%, `ping.py` 96%, `mssql.py` 98%, `dnssec.py` 98%, `ftp.py` 98%, `s3.py` 97%, `postgresql.py` 99%, `smtp.py` 99%, `mysql.py` 99%, `service.py` 97%, `trace.py` 99%, `resolve.py` 97%, `radix.py` 97%, `passwords.py` 97%.
- `ethscan/main.py`: 67% (line 7 — `if __name__ == "__main__"` block, only reachable when run as a script).
- Full suite: 98% total coverage, 3730 passed, 1 skipped.

## Next precise task

Improve coverage on one of the 95% modules — e.g. `ethscan/urlcheck.py` (10 missing), `ethscan/web.py` (10 missing), or `ethscan/recon.py` (11 missing) — adding targeted unit tests to `tests/test_urlcheck.py` / `tests/test_web.py` / `tests/test_recon.py` following existing test conventions, without modifying files under `ethscan/`. Alternatively select a new command per the TASK.md conventions (`run_*`, `format_*_report_json/markdown`, CLI registration, unit + CLI integration tests, stdlib only). No prior handoff is pending. Verification baseline: full suite 3730 passed, 1 skipped; `ntp.py` at 99%.
