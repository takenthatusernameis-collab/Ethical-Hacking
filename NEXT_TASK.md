# Next Task

## Status: no pending task; repo fully green with fresh evidence.

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 268 source files.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- `python -m pytest -q` -> **46771 passed, 147 skipped, 0 failed**.
- Regression already locked: `ethscan/scanner.py` `scan_udp_port` is family-aware (`getaddrinfo` + `socket.socket(family, ...)`); `tests/test_scanner.py::test_scan_udp_port_ipv6_loopback_open_is_detected` and `tests/test_cli.py::test_scan_udp_ipv6_loopback_open_is_detected` both present and passing.

## Next task
- None pending. Repository is fully green.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- The remaining `AF_INET` occurrences in `resolve.py`/`dns.py`/`stale.py`/`subtake.py` are `getaddrinfo` name-resolution hints (intentionally IPv4), not sockets; not a bug.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once; if green, proceed.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work. Do not repeat verification-only sessions.
