## Status: IN PROGRESS (this session)

### What changed
- Added targeted tests: `tests/test_hash_extra.py` (cover MD4 normalization/unavailable paths, PBKDF2+pepper unsupported algorithm) and `tests/test_ssh_extra.py` (cover generic exception and empty-payload read paths). Fixed minor lint issues.

### What was actually verified
- `python -m ruff check ethscan/ tests/` -> `All checks passed!`
- `python -m mypy ethscan/` and targeted mypy for new tests -> `Success: no issues found`
- New tests: `python -m pytest tests/test_hash_extra.py tests/test_ssh_extra.py -q` -> `5 passed`
- Coverage on modified targets improved (hash/ssh uncovered reduced in exercised paths)

### What remains unresolved
- Module-level MD4 init branches (hash.py:36-37) remain hard to exercise without reload tricks; other residual misses are defensive/unreachable as before.

### Which approaches failed and why
- None this session.

### One precise next task
- If desired, add a controlled reload test for MD4 init fallback with clean module isolation, or leave as-is (defensive). Otherwise proceed to address any newly reported defect.
