## Status: COMPLETE

### What changed
- Added 1 test to `tests/test_cve.py` covering `ethscan/cve.py` line 70: `_load_cache` returns `{}` when the cache file holds valid JSON that is not a mapping.

### What was actually verified
- `pytest tests/test_cve.py -q` -> 82 passed.
- `ethscan/cve.py` coverage: 98% -> 99% (432 stmts, 2 miss: lines 348-349, dead code).
- `ruff check ethscan/ tests/` -> 10 pre-existing errors, no new errors.
- Full suite `python -m pytest -q` -> 5355 passed, 51 skipped; 1 pre-existing failure (`test_dnssec_inner_dns_import_failure`, environment-related).

### What remains unresolved
- `ethscan/cve.py` lines 348-349 are unreachable dead code (not coverable by tests without source changes).
- Pre-existing `test_dnssec_inner_dns_import_failure` failure.

### One precise next task
- No test-only coverage gains remain (`cve.py` 99% with only dead lines 348-349 missing; `radix.py` deferred without source changes). Next: `ethscan/radix.py` only if source changes are authorized to make its defensive branches reachable.
