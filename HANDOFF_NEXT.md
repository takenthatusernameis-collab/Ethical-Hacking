## Status: COMPLETE

### What changed
- Added 10 tests to `tests/test_resolve.py`, covering previously uncovered branches of `ethscan.resolve` (record-type failure swallowing in `run_resolve`, gethostbyaddr failure without dnspython, unknown-type handling with and without dnspython, dnspython import failure, non-list formatter branches). No source changes.

### What was actually verified
- `pytest tests/test_resolve.py` -> 69 passed.
- `ruff check ethscan/ tests/` -> All checks passed.
- Full suite `pytest -q` -> 5239 passed, 48 skipped.
- `ethscan/resolve.py` coverage: 91% -> 99%; remaining misses (lines 225, 232-233) are unreachable defensive code.

### What remains unresolved
- None blocking. `ethscan/dns.py` is the next-lowest coverage module at 92%.

### Which approaches failed and why
- None.

### One precise next task
- Add tests to `tests/test_dns.py` to raise `ethscan/dns.py` coverage from 92% (12 missing statements). Identify missing lines with `python -m coverage report --include="ethscan/dns.py" -m`, then keep `ruff check ethscan/ tests/` and the full suite green.

Verified: 2026-10-28 (ruff/mypy/pytest all passing; coverage 5239 passed, 48 skipped).
