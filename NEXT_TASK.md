# Next Task
Date: Thu Nov 19 2026 (session 20)

## Status
- Green: **46653 passed, 146 skipped, 0 failed**; mypy Success (262 source files; `--check-untyped-defs` clean); `ruff check ethscan tests` clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; one test fix applied (see HANDOFF_NEXT.md).
- Formatter fuzzer (prior session): 160 `format_*_report_{json,markdown,csv}` functions x 18 hostile shapes = 2,880 calls, 0 crashes (all formats).
- No uncommitted changes beyond the `tests/test_ping.py` fix. No pending task.

## This session (what changed)
- Reproduced a real baseline failure: `tests/test_ping.py::test_ping_tcp_fallback_ipv6_family_sets_hop_limit` raised `NameError: name 'results' is not defined` (the body called `probe_icmp` directly but then used undefined `results`-based assertions).
- Fixed `tests/test_ping.py` minimally: replaced the undefined-`results` assertions with an assertion that the IPv6 TCP-fallback path sets `IPV6_UNICAST_HOPS` to the TTL (matching the test's documented intent), and added instance tracking to the local `_FakeSocket`.
- No source (`ethscan/`) changes; purely a test fix, fully reversible.

## Verified (this session)
- `python -m pytest -q` -> 46653 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 262 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python3 check_readme.py` -> 54/54, 0 drift both directions.
- `git status` -> only `tests/test_ping.py` modified.

## Next task (precise)
- **None pending.** Repository fully green with all known limitations resolved or explicitly out of scope. If future work is needed, pick one bounded, high-value improvement, reproduce a concrete gap first (failing check/test or contract deviation), fix minimally, rerun pytest/mypy/ruff/check_readme, and do not weaken safety/validation.

## Known limitations (not in scope)
- `ethscan/cli.py:4318` documented unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- `ethscan/ping.py` raw IPv4 ICMP/stream sockets need ICMPv6/checksum support (privileged, larger change).
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.
- PBKDF2 + NTLM intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.
