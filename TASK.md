## Status: COMPLETE

### What changed
- Added 10 tests to `tests/test_resolve.py` pinning previously uncovered branches of `ethscan.resolve`:
  - `test_resolve_ptr_records_gethostbyaddr_failure_without_dnspython` — `resolve_ptr_records` gethostbyaddr failure path with dnspython unavailable (lines 126-127).
  - `test_run_resolve_aaaa_records_failure_is_swallowed`, `test_run_resolve_cname_records_failure_is_swallowed`, `test_run_resolve_ptr_records_failure_is_swallowed` — per-record-type failure swallowing in `run_resolve` (lines 212-213, 217-218, 222-223).
  - `test_run_resolve_unknown_type_without_dnspython_is_ignored` — unknown record types ignored when dnspython unavailable (lines 234-235).
  - `test_resolve_dnspython_import_failure_degrades_gracefully` — module degrades to stdlib-only when `import dns` fails (lines 16-18); restores `sys.modules` and reloads the module in `finally`.
  - `test_format_resolve_report_markdown_record_types_queried_non_list`, `test_format_resolve_report_markdown_values_not_list`, `test_format_resolve_report_csv_values_not_list` — non-list branches of the report formatters (lines 267, 285, 309-310).
  - `test_run_resolve_unknown_type_dnspython_failure_is_swallowed` — dnspython failure for unknown types is swallowed.
- No source changes to `ethscan/resolve.py`.

### What was actually verified
- `python -m pytest tests/test_resolve.py -q` -> 69 passed (was 60).
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python -m mypy tests/test_stale.py ethscan/stale.py` -> Success: no issues found.
- `python -m coverage run -m pytest -q` (full suite) -> 5239 passed, 48 skipped (was 5229 passed).
- `ethscan/resolve.py` coverage: 91% -> 99% (201 stmts, 3 miss).

### What remains unresolved
- `ethscan/resolve.py` lines 225, 232-233 remain uncovered: line 225 is a defensively unreachable `continue` (every type in `all_supported` is handled above it); lines 232-233 are unreachable because `resolve_with_dnspython` swallows all exceptions before they propagate to `run_resolve`. Both are dead defensive code; no test can reach them without source changes.

### Which approaches failed and why
- None. Coverage measurement via an isolated `tests/test_resolve.py` run produced a stale/misleading report (reload artifacts); the full-suite run is the authoritative check.

### One precise next task
- COMPLETE: `ethscan/dns.py` is now 100% (144 stmts, 0 miss) after adding `test_run_dns_resolver_unexpected_exception_is_swallowed` to `tests/test_dns.py` covering the outer `except Exception` in `resolve_type` (lines 172-173) via a mocking resolver that raises `RuntimeError`.
- Next: raise `ethscan/radix.py` coverage from 94% (340 stmts, 19 miss: lines 181-182, 200-202, 206-209, 267-268, 296, 444, 448, 473, 488, 521, 558, 561, 575) by adding tests to `tests/test_radix.py`, keeping `ruff check ethscan/ tests/` and the full pytest suite green. Use `python -m coverage report --include="ethscan/radix.py" -m` to identify missing lines first.
