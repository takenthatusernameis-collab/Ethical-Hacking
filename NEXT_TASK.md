# Next Task
Date: Thu Nov 19 2026 (session 21)

## Status
- Green: **46672 passed, 146 skipped, 0 failed**; mypy Success (264 source files); `ruff check ethscan tests` clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean.
- Formatter fuzzer (prior session): 160 `format_*_report_{json,markdown,csv}` functions x 18 hostile shapes = 2,880 calls, 0 crashes (all formats).
- No pending task.

## This session (what changed)
- Added `tests/test_scanner_branch_gaps.py` (2 tests): closed two reachable partial branches in `ethscan/scanner.py` that no prior suite covered:
  - `test_scan_port_open_local_listener` (covers 22->24): binds a local TCP listener on an ephemeral port and asserts `scan_port` returns `(port, True)`. Prior suites only exercised the failure path (monkeypatched `create_connection`) or closed ports, so the success-return branch at line 24 was never reached.
  - `test_parse_port_range_empty_token` (covers 94->95): `parse_port_range("80,")` raises `PortSpecError` matching "Empty port token". The whitespace test only exercised non-empty tokens after stripping, so the `if not part:` guard at line 94 was never true.
- No source (`ethscan/`) changes; purely test additions, fully reversible.

## Verified (this session)
- Reproduced the gap first: `coverage run --branch --source=ethscan.scanner` on the existing scanner suites reported `ethscan/scanner.py 127 stmts, 2 miss, 52 branch, 1 BrPart, 98%` with missing lines `[24, 95]` and missing branch `[[94, 95]]`.
- After the new tests: `ethscan/scanner.py` is `127 stmts, 0 miss, 52 branch, 0 BrPart (100%)`.
- `python -m pytest -q` -> 46672 passed, 146 skipped, 0 failed (includes the 2 new tests).
- `python -m mypy ethscan/ tests/` -> Success, no issues in 264 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54/54, 0 drift both directions.
- `git status` -> only `tests/test_scanner_branch_gaps.py` added (plus handoff doc updates).

## Next task (precise)
- **None pending.** Repository fully green with all known limitations resolved or explicitly out of scope. If future work is needed, pick one bounded, high-value improvement, reproduce a concrete gap first (failing check/test or contract deviation), fix minimally, rerun pytest/mypy/ruff/check_readme, and do not weaken safety/validation.

## Known limitations (not in scope)
- `ethscan/cli.py:4318` documented unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- `ethscan/ping.py` raw IPv4 ICMP/stream sockets need ICMPv6/checksum support (privileged, larger change).
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.
- PBKDF2 + NTLM intentionally unsupported.
- Pre-existing `tests/test_ping.py` runtime failures (6 tests) from Python 3.14 making `socket.timeout` a read-only descriptor on `_socket.socket` subclasses — unrelated to this work.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.

(End of file - total 52 lines)