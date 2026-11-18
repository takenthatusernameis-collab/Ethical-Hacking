# Handoff
Date: Wed Nov 18 2026 (session 13)

## State at HEAD (uncommitted work staged by controller)
- `pytest -q` -> 39885 passed, 146 skipped, 0 failed (start-of-session
  baseline: 39877 passed / 146 skipped; +8 tests this session).
- mypy: `Success: no issues found in 59 source files`; ruff: all checks
  passed; `check_readme.py`: 54 commands, 0 drift both directions;
  `git diff --check` clean.
- Full-suite branch coverage for the touched modules:
  `ethscan/memcached.py` and `ethscan/redis.py` both 100% (270/270 and
  305/305 stmts, 0 partial branches).
- Files changed: `ethscan/memcached.py`, `ethscan/redis.py`,
  `tests/test_memcached.py`, `tests/test_redis.py` (+247/-7).

## Done this session
1. Chose the highest-value pending item from the previous handoff: the
   remaining `AF_INET`-hardcoded transports, bounded to two TCP modules
   (`memcached`, `redis`).
2. Reproduced the defect first:
   `python -c "from ethscan import memcached, redis;
   print(memcached.run_memcached('::1', timeout=0.2))"` ->
   `version request failed: [Errno -9] Address family for hostname
   not supported`; same for `redis.run_redis('::1')` / `ping request
   failed: [Errno -9] ...`.
3. Fixed both `_send_recv` helpers to mirror the `ntp`/`netbios` pattern:
   resolve with `socket.getaddrinfo(host, port, type=socket.SOCK_STREAM,
   proto=socket.IPPROTO_TCP)`, take `infos[0]`, create
   `socket.socket(family, socktype, proto)`, and `connect(sockaddr)`.
   Resolution failure -> `"address resolution failed: <exc>"`; empty
   result -> `"no address found for host:port"`. The injectable
   `connector` seam still short-circuits before resolution.
4. Added deterministic tests (no real network): AF_INET6 for `::1`,
   AF_INET for IPv4 (asserting the family passed to `socket()` and the
   sockaddr passed to `connect`), getaddrinfo-failure path (no socket
   created), and empty-result path. Updated the existing memcached
   default-socket success test to stub `getaddrinfo` so it no longer
   depends on real `localhost` resolution.

## Verified
- After fix: `memcached.run_memcached("::1", timeout=0.3)` ->
  `version request failed: [Errno 111] Connection refused` (IPv6 reach
  attempted, no family error); same for `redis.run_redis("::1")`.
  IPv4 control (`127.0.0.1`) also returns Connection refused, unchanged.
- Focused: 217 passed across `test_memcached.py`, `test_redis.py`,
  `test_memcached_branch_gaps.py`, `test_redis_branch_gaps.py`.
- Full: 39885 passed, 146 skipped; mypy/ruff/README/diff-check clean;
  full-suite branch coverage 100% on both touched modules.

## Unresolved / known limitations
- Still `AF_INET`-hardcoded transports (same pattern applies):
  `ldap.py:468` (TCP), `smb.py:222` (TCP), `snmp.py:407` (UDP),
  `dnssec.py:191,233` (UDP + explicit AF_INET getaddrinfo),
  `osdetect.py:190,230,270` (TCP). They accept IPv6 targets
  syntactically but cannot transport to them yet.
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

## Next task
- Apply the identical family-aware TCP fix to `ethscan/ldap.py` (line
  ~468) and `ethscan/smb.py` (line ~222): replace
  `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` +
  `connect((host, port))` with `getaddrinfo(..., type=SOCK_STREAM,
  proto=IPPROTO_TCP)` + family-specific socket + `connect(sockaddr)`,
  keeping the `connector` seam and existing error strings. Reproduce
  first with `run_ldap("::1")` / `run_smb("::1")` showing Errno -9, add
  the same four deterministic tests per module, then rerun the full
  matrix (pytest, mypy, ruff, `check_readme.py`, `git diff --check`,
  full-suite coverage on both modules). Do not touch `snmp`, `dnssec`,
  or `osdetect` in the same task.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.
- Do not commit manually: the workflow controller stages/commits/pushes.
