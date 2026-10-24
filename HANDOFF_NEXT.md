## What changed this session
Removed runpy RuntimeWarnings by popping cached module entries before runpy.run_module in tests/test_main.py.

## What was actually verified
- tests/test_main.py: 14 passed (warnings treated as errors).
- Full suite: 5207 passed, 48 skipped, 0 warnings.
- ruff: all checks passed.

## What remains unresolved
None.

## One precise next task
None.
