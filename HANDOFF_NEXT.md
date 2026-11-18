# Handoff
Date: Wed Nov 18 2026

## State at HEAD (after this session)
- `pytest -q` -> 39865 passed, 146 skipped, 0 failed (true start-of-session
  baseline: 39820 passed / 146 skipped). mypy clean (262 files); ruff clean;
  `check_readme.py` 54/54, 0 drift; `git diff --check` clean.
- Full-suite branch coverage: 100% for every touched module and still 100%
  everywhere except the documented `ethscan/cli.py` defensive guard.
- Working tree: 14 `ethscan/*` modules + `tests/test_mysql.py` +
  `tests/test_validate.py` modified, `tests/test_bare_ipv6_target_parsing.py`
  added. Not committed (controller commits).

## Done this session
1. The assigned next task (`hash._infer_algorithm` rejecting non-hex digests)
   was ALREADY implemented and committed at HEAD `c17edb3`; the handoff was
   stale. Verified: `_infer_algorithm("z"*32) is None`, `run_check("x",
   "z"*32)["algorithm"] is None` + "Could not infer algorithm ..." error.
   No work needed; the handoff files are corrected below.
2. Fixed a real validation/scanner divergence in `ethscan/validate.py`:
   `_validate_port_spec` silently dropped empty comma tokens, so
   `ethscan validate --ports "80,,443"` reported `valid: true,
   all_valid: true` while `ethscan scan --ports "80,,443"` failed with
   `PortSpecError: Empty port token in specification: '80,,443'`.
   Validation now accepts exactly the specs `parse_port_range` accepts and
   reports the scanner's wording. Comma/whitespace-only specs still report
   "No ports in specification" (existing contract).
3. Fixed bare-IPv6 target parsing across 14 modules (`ftp`, `ldap`,
   `memcached`, `mongodb`, `mssql`, `mysql`, `netbios`, `ntp`, `oracle`,
   `postgresql`, `redis`, `smb`, `smtp`, `snmp`). The shared
   `_normalize_target` split the last colon of an unbracketed IPv6 literal
   as a port: `ntp._normalize_target("::1")` -> `(':', 1)` and
   `"2001:db8::1"` -> `('2001:db8:', 1)`, so `run_ntp("::1", connector=...)`
   dialled host `:` port `1`. The port split now requires exactly one colon;
   a port on an IPv6 literal must be bracketed. Updated the mysql test that
   codified the old `("2001:db8:", 1)` behavior.

## Verified
- Repro before fix: `run_ntp("::1", connector=rec)` called
  `rec(':', 1, ...)`; after fix `rec('::1', 123, ...)`.
- CLI after fix: `python -m ethscan ntp --target ::1 --timeout 0.2
  --format json` -> `host: "::1"`, `port: 123` (before: host `":"`,
  port `1`).
- Focused: 1325 passed across the 14 affected test files + the new file.
- Full: 39865 passed, 146 skipped (baseline 39820; +43 IPv6 tests, +2
  validate tests).
- mypy `Success: no issues found in 262 source files`; ruff all checks
  passed; `check_readme.py` 54 commands, 0 drift both directions;
  `git diff --check` clean.
- Coverage (`coverage run --branch --source=ethscan -m pytest -q`): all 14
  touched modules + `validate.py` at 100% branch coverage.

## Unresolved / known limitations
- `ntp._send_recv` and `netbios._send_recv` still hardcode
  `socket.AF_INET` for their UDP sockets, so a now-correctly parsed IPv6
  literal still fails with `[Errno -9] Address family for hostname not
  supported`. The same hardcoding exists in the stream transports of
  `ldap`, `memcached`, `redis`, `smb`, `snmp`, `dnssec` and `osdetect`.
  See next task.
- `cli.py:4318` unreachable defensive guard (unchanged).
- `oracle`/`postgresql` in-band empty-target handling by contract.
- PBKDF2+NTLM intentionally unsupported.
- `mac._extract_oui` docstring says "24-bit OUI" but returns 8 hex chars
  (first 4 octets); many tests codify `"001a2b3c"`. Documentation/contract
  mismatch only; do not change output without evidence.

## Approaches already tried / ruled out
- Interpreting a bare IPv6+port (`::1:3306`) as host+port by testing the
  prefix with `ipaddress`: rejected as ambiguous (`fe80::abcd:1` is itself a
  valid literal) and inconsistent with "IPv6 ports require brackets"; the
  whole literal is kept as the host, matching `target._bracket_ipv6_netloc`'s
  documented ambiguity note.
- Treating only IPv6 addresses that fail `ipaddress.ip_address` as hosts:
  rejected; the failure mode is precisely valid literals ending in a numeric
  group.
- Reusing `parse_port_range` inside `validate`: still rejected (the module
  needs per-spec, in-band error messages); parity is now asserted by a
  differential test instead.

## Next task
- Make the UDP transports family-aware so a parsed IPv6 target is actually
  usable. Evidence: `python -m ethscan ntp --target ::1 --timeout 0.2
  --format json` -> `error: "time request failed: [Errno -9] Address family
  for hostname not supported"` even though `host` is now `"::1"`.
  `ethscan/ntp.py:291` and `ethscan/netbios.py:479` construct
  `socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`. Resolve the endpoint
  with `socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)`, open the
  socket for the returned family, and `sendto(request, sockaddr)`, keeping
  the existing error-as-field contract and the injectable `connector` seam.
  Add deterministic tests that monkeypatch `socket.getaddrinfo` /
  `socket.socket` and assert `AF_INET6` is selected for `::1` (and `AF_INET`
  for IPv4), without real network access. Keep `ntp.py`/`netbios.py` at 100%
  branch coverage and re-run pytest/mypy/ruff/check_readme/full coverage.
  Do not change the target-parsing contract established this session.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.
- Do not commit manually: the workflow controller stages/commits/pushes.
