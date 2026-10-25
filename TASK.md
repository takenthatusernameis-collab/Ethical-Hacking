# TASK

## Status: COMPLETE

Repository complete and in sync with origin/main. Previous fix for `BLE001` in `ethscan/config.py:121` (commit `44202cf`) committed and pushed. All tests and lint pass.

This session: fixed `ethscan config --init PATH --out OUT` silently dropping `--out` (commit below). Added regression test `test_config_init_and_out_are_mutually_exclusive`. All tests and lint pass.

### What was actually verified

- `git push` succeeded (branch ahead pushed to origin)
- `python -m ruff check ethscan/ tests/` → All checks passed
- `python -m pytest tests/ -q` → 5205 passed, 51 skipped, 0 warnings