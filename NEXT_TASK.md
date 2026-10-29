## Status: COMPLETE

### What changed
- Added `test_merge_networks_mixed_families_kept_separate` to `tests/test_radix.py`, covering the version-mismatch branch of `ethscan/radix.py` `_merge_networks` (lines 193-195).
- No source changes to `ethscan/radix.py`.

### What was actually verified
- `pytest tests/test_radix.py -q` -> 125 passed.
- `ethscan/radix.py` coverage: 94% -> 95% (367 stmts, 20 miss).
- `ruff check ethscan/ tests/` -> no new errors (9 pre-existing on clean HEAD).
- Full suite `pytest -q` -> 5297 passed, 51 skipped.

### What remains unresolved
- `ethscan/radix.py` lines 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324 are dead defensive code, unreachable without source changes.

### One precise next task
- Raise another sub-100% module by adding tests, keeping ruff and full suite green. Most bounded candidate: `ethscan/tls.py` at 95% (210 stmts, 10 miss: lines 419, 429, 439, 445, 461, 467, 499, 502, 515, 518). Confirm missing lines with `python -m coverage report --include="ethscan/tls.py" -m` first.
