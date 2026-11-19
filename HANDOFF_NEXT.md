# Handoff
Date: Thu Nov 19 2026 (session 15)

## State at HEAD (working tree, controller will stage/commit)
- `pytest -q` -> 39921 passed, 146 skipped, 0 failed.
- mypy: `Success: no issues found in 59 source files`; `ruff check ethscan tests`:
  all checks passed; `check_readme.py`: 54 commands, 0 drift both directions;
  `git diff --check` clean.
- Files changed: `ethscan/whois.py`, `tests/test_whois.py`.

## Done this session
1. Read `HANDOFF_NEXT.md`/`NEXT_TASK.md` from session 14. Their requested
   next task (family-aware IPv6 transport for `snmp.py`, `dnssec.py`,
   `osdetect.py`) was already implemented at HEAD: all three modules already
   use `socket.getaddrinfo` with `SOCK_DGRAM`/`SOCK_STREAM` +
   `IPPROTO_UDP`/`IPPROTO_TCP`, and the deterministic IPv4/IPv6/failure/empty
   tests already exist. Re-verified: 350 passed across
   `test_snmp.py`, `test_dnssec.py`, `test_osdetect.py` (no code change).
2. Picked the next bounded item from that handoff's unresolved list: the
   hardcoded `socket.AF_INET` TCP transport in `ethscan/whois.py`
   (`query_whois`, was line ~40). Real WHOIS servers are reachable over IPv6.
3. Replaced the hardcoded socket with the established family-aware pattern:
   `getaddrinfo(server, port, type=SOCK_STREAM, proto=IPPROTO_TCP)`,
   family/socktype/proto from `infos[0]`, `connect(sockaddr)`; empty
   resolution raises `OSError("no address found for host:port")`.
4. Kept the existing exception-propagation contract of `query_whois`
   (gaierror/timeout/ConnectionRefusedError still raise; `run_whois` still
   converts them into its `error` field). No validation/exit-code changes.
5. Tests: made the three existing socket tests deterministic by stubbing
   `ethscan.whois.socket.getaddrinfo` (previously they relied on real DNS).
   Added four tests: IPv6 -> AF_INET6 + IPv6 sockaddr, IPv4 -> AF_INET,
   getaddrinfo failure raises, empty getaddrinfo raises.

## Verified
- Manual: `whois.query_whois("example.com", server="::1", port=43,
  timeout=0.3)` -> `ConnectionRefusedError(111, 'Connection refused')`
  (IPv6 transport attempted, no Errno -9 family error); IPv4 control
  (`127.0.0.1`) also returns Connection refused, unchanged.
- Focused: 50 passed (`tests/test_whois.py`).
- Full: 39921 passed, 146 skipped; mypy 59 files clean; ruff clean;
  README 54/54, 0 drift both directions; `git diff --check` clean.
- Branch coverage tooling (`pytest-cov`/`coverage`) is not installed in this
  environment; focused/full test evidence used instead.

## Unresolved / known limitations
- Remaining `AF_INET`-hardcoded transports (same family-aware pattern
  applies):
  - `ethscan/trace.py:54` TCP probe socket plus `socket.gethostbyname`
    (IPv4-only) in `_trace_single`; needs `getaddrinfo`, an AF_INET6
    sockaddr, and `IPV6_UNICAST_HOPS` (guarded by `hasattr`) instead of
    `IP_TTL` for IPv6. Many `tests/test_trace.py` cases patch
    `socket.gethostbyname`/`_probe_once`, so this is a larger, contract-
    sensitive change; plan test migration explicitly.
  - `ethscan/ping.py:158,213,286` raw IPv4 ICMP/stream sockets (privileged,
    ICMPv6 checksum work required; out of scope for a small change).
  - `ethscan/dns.py:58`, `resolve.py:67`, `stale.py:53`,
    `subtake.py:317,352` call `getaddrinfo(..., AF_INET)` for A-record /
    canonical-name lookups. This is likely intentional (IPv4-only A record
    semantics); do not change without evidence and a documented contract.
- `ethscan/cli.py:4318` unreachable defensive guard (documented).
- `oracle`/`postgresql` in-band empty-target handling by contract.
- PBKDF2+NTLM intentionally unsupported.
- `mac._extract_oui` docstring/contract mismatch (returns 8 hex chars);
  do not change output without evidence.

## Approaches already tried / ruled out
- Interpreting a bare `IPv6:port` as host+port: rejected as ambiguous.
- Sharing `parse_port_range` in `validate`: rejected; parity asserted by
  differential test instead.
- Do not weaken validation or exit-code contracts to make IPv6 "work".
- Do not add network-dependent tests: always stub `getaddrinfo`/`socket`.

## Next task
- Apply the identical family-aware TCP transport fix to `ethscan/trace.py`
  (`_probe_once` + `_trace_single`). Replace `socket.gethostbyname` with
  `getaddrinfo(host, port, type=SOCK_STREAM, proto=IPPROTO_TCP)`, create the
  socket from the resolved family and connect to the resolved sockaddr; use
  `IP_TTL` for AF_INET and `IPV6_UNICAST_HOPS` for AF_INET6 (guarded with
  `hasattr`/try-except so platforms without it still work). Reproduce first:
  `trace._trace_single("::1", 80, 1, 0.2, 1)` should fail resolution or
  family before the fix. Migrate the `tests/test_trace.py` patches that
  target `gethostbyname`/`_probe_once` deterministically, then add family
  assertion tests (AF_INET6 sockaddr, AF_INET control, resolution failure,
  empty result). Rerun focused + full suite, mypy, ruff, `check_readme.py`,
  `git diff --check`. Do not touch other modules.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5.
- `pytest-cov`/`coverage` are NOT installed; do not rely on `--cov`.
- Do not commit manually: the workflow controller stages/commits/pushes.
