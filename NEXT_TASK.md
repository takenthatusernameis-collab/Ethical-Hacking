# Next Task
Date: Wed Nov 18 2026

## Status
- Green: 39865 passed, 146 skipped, 0 failed; mypy clean (262 files); ruff
  clean; README 54/54 with 0 drift; full-suite branch coverage 100% except
  the documented unreachable `ethscan/cli.py` guard.
- The previously assigned `hash._infer_algorithm` hex fix was already at HEAD
  `c17edb3`; verified, no work needed.
- This session (11) fixed (a) a validate/scan port-spec divergence and (b)
  bare-IPv6 target parsing in 14 modules (see TASK.md).

## This session (what changed)
- `ethscan/validate.py`: `_validate_port_spec` no longer drops empty comma
  tokens. `"80,,443"`, `",80"`, `"80,"`, `"80, ,443"` are now invalid with
  the scanner's `Empty port token in specification: ...` wording, matching
  `ethscan.scanner.parse_port_range`. Comma/whitespace-only specs still say
  "No ports in specification".
- `ethscan/{ftp,ldap,memcached,mongodb,mssql,mysql,netbios,ntp,oracle,
  postgresql,redis,smb,smtp,snmp}.py`: the bare-target port split now
  requires exactly one colon (`host.count(":") == 1`), so unbracketed IPv6
  literals are kept whole as the host (`::1`, `2001:db8::1`). A port on an
  IPv6 literal must be bracketed.
- `tests/test_bare_ipv6_target_parsing.py` (new, 43 tests): per-module
  bare-IPv6 host preservation, host:port / bare-IPv4 split parity, bracketed
  IPv6 parsing, and an `ntp.run_ntp` probe-level regression.
- `tests/test_validate.py` (+2): empty-token rejection and differential
  parity with `parse_port_range`.
- `tests/test_mysql.py`: updated the assertion that codified
  `_normalize_target("2001:db8::1") == ("2001:db8:", 1)`.

## Verified
- Before: `ntp._normalize_target("::1") == (":", 1)`;
  `run_ntp("::1", connector=rec)` calls `rec(":", 1, ...)`.
  After: `("::1", 123)` and `rec("::1", 123, ...)`.
- CLI: `python -m ethscan validate --ports 80,,443 --format json` ->
  `valid: false`, `all_valid: false`; `python -m ethscan ntp --target ::1
  --timeout 0.2 --format json` -> `host: "::1"`, `port: 123`.
- Focused 1325 passed; full suite 39865 passed / 146 skipped (start
  baseline 39820); mypy Success (262 files); ruff clean; `check_readme.py`
  54/54; `git diff --check` clean; touched modules + validate.py 100%
  branch coverage under the full suite.

## Next task
- Make the UDP transports family-aware for the IPv6 targets that now parse
  correctly. Evidence: `ethscan ntp --target ::1 --timeout 0.2
  --format json` still returns
  `"time request failed: [Errno -9] Address family for hostname not
  supported"`; `ntp.py:291` and `netbios.py:479` open
  `socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`. Use
  `socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)` to select the
  family/sockaddr, `sendto(request, sockaddr)`, keep the existing
  error-as-field contract and the `connector` seam, add monkeypatched
  deterministic tests asserting `AF_INET6` for `::1` / `AF_INET` for IPv4,
  keep both modules at 100% branch coverage. Do not change the parsing
  contract established this session.
- Optional follow-up (lower priority): `mac._extract_oui` docstring says
  "24-bit OUI" but returns 8 hex chars; tests codify `"001a2b3c"`. Fix the
  docstring or add a documented 6-hex OUI field only if a task asks.

## Known limitations (intended, out of scope)
- `ethscan/cli.py:4318` is a documented unreachable defensive guard.
- `oracle`/`postgresql` report an unusable target in-band (exit 0) by contract.
- PBKDF2 + NTLM remains intentionally unsupported.
- Other modules (`ldap`, `memcached`, `redis`, `smb`, `snmp`, `dnssec`,
  `osdetect`) also open `AF_INET` sockets directly; they accept IPv6
  targets syntactically but cannot transport to them yet.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network).
- Do not commit manually; the workflow controller commits and verifies pushes.
