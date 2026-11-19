# Next Task
Date: Thu Nov 19 2026 (session 15 handoff)

## Status
- Green: 39921 passed, 146 skipped, 0 failed; mypy Success (59 source
  files); `ruff check ethscan tests` clean; README 54/54 with 0 drift both
  directions; `git diff --check` clean.
- Uncommitted at handoff: controller will stage/commit
  `ethscan/whois.py`, `tests/test_whois.py`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md`.

## This session (what changed)
1. Confirmed the prior handoff's requested work (family-aware IPv6
   transports in `ethscan/snmp.py`, `ethscan/dnssec.py`,
   `ethscan/osdetect.py`) was already present and tested at HEAD; 350
   focused tests passed with no edits.
2. Made the WHOIS TCP transport family-aware in `ethscan/whois.py`
   (`query_whois`):
   - `socket.getaddrinfo(server, port, type=SOCK_STREAM,
     proto=IPPROTO_TCP)`
   - socket created from the resolved `family, socktype, proto`
   - `sock.connect(sockaddr)` instead of `connect((server, port))`
   - empty resolution -> `OSError("no address found for host:port")`
   - existing raise-on-transport-error contract preserved.
3. Made the three existing `tests/test_whois.py` socket tests
   deterministic by stubbing `ethscan.whois.socket.getaddrinfo`, and added:
   - `test_query_whois_ipv6_uses_af_inet6`
   - `test_query_whois_ipv4_uses_af_inet`
   - `test_query_whois_getaddrinfo_failure_is_reported`
   - `test_query_whois_empty_getaddrinfo_is_reported`

## Verified
- Manual: IPv6 target `::1` -> Connection refused (Errno 111), no family
  error; IPv4 control `127.0.0.1` -> Connection refused, unchanged.
- Focused: 50 passed (`tests/test_whois.py`).
- Full: 39921 passed / 146 skipped; mypy clean; ruff clean; README
  54/54 with no drift; `git diff --check` clean.
- Note: `pytest-cov`/`coverage` are not installed in this environment.

## Next task (precise)
- Extend the same family-aware TCP transport to `ethscan/trace.py`:
  - Replace `socket.gethostbyname(host)` in `_trace_single` with
    `getaddrinfo(host, port, type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP)`; keep the existing failure result dict shape
    (all documented keys preserved, `error` populated).
  - Thread the resolved `family`/`sockaddr` into `_probe_once` (keep a
    backward-compatible signature or update call sites/tests together).
  - Use `IPPROTO_IP`/`IP_TTL` for AF_INET and
    `IPPROTO_IPV6`/`IPV6_UNICAST_HOPS` for AF_INET6, guarded with
    `hasattr`/try-except so unsupported platforms still work.
  - Keep `normalize_host`/`TargetSpecError` behavior unchanged.
- Test migration + additions:
  1. Reproduce first: IPv6 literal should fail resolution/family before
     the fix.
  2. Update `tests/test_trace.py` cases that patch
     `ethscan.trace.socket.gethostbyname` or `_probe_once` so they stub
     `getaddrinfo` deterministically (no real DNS).
  3. Add family assertion tests: AF_INET6 sockaddr passed to
     `connect`/`_probe_once`, AF_INET control, resolution failure, empty
     getaddrinfo.
- Verify: focused trace tests, full suite, mypy, ruff, `check_readme.py`,
  `git diff --check`.

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
