## Status: COMPLETE

### What changed
- Added `test_format_cve_report_csv_skips_non_dict_entries` and `test_format_cve_report_markdown_skips_non_dict_entries` to `tests/test_cve.py`, covering non-dict entry skip branches in `ethscan/cve.py` (lines 533, 630).

### What was actually verified
- `pytest tests/test_cve.py -q` -> 68 passed.
- `ruff check ethscan/ tests/` -> 9 pre-existing errors, no new.

### What remains unresolved
- `ethscan/cve.py` still has defensive branches uncovered (306-308, 325-329, 348-349, 354-355, 359-360, 366-367, 371-372, 377, 380, 383-384, 430-431, 70, 98). Some require source changes or mocking.

### One precise next task
- Pick next module below 100% coverage (e.g. `ethscan/dnssec.py` at 95%) and raise by adding tests, keeping ruff and full suite green.
