# Next Task for Agent

## Status
`ethscan/cidr.py` coverage task COMPLETE (now 100%: 148 stmts, 0 missing). Full suite: 3771 passed, 1 skipped. Only `tests/test_cidr.py` was modified (added targeted unit tests); no files under `ethscan/` were modified.

## Current coverage state
Remaining non-100 modules include many 96-99%. Lowest: `ethscan/cli.py` 96% (57 missing), `ethscan/ping.py`/`ethscan/snmp.py` 96%.

## Next precise task
Improve coverage on `ethscan/cli.py` (96% coverage, 57 missing lines) — add targeted unit tests to `tests/test_cli.py` following existing conventions, without modifying files under `ethscan/`. Verification baseline: full suite 3771 passed, 1 skipped; `cidr.py` and `recon.py` at 100%.
