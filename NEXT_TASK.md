# Next Task

## Status: no pending task; repo fully green with fresh evidence.

This session completed the session 2 handoff: added the end-to-end CLI regression test that `ethscan scan --target ::1 --protocol udp` reports a live IPv6 UDP service as open. Working tree has the completed, uncommitted test addition at HEAD `38dd480`.

## Verification (fresh evidence, this session)
- `python -m pytest -q` -> **46771 passed, 147 skipped, 0 failed** (baseline 46770; +1 new test).
- `python -m mypy ethscan/ tests/` -> Success, no issues in 268 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- `git diff --check` -> clean; `git status` -> only `tests/test_cli.py` modified (67 insertions).
- Regression proof: temporarily reverting `scan_udp_port` to the pre-fix `AF_INET` form made the new test fail (`assert <port> in []`); restoring the fix made it pass.

## Next task
- None pending. Repository is fully green. The UDP-IPv6 silent-wrong-result fix is now locked at both the scanner level (`tests/test_scanner.py::test_scan_udp_port_ipv6_loopback_open_is_detected`) and the CLI level (`tests/test_cli.py::test_scan_udp_ipv6_loopback_open_is_detected`).

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it (removing would weaken validation; `# pragma: no cover` would game the metric).
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- The remaining `AF_INET` occurrences in `resolve.py`/`dns.py`/`stale.py`/`subtake.py` are `getaddrinfo` name-resolution hints (intentionally IPv4), not sockets; not a bug.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once; if green, proceed.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work. Do not repeat verification-only sessions.