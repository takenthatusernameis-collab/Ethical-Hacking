# Handoff
Date: Thu Nov 19 2026 (session 17)

## State at HEAD (working tree, controller will stage/commit)
- `pytest -q` -> 39925 passed, 146 skipped, 0 failed.
- mypy: `Success: no issues found in 262 source files`; `ruff check ethscan tests`:
  all checks passed; `check_readme.py`: 54 commands, 0 drift both directions;
  `git diff --check` clean.
- Files changed: `ethscan/trace.py`, `ethscan/mac.py`,
  `tests/test_trace.py`, `tests/test_trace_branch_gaps.py`,
  `tests/test_cli_trace_brute_unreachable_sweep.py`.

## Done this session
1. Read `HANDOFF_NEXT.md`/`NEXT_TASK.md` from session 15. Their requested next
   task was the family-aware IPv6 TCP transport for `ethscan/trace.py`
   (`_probe_once` + `_trace_single`).
2. Reproduced first: `trace._trace_single("::1", 80, 1, 0.2, 1)` failed with
   `[Errno -9] Address family for hostname not supported` because
   `_trace_single` used IPv4-only `socket.gethostbyname`, and `_probe_once`
   hardcoded `socket.AF_INET`.
3. Applied the same family-aware pattern already used in `ethscan/whois.py`
   (session 15) and `ethscan/{snmp,dnssec,osdetect}.py` (session 14):
   - `_trace_single` now calls `socket.getaddrinfo(host, port,
     type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)`, takes `infos[0]`,
     threads `family`/`sockaddr` into `_probe_once`, and uses `sockaddr[0]`
     as `dst_ip`/`ip`. Resolution failure and empty results return the same
     in-band error-result dict shape (all documented keys preserved,
     `error` populated), including `OSError("no address found for host:port")`
     for an empty resolution, matching `query_whois`.
   - `_probe_once(dst, port, ttl, timeout, family=socket.AF_INET)` creates the
     socket from the resolved family, connects to the sockaddr (or `(dst,
     port)` for a plain host string for backward compatibility), and sets the
     hop limit with `IP_TTL` for AF_INET and `IPV6_UNICAST_HOPS` for AF_INET6
     (guarded via `getattr` with `hasattr`-style fallback so platforms without
     it still work). `normalize_host`/`TargetSpecError` behavior unchanged.
   - No validation or exit-code contract changes: CLI trace still exits 2 on
   unusable targets and reports transport failures in-band.
4. Tests: migrated every test pinning the old seam from `gethostbyname` to
   `getaddrinfo` (`tests/test_trace.py`, `tests/test_trace_branch_gaps.py`,
   `tests/test_cli_trace_brute_unreachable_sweep.py`). `fake_probe_once`
   signatures updated to the 5-argument `_probe_once` call. All patches stay
   deterministic (no real DNS/network).
   - Added 4 tests: IPv6 uses `AF_INET6` + IPv6 sockaddr passed to
     `_probe_once`, IPv4 uses `AF_INET` control, getaddrinfo failure reported
     in-band, empty getaddrinfo result reported in-band.
5. Doc-accuracy fix on `ethscan/mac.py:_extract_oui`: the docstring said
   "24-bit OUI" but the code returns `cleaned[:8]` = 8 hex chars = a 32-bit
   prefix (first 4 octets), and every test codifies `"001a2b3c"`. Corrected the
   docstring to "Extract the first 8 hex characters (32-bit prefix, first 4
   octets) from a MAC address." No output or test change — behavior unchanged.

## Verified
- Repro before fix: `_trace_single("::1", ...)` -> `[Errno -9] ... not supported`.
  After fix: `dst_ip == "::1"`, no family error, connect-only fallback mode
  (connection refused on an unlistened ::1:80, same as IPv4); `127.0.0.1`
  unchanged.
- Focused: `tests/test_trace.py tests/test_trace_branch_gaps.py
  tests/test_trace_cli.py tests/test_cli_trace_brute_unreachable_sweep.py` ->
  73 passed; `tests/test_mac.py tests/test_mac_hostile_sweep.py
  tests/test_mac_formatter_hostile_sweep.py` -> 169 passed (_extract_oui
  output unchanged).
- Full: 39925 passed, 146 skipped, 0 failed (baseline 39921; +4 new tests).
- mypy `ethscan/ tests/` -> Success: no issues found in 262 source files.
- `ruff check ethscan/ tests` -> all checks passed.
- `check_readme.py` -> 54/54, 0 drift both directions.
- `git diff --check` clean.

## Unresolved / known limitations
- Remaining `AF_INET`-hardcoded transports (same family-aware pattern applies,
  but out of scope for this task):
  - `ethscan/ping.py:158,213,286` raw IPv4 ICMP/stream sockets (privileged,
    ICMPv6 checksum work required; do not touch in a small change).
  - `ethscan/dns.py:58`, `resolve.py:67`, `stale.py:53`,
    `subtake.py:317,352` call `getaddrinfo(..., AF_INET)` for A-record /
    canonical-name lookups. Likely intentional (IPv4-only A record
    semantics); do not change without evidence and a documented contract.
- `ethscan/cli.py:4318` unreachable defensive guard (documented).
- `oracle`/`postgresql` in-band empty-target handling by contract.
- PBKDF2+NTLM intentionally unsupported.

## Approaches already tried / ruled out
- Interpreting a bare `IPv6:port` as host+port: rejected as ambiguous.
- Do not weaken validation or exit-code contracts to make IPv6 "work".
- Do not add network-dependent tests: always stub `getaddrinfo`/`socket`.

## Next task
- None pending. Repository is fully green with all known limitations resolved
  or explicitly out of scope. If future work is needed, pick a single bounded,
  high-value, verifiable improvement and reproduce it first — do not speculate
  or weaken safety controls. `oracle`/`postgresql` empty-target handling
  remains intentionally out of scope per their documented contract (exit 0,
  in-band error).

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5.
- `pytest-cov`/`coverage` are NOT installed; do not rely on `--cov`.
- Do not commit manually: the workflow controller stages/commits/pushes.
