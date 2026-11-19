# Next Task
Date: Thu Nov 19 2026 (session 16)

## Status
- Green: 39925 passed, 146 skipped, 0 failed; mypy Success (262 source
  files); `ruff check ethscan tests` clean; README 54/54 with 0 drift both
  directions; `git diff --check` clean.
- Uncommitted at handoff: controller will stage/commit
  `ethscan/trace.py`, `tests/test_trace.py`,
  `tests/test_trace_branch_gaps.py`,
  `tests/test_cli_trace_brute_unreachable_sweep.py`,
  `HANDOFF_NEXT.md`, `NEXT_TASK.md`.

## This session (what changed)
1. Confirmed the prior handoff's requested work (family-aware IPv6 transports
   in `ethscan/snmp.py`, `ethscan/dnssec.py`, `ethscan/osdetect.py`) was
   already present and tested at HEAD; no changes needed there.
2. Made the `trace` TCP transport family-aware in `ethscan/trace.py`
   (`_probe_once` + `_trace_single`), following the established whois.py
   pattern:
   - `socket.getaddrinfo(host, port, type=SOCK_STREAM, proto=IPPROTO_TCP)`
     replaces `socket.gethostbyname(host)` in `_trace_single`.
   - Socket created from the resolved `family, socktype, proto`; `connect` to
     the resolved `sockaddr` (existing failure result dict shape preserved,
     `error` populated; empty resolution ->
     `OSError("no address found for host:port")`).
   - `IP_TTL` for AF_INET and `IPV6_UNICAST_HOPS` for AF_INET6 (guarded with
     `getattr(..., None)` so platforms without it still work).
   - Existing raise-on-transport-error and `TargetSpecError` contracts
     preserved.
3. Migrated tests pinning the old seam (`gethostbyname`/`_probe_once`) to
   `getaddrinfo` in `tests/test_trace.py`,
   `tests/test_trace_branch_gaps.py`,
   `tests/test_cli_trace_brute_unreachable_sweep.py` (deterministic stubs, no
   real network), and added 4 family-assertion tests:
   - `test_trace_single_ipv6_uses_af_inet6`
   - `test_trace_single_ipv4_uses_af_inet`
   - `test_trace_single_getaddrinfo_failure_is_reported`
   - `test_trace_single_empty_getaddrinfo_is_reported`

## Verified
- Repro before fix: `trace._trace_single("::1", 80, 1, 0.2, 1)` -> `[Errno -9]
  Address family for hostname not supported`. After fix: `dst_ip == "::1"`,
  no family error, connect-only fallback; IPv4 control unchanged.
- Focused: 73 passed across the four trace test files.
- Full: 39925 passed / 146 skipped; mypy clean; ruff clean; README 54/54 with
  no drift; `git diff --check` clean.
- Note: `pytest-cov`/`coverage` are not installed in this environment.

## Next task (precise)
- None pending. Repository is fully green. If future work is needed, pick a
  single bounded, high-value, verifiable improvement and reproduce it first —
  do not speculate or weaken safety controls.

## Known limitations (not in scope)
- `ethscan/ping.py` raw IPv4 ICMP sockets need ICMPv6/checksum support
  (privileged, larger change) — do not touch in this task.
- `ethscan/dns.py`, `resolve.py`, `stale.py`, `subtake.py` use
  `getaddrinfo(..., AF_INET)` for A-record/canonical-name lookups; treat as
  intentional unless evidence says otherwise.
- `ethscan/cli.py:4318` documented unreachable guard.
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- PBKDF2 + NTLM intentionally unsupported.
- `mac._extract_oui` returns 8 hex chars despite docstring; tests codify it.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.
