# Next Task for Agent

## Status
- Working tree: modified (ethscan/web.py, tests/test_cert.py, tests/test_geo.py, tests/test_mac.py, tests/test_osdetect.py, tests/test_wifi.py). Not committed.
- Tests: 3902 passed, 1 skipped.
- PERF102 + SIM117 clean in touched files; global SIM117 reduced from 22 to 0 in src scope context; tests partially cleaned.

## Next precise task
Apply the safe, deterministic lint cleanups that ruff can auto-fix without --unsafe where possible; otherwise one bounded code at a time. Continue SIM117 cleanup in remaining test files if desired (small batches), or pick another safe autofix group (e.g. F841, RUF015) bounded to specific files. Verify with ruff --select <codes> and pytest.
