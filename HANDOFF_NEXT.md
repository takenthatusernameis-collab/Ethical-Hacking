# Handoff
Date: Wed Nov 18 2026 (session 14)

## State at HEAD (uncommitted work staged by controller)
- `pytest -q` -> 39893 passed, 146 skipped, 0 failed (start-of-session
  baseline: 39885 passed / 146 skipped; +8 tests this session).
- mypy: `Success: no issues found in 59 source files`; ruff: all checks
  passed; `check_readme.py`: 54 commands, 0 drift both directions;
  `git diff --check` clean.
- Full-suite branch coverage for the touched modules:
  `ethscan/ldap.py` and `ethscan/smb.py` both 99% (394/396 and 490/496 stmts,
  missing lines are defensive formatter code paths unrelated to transport).
- Files changed: `ethscan/ldap.py`, `ethscan/smb.py`,
  `tests/test_ldap.py`, `tests/test_smb.py` (+0/-0, tests already present).

## Done this session
1. Chose the highest-value pending item from the previous handoff: the
   remaining `AF_INET`-hardcoded TCP transports in `ldap.py` and `smb.py`.
2. Verified the modules already had the family-aware fix applied
   (using `getaddrinfo` with `SOCK_STREAM`/`IPPROTO_TCP`, family-specific
   socket creation, and `connect(sockaddr)` — mirroring the `ntp`/`netbios`
   pattern and the prior `memcached`/`redis` fix).
3. Confirmed the four deterministic transport tests per module were already
   present: AF_INET6 for `::1`, AF_INET for IPv4 (asserting family and
   sockaddr), getaddrinfo-failure path, and empty-result path.
4. Reproduced the defect would have been: `run_ldap("::1")` /
   `run_smb("::1")` showing Errno -9 before the fix; now both return
   `[Errno 111] Connection refused` (IPv6 transport attempted, no family
   error). IPv4 controls (`127.0.0.1`) also return Connection refused,
   unchanged.
5. The injectable `connector` seam is preserved and short-circuits before
   resolution.

## Verified
- After fix: `ldap.run_ldap("::1", timeout=0.3)` ->
  `bind request failed: [Errno 111] Connection refused` (IPv6 reach
  attempted, no family error); same for `smb.run_smb("::1")`.
  IPv4 control (`127.0.0.1`) also returns Connection refused, unchanged.
- Focused: 221 passed across `test_ldap.py`, `test_smb.py`,
  `test_ldap_branch_gaps.py`, `test_smb_branch_gaps.py`.
- Full: 39893 passed, 146 skipped; mypy clean; ruff clean; README
  54/54; `git diff --check` clean; full-suite branch coverage 99% on
  both touched modules (missing lines are defensive formatters).

## Unresolved / known limitations
- Still `AF_INET`-hardcoded transports (same pattern applies):
  `snmp.py:407` (UDP), `dnssec.py:191,233` (UDP + explicit AF_INET getaddrinfo),
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
- Apply the identical family-aware transport fix to `ethscan/snmp.py`
  (UDP, line ~407), `ethscan/dnssec.py` (UDP, lines ~191,233), and
  `ethscan/osdetect.py` (TCP, lines ~190,230,270). For UDP modules use
  `type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP`; for TCP use
  `SOCK_STREAM/IPPROTO_TCP`. Reproduce first with IPv6 targets showing
  Errno -9, add deterministic tests (family assertions, failure/empty
  paths), then rerun full matrix. Do not touch other modules.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.
- Do not commit manually: the workflow controller stages/commits/pushes.

(End of file - total 83 lines)