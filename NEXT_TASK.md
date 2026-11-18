# Next Task
Date: Wed Nov 18 2026 (session 14 handoff)

## Status
- Green: 39893 passed, 146 skipped, 0 failed; mypy Success (59 source
  files); ruff clean; README 54/54 with 0 drift both directions;
  `git diff --check` clean.
- Full-suite branch coverage 99% for `ethscan/ldap.py` and `ethscan/smb.py`
  (the modules touched this session; missing lines are defensive formatters).
- Uncommitted at handoff: controller will stage/commit
  `ethscan/ldap.py`, `ethscan/smb.py`,
  `tests/test_ldap.py`, `tests/test_smb.py` (tests already present, no diff).

## This session (what changed)
1. Verified the IPv6 transport defect was already fixed in two TCP modules:
   - `ldap.py` `_send_recv` (line ~468) already uses `getaddrinfo` with
     `SOCK_STREAM`/`IPPROTO_TCP`, family-aware socket creation, and
     `connect(sockaddr)`.
   - `smb.py` `_send_recv` (line ~222) already uses the same pattern.
2. Confirmed the four deterministic transport tests per module were already
   present and passing:
   - `test_send_recv_ipv6_uses_af_inet6`
   - `test_send_recv_ipv4_uses_af_inet`
   - `test_send_recv_getaddrinfo_failure_is_reported`
   - `test_send_recv_empty_getaddrinfo_is_reported`
3. Manual verification:
   - `ldap.run_ldap("::1", timeout=0.3)` -> `Connection refused` (Errno 111)
   - `smb.run_smb("::1", timeout=0.3)` -> `Connection refused` (Errno 111)
   - Both IPv4 controls also return `Connection refused`, unchanged.

## Verified
- Focused: 221 passed (`test_ldap.py`, `test_smb.py`,
  `test_ldap_branch_gaps.py`, `test_smb_branch_gaps.py`).
- Full: 39893 passed / 146 skipped; mypy clean; ruff clean; README
  54/54; `git diff --check` clean; full-suite branch coverage 99% on
  `ldap.py` and `smb.py`.

## Next task (precise)
- Extend the same family-aware transport fix to:
  - `ethscan/snmp.py` (UDP, line ~407): use
    `getaddrinfo(..., type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)`
  - `ethscan/dnssec.py` (UDP, lines ~191,233): same UDP pattern
  - `ethscan/osdetect.py` (TCP, lines ~190,230,270): use
    `getaddrinfo(..., type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)`
- For each module:
  1. Reproduce first: `run_<module>("::1", timeout=0.2)` should show Errno -9
     before fix.
  2. Replace hardcoded `AF_INET` socket creation with family-aware pattern.
  3. Add the same 4 deterministic tests per module (family assertions on
     `socket()` args and `connect`/`sendto` sockaddr; failure and
     empty-result paths).
  4. Verify: focused tests, full suite, mypy, ruff, `check_readme.py`,
     `git diff --check`, full-suite branch coverage on all touched modules.

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

(End of file - total 73 lines)