# Next Task for Agent

## Status
`ethscan/recon.py` coverage task COMPLETE (already 100%: 208 stmts, 0 missing). Full suite: 3746 passed, 1 skipped. No source files modified this session (recon was already at 100% on entry).

## Current coverage state
Remaining non-100 modules include many 96-99%. Lowest: `ethscan/cidr.py` 93% (10 missing: 68-69, 116, 122-123, 126-127, 248-250). Also `ethscan/cli.py` 96% (57 missing), `ethscan/ping.py`/`ethscan/snmp.py` 96%.

## Next precise task
Improve coverage on `ethscan/cidr.py` (10 missing lines: 68-69, 116, 122-123, 126-127, 248-250) — add targeted unit tests to `tests/test_cidr.py` following existing conventions, without modifying files under `ethscan/`. Verification baseline: full suite 3746 passed, 1 skipped; `recon.py` at 100%.
