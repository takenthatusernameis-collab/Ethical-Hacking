## Status: IN_PROGRESS

### One precise next task
- Raise `ethscan/dns.py` coverage from 92% (147 stmts, 12 miss) by adding tests to `tests/test_dns.py`.
- First step: run `python -m coverage report --include="ethscan/dns.py" -m` to list missing lines.
- Constraints: keep `ruff check ethscan/ tests/` passing and the full `pytest -q` suite green; prefer smallest reversible changes, no source changes unless a branch is demonstrably dead.
