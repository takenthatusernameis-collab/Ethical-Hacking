## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/brute.py` (3 errors -> 0): hardened formatting functions to safely handle dynamic dict values.
- Fixed mypy typing errors in `ethscan/hash.py` (2 errors -> 0): hardened markdown/CSV formatting to safely iterate over results.
- Fixed NetBIOS behavior in `ethscan/netbios.py`: when `_send_recv` returns `(None, None)`, `run_netbios` now reports `response parse failed: empty response` (matches expected behavior for empty transport responses).

### What was actually verified
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest tests/test_brute.py tests/test_hash.py tests/test_netbios.py -q` -> all passing.
- Full test suite: `python -m pytest -q` -> 5225 passed, 51 skipped.

### What remains unresolved
- None.

### One precise next task
None - all mypy errors in `ethscan/` are resolved and full test suite passes.
