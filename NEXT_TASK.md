# Next Task
Date: Fri Nov 20 2026 (session 28) — IPv6 raw-ping fallback fixed; follow-up available.

## Status
- Green: **46693 passed, 146 skipped, 0 failed**; mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean.

## This session (what changed)
- Fixed `ethscan/ping.py`: raw ICMP sockets are IPv4-only, so an IPv6 target with a raw socket available (root) failed every probe with `[Errno -9] Address family for hostname not supported`. IPv6 now uses the family-aware TCP connect fallback; the owned raw socket is closed, `raw_socket_available` is `False`, and a note explains the IPv4-only limitation.
- `probe_icmp` also refuses the raw path when `resolved_family == AF_INET6` (defense in depth for direct callers).
- Added 4 deterministic tests in `tests/test_ping.py`; no IPv4 behavior or formatter changes.

## Verified (this session)
- `pytest tests/test_ping.py -q` -> 68 passed.
- `pytest -q` -> 46693 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- Full-suite coverage: `ethscan/ping.py` 100% (0 missing / 0 partial); total 99% with only `ethscan/cli.py:4336`.

## Known limitations (not in scope)
- IPv6 ping is TCP-connect based; real ICMPv6 is not implemented (documented in the run note).
- `ethscan/cli.py` unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- PBKDF2 + NTLM intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS; fake sockets only).
- Do not commit manually; the workflow controller commits and verifies pushes.

## Next task (for the next agent)
- Implement real ICMPv6 ping in `ethscan/ping.py`: `AF_INET6`/`IPPROTO_ICMPV6` raw sockets, Echo Request type 128 / Reply type 129, IPv6 pseudo-header checksum, family-aware `_try_create_raw_socket`, TCP fallback retained when raw sockets are unavailable. Evidence to start from: this session's reproduction (pre-fix `error: [Errno -9] Address family for hostname not supported`; post-fix `raw_socket_available: False`, `response_type: RST`) and the IPv4-only comment/guard in `probe_icmp`. Reproduce with a fake raw socket, keep `ping.py` at 100% branch coverage, and re-run pytest/mypy/ruff/check_readme.
