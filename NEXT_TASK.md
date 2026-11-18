# Next Task
Date: Wed Nov 18 2026 (session 13 handoff)

## Status
- Green: 39885 passed, 146 skipped, 0 failed; mypy Success (59 source
  files); ruff clean; README 54/54 with 0 drift both directions;
  `git diff --check` clean.
- Full-suite branch coverage 100% for `ethscan/memcached.py` and
  `ethscan/redis.py` (the modules touched this session).
- Uncommitted at handoff: controller will stage/commit
  `ethscan/memcached.py`, `ethscan/redis.py`,
  `tests/test_memcached.py`, `tests/test_redis.py` (+247/-7).

## This session (what changed)
1. Reproduced the IPv6 transport defect in two TCP modules:
   - `memcached.run_memcached("::1", timeout=0.2)` ->
     `version request failed: [Errno -9] Address family for hostname
     not supported`
   - `redis.run_redis("::1", timeout=0.2)` -> same Errno -9 on ping.
2. Fixed `_send_recv` in both modules to resolve the endpoint with
   `socket.getaddrinfo(host, port, type=socket.SOCK_STREAM,
   proto=socket.IPPROTO_TCP)`, create `socket.socket(family, socktype,
   proto)` from `infos[0]`, and `connect(sockaddr)` — mirroring the
   already-fixed `ntp`/`netbios` pattern. New error strings:
   `"address resolution failed: <exc>"` and
   `"no address found for <host>:<port>"`.
3. Preserved the injectable `connector` seam (short-circuits before
   resolution) and all existing OSError/timeout handling.
4. Added 4 deterministic tests per module (AF_INET6 for `::1`, AF_INET
   for IPv4, getaddrinfo failure, empty result), and made the
   memcached default-socket success test stub `getaddrinfo` so it is
   independent of real `localhost` resolution.

## Verified
- After: `memcached.run_memcached("::1", timeout=0.3)` and
  `redis.run_redis("::1", timeout=0.3)` now report
  `[Errno 111] Connection refused` for IPv6 (transport attempt
  happens; no family error). IPv4 control unchanged.
- Focused: 217 passed (`test_memcached.py`, `test_redis.py`,
  `test_memcached_branch_gaps.py`, `test_redis_branch_gaps.py`).
- Full: 39885 passed / 146 skipped; mypy clean; ruff clean; README
  54/54; `git diff --check` clean; full-suite branch coverage 100% on
  `memcached.py` and `redis.py`.

## Next task (precise)
- Extend the same family-aware TCP fix to `ethscan/ldap.py` (~line 468)
  and `ethscan/smb.py` (~line 222). Both currently do
  `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` +
  `connect((host, port))`.
  1. Reproduce first: `run_ldap("::1", timeout=0.2)` and
     `run_smb("::1", timeout=0.2)` should show Errno -9.
  2. Replace with `getaddrinfo(..., type=socket.SOCK_STREAM,
     proto=socket.IPPROTO_TCP)` + family socket + `connect(sockaddr)`;
     keep the `connector` seam and existing timeout/OSError strings.
  3. Add the same 4 deterministic tests per module (family assertions on
     `socket()` args and `connect` sockaddr; failure and empty-result
     paths).
  4. Verify: focused tests, full suite, mypy, ruff, `check_readme.py`,
     `git diff --check`, full-suite branch coverage 100% on both modules.
- Do not modify `snmp`, `dnssec`, or `osdetect` in that task; they are a
  follow-up (UDP / explicit AF_INET getaddrinfo paths).

## Known limitations (intended, out of scope)
- `ethscan/cli.py:4318` is a documented unreachable defensive guard.
- `oracle`/`postgresql` report an unusable target in-band (exit 0) by contract.
- PBKDF2 + NTLM remains intentionally unsupported.
- `mac._extract_oui` docstring says 24-bit but returns 8 hex chars; tests
  codify current output — do not change without evidence.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network).
- Do not commit manually; the workflow controller commits and verifies pushes.
