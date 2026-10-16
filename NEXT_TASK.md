# Next Task for Agent

## Status
The `ethscan/urlcheck.py` coverage task is COMPLETE.

- `tests/test_urlcheck.py`: 17 → 21 tests (4 added, 1 existing test repaired), all pass.
- `ethscan/urlcheck.py` coverage: 95% → **100%** (196 stmts, 0 missing).
- No source files modified.
- Tests added (following existing conventions):
  - Repaired `test_run_urlcheck_with_weak_ssl`: it previously patched `ethscan.web.run_web_checks` / `ethscan.ssl.run_ssl` on the source modules, but `urlcheck.py` imports those names at module level, so the mocks were ineffective. Now patches `ethscan.urlcheck.run_web_checks` / `ethscan.urlcheck.run_ssl`, exercising the summary SSL-cert findings branch (lines 92-97).
  - `test_run_urlcheck_fuzz_findings_counted`: fuzz findings counted in `summary.total_findings` (line 88).
  - `test_format_urlcheck_report_markdown_info_disclosure_table`: info-disclosure table branch (lines 158-161).
  - `test_format_urlcheck_report_markdown_web_ssl_error`: web-check SSL error branch (line 170).
  - `test_format_urlcheck_report_csv_info_disclosure`: CSV information-disclosure row (line 270).
- Full suite: **3734 passed, 1 skipped** (baseline 3730); no regressions.
- `python -m ruff check tests/test_urlcheck.py`: 1 error, pre-existing (`pytest` F401 unused import present in the original file); zero new issues introduced.

## What was verified
1. `python -m pytest tests/test_urlcheck.py -q` — 21 passed.
2. `python -m pytest tests/test_urlcheck.py -q --cov=ethscan.urlcheck --cov-report=term-missing` — 100%, 0 missing.
3. `python -m pytest -q` — full suite 3734 passed, 1 skipped, no regressions.
4. `python -m ruff check tests/test_urlcheck.py` — no new linting issues.

## Current coverage state (from `python -m pytest -q --cov=ethscan --cov-report=term-missing`)

- `ethscan/urlcheck.py`: **100%**.
- `ethscan/smb.py`: 100%, `ethscan/wifi.py`: 100%, `ethscan/dnsbrute.py`: 100%.
- `ethscan/vuln.py`: 98%, `ethscan/ntp.py`: 99%, `ethscan/oracle.py`: 99%, `ethscan/mongodb.py`: 99%.
- Remaining 95% modules: `web.py` (10 missing: 171-172, 180-181, 204-205, 242, 305-307), `recon.py` (11 missing: 112-113, 125-126, 139-140, 154-155, 274, 276, 282).
- Plus `hash.py` 96%, `netbios.py` 97%, `snmp.py` 96%, `ldap.py` 96%, `ping.py` 96%, `mssql.py` 98%, `dnssec.py` 98%, `ftp.py` 98%, `s3.py` 97%, `postgresql.py` 99%, `smtp.py` 99%, `mysql.py` 99%, `service.py` 97%, `trace.py` 99%, `resolve.py` 97%, `radix.py` 97%, `passwords.py` 97%.
- `ethscan/fuzz.py`: 99% (1 missing: 79 — `fuzz_path` HTTPError branch).
- `ethscan/main.py`: 67% (line 7 — `if __name__ == "__main__"` block, only reachable when run as a script).
- Full suite: 98% total coverage, 3734 passed, 1 skipped.

## Next precise task

Improve coverage on one of the remaining 95% modules — e.g. `ethscan/web.py` (10 missing), `ethscan/recon.py` (11 missing), or the single line in `ethscan/fuzz.py` (79) — adding targeted unit tests to `tests/test_web.py` / `tests/test_recon.py` / `tests/test_fuzz.py` following existing test conventions, without modifying files under `ethscan/`. No prior handoff is pending. Verification baseline: full suite 3734 passed, 1 skipped; `urlcheck.py` at 100%.

(End of file - total 34 lines)