## Status: COMPLETE

### What changed
- Added `test_merge_networks_mixed_families_kept_separate` to `tests/test_radix.py`, covering the version-mismatch branch of `ethscan/radix.py` `_merge_networks` (lines 193-195).
- No source changes.

### What was actually verified
- `python -m pytest tests/test_radix.py -q` -> 125 passed.
- `ruff check ethscan/ tests/` -> no new errors (9 pre-existing on clean HEAD).
- Full suite `python -m pytest -q` -> 5297 passed, 51 skipped.
- `ethscan/radix.py` coverage: 94% -> 95% (367 stmts, 20 miss: 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324).

### What remains unresolved
- `ethscan/radix.py` lines 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324 are unreachable defensive code (sort fallbacks, blind-except handlers, mixed-version branches, `ip_network` ValueError fallback, non-list children). Reaching them would require source changes or mocking non-`ipaddress` objects.

### One precise next task
- Pick next module below 100% coverage and raise it by adding tests, keeping ruff and full suite green. Most bounded candidate: `ethscan/tls.py` at 95% (210 stmts, 10 miss: lines 419, 429, 439, 445, 461, 467, 499, 502, 515, 518). Confirm missing lines with `python -m coverage report --include="ethscan/tls.py" -m` first.
