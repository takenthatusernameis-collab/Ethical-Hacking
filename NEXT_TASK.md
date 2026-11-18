# Next Task
Date: Wed Nov 18 2026

## Status
- Green: 39877 passed, 146 skipped, 0 failed; mypy clean (262 source files);
  ruff clean; README 54/54 with 0 drift; full-suite branch coverage 100%
  except the documented unreachable `ethscan/cli.py` guard.
- The previously assigned family-aware-UDP-transport task was already at
  HEAD `92cdefc`; verified, no work needed.
- This session (12) confirmed the `ntp`/`netbios` IPv6 transport fix and
  re-ran the full verification matrix.

## This session (what changed)
- No source changes; the working tree is clean. Confirmed:
  - `ethscan/ntp.py` and `ethscan/netbios.py` `_send_recv` resolve the
    endpoint with `socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM,
    proto=socket.IPPROTO_UDP)`, open the socket for the returned family,
    and `sendto(request, sockaddr)`. The injectable `connector` seam is
    preserved.
  - Deterministic monkeypatched tests assert `AF_INET6` for `::1` and
    `AF_INET` for IPv4 in both modules, plus getaddrinfo-failure and
    empty-result error paths.
  - CLI: `python -m ethscan ntp --target ::1 --timeout 0.2
    --format json` -> `host: "::1"`, `port: 123`, `error: "time request
    failed: timeout"` (no more `[Errno -9] Address family for hostname
    not supported`).

## Verified
- Before (prior session): `ntp._normalize_target("::1") == (":", 1)`;
  `run_ntp("::1", connector=rec)` calls `rec(":", 1, ...)`.
- After: `("::1", 123)` and `rec("::1", 123, ...)`.
- CLI: `python -m ethscan validate --ports 80,,443 --format json` ->
  `valid: false`, `all_valid: false`; `python -m ethscan ntp --target ::1
  --timeout 0.2 --format json` -> `host: "::1"`, `port: 123`.
- Focused 212 passed; full suite 39877 passed / 146 skipped (baseline
  39820); mypy Success (262 source files); ruff clean; `check_readme.py`
  54/54; `git diff --check` clean; `ntp.py`, `netbios.py`, `validate.py`,
  `mac.py` all at 100% branch coverage under the full suite.

## Next task
- None pending from the handoff. The repository is green with 100% branch
  coverage on all touched modules. If future work is needed, pick a single
  high-value, verifiable improvement and reproduce it first — do not
  speculate or weaken safety controls.
- Optional follow-up (lower priority): `mac._extract_oui` docstring says
  "24-bit OUI" but returns 8 hex chars; tests codify `"001a2b3c"`. Fix the
  docstring or add a documented 6-hex OUI field only if a task asks.
- Optional follow-up (lower priority): the remaining `AF_INET`-hardcoded
  transports (`ldap`, `memcached`, `redis`, `smb`, `snmp`, `dnssec`,
  `osdetect`) accept IPv6 targets syntactically but cannot transport to
  them yet; only worth doing if a task asks.

## Known limitations (intended, out of scope)
- `ethscan/cli.py:4318` is a documented unreachable defensive guard.
- `oracle`/`postgresql` report an unusable target in-band (exit 0) by contract.
- PBKDF2 + NTLM remains intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network).
- Do not commit manually; the workflow controller commits and verifies pushes.

(End of file - total 72 lines)