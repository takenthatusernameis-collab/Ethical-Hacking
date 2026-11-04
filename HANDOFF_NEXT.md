# Handoff
Date: Wed Nov 04 2026
Session: Found and fixed five more instances of the same output-completeness defect class (CSV formatter dropping the `findings` section that markdown and JSON both render): `ftp`, `ntp`, `oracle`, `smtp`, `snmp`. Baseline green.

## What changed (this session)
- `ethscan/ftp.py`, `ethscan/ntp.py`, `ethscan/oracle.py`, `ethscan/smtp.py`, `ethscan/snmp.py` — each `format_*_report_csv()` rendered its main section but silently dropped the `findings` section, even though the corresponding `format_*_report_markdown()` rendered it. Added a `findings` CSV block mirroring the markdown section: a `finding` header row followed by one row per finding string (identical pattern to the earlier `web.py` and `headers.py` fixes).
- `tests/test_ftp.py`, `tests/test_ntp.py`, `tests/test_oracle.py`, `tests/test_smtp.py`, `tests/test_snmp.py` — added `test_format_*_report_csv_with_findings` and `test_format_*_report_csv_no_findings` for each module (10 new tests).

## What was actually verified (this session)
- Reproduced the defect class systematically: AST-audited all 38 formatter triplets for modules that populate a `findings` key. 19 modules populate `findings`; 17 render it in CSV; 5 were genuine omissions (`ftp`, `ntp`, `oracle`, `smtp`, `snmp`) — all string-list findings rendered by markdown but not CSV.
- `fuzz.py` and `ssh.py` were audited and confirmed **not** defects: `fuzz` preserves findings via an `is_finding` column (status_code != 404) on every result row; `ssh` emits one CSV row per finding dict.
- `python -m pytest tests/test_ftp.py tests/test_ntp.py tests/test_oracle.py tests/test_smtp.py tests/test_snmp.py -q` → 432 passed.
- `python -m pytest -q` → 5555 passed / 50 skipped (was 5545; +10 new tests, no regressions).
- `python -m ruff check ethscan tests` → "All checks passed!".
- `python -m mypy ethscan` → "Success: no issues found in 59 source files".
- Re-ran the AST audit after the fix: all 19 `findings`-populating modules now render `findings` in CSV.

## What remains unresolved
- Landing CI workflow `.github/workflows/test.yml` on `origin/main` is still blocked. Re-verified this session via an actual push attempt: deterministic 403 on the `workflows` permission scope. The file content is known (`git show 2e9a943:.github/workflows/test.yml`).
- No other bounded feature/bug task identified.

## Approaches already tried and why they failed
- Pushing `test.yml` (re-attempted this session) → 403. Deterministic; renaming or recreating does not help.
- Systematic cross-format consistency audit across all 38 formatter triplets → two modules (`fuzz.py`, `ssh.py`) flagged as having keys in markdown/JSON but not CSV, but on inspection both **preserve** the `findings` information in CSV — `fuzz.py` derives an `is_finding` column from `all_results` (status_code != 404), and `ssh.py` emits one CSV row per finding dict. Neither is a real omission defect.
- Assuming the repo was fully output-consistent across formats → false for `web.py` (prior session), `headers.py` (this session), and five more modules (`ftp`, `ntp`, `oracle`, `smtp`, `snmp`, this session). All seven were genuine defects; all fixed.
- Assuming the `findings`-section omission was isolated to `web.py` → false; `headers.py`, `ftp`, `ntp`, `oracle`, `smtp`, and `snmp` all shared the exact same pattern (a `findings` key populated by an `_assess_*_version` helper and rendered by markdown but not CSV).
- Trusting a manual grep-based audit → unreliable; the CSV functions end with `return` rather than another `def`, so range-based grep missed the `web.py` findings block that was already fixed. An AST-based audit was required and is the reliable method.

## Precise next task
1. If/when a `workflows`-scoped token becomes available: restore `.github/workflows/test.yml` from `2e9a943` (or recreate identically), commit, `git push origin main`, then re-verify `ruff`, `mypy`, and `pytest`.
2. Otherwise: repo is green and feature-complete. Do not create speculative work.

(End of file - total 41 lines)