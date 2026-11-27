# Handoff

## Status
Repository fully green. Full gate re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49948 passed, 147 skipped, 0 failed (EXIT 0, 145s)
- `python -m coverage report` -> TOTAL 100% (16295 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 276 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

## What changed (this session)
Fixed a REAL, reproduced defect in the MySQL handshake parser (no prior session had found it):
- `ethscan/mysql.py::_parse_handshake`: `auth-plugin-data-part-1` is a FIXED 8-byte field
  followed by a single filler (0x00) byte. The old code located the end of the salt with
  `payload.find(b"\x00", salt1_start)`, which is wrong: the salt bytes are random and may
  legitimately contain 0x00. Whenever a salt byte was zero, the salt was truncated and every
  subsequent field (capabilities/charset/status/auth-plugin-data) was misaligned.
  New code reads the fixed 8-byte window (clamped to available bytes for a truncated packet)
  and then consumes one filler byte when present. Removed the now-dead `salt1_len < 0` /
  `salt1_len > 12` / `null1 != -1` branches.
- `tests/test_mysql.py`: updated the ~10 `_parse_handshake` tests that encoded the old lenient
  short-salt behavior (`b"s\x00"`, `b"salt1\x00"`) to spec-compliant 8-byte salts + filler,
  preserving each test's original early-return branch intent. Added two new tests:
  - `test_parse_handshake_null_byte_in_salt` (regression for the actual defect: 8-byte salt
    `b"ab\x00defgh"` still yields correct capabilities/charset/status).
  - `test_parse_handshake_truncated_salt` (covers the clamped-window / no-filler path when a
    packet ends mid-salt).

## What was actually verified (first-hand this session)
- Reproduction BEFORE fix: independent builder oracle over 20000 randomized well-formed
  handshakes -> 653 mismatches (every case whose 8-byte salt contained a 0x00 byte).
- After fix: same oracle -> 0 mismatches across 20000 trials.
- Focused: `pytest tests/test_mysql*.py` -> 151 passed; `coverage` on mysql.py -> 100% (0 missing).
- Full gate re-verified first-hand (numbers above).

## What remains unresolved
- None blocking.

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile
  sweeps; CLI target/option sweeps; radix math + property tests; target.py parsers; hash/passwords/
  jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/
  stale/subdomains; validate<->cidr; validate<->scanner ports; osdetect checksum; cve version-range;
  mac OUI; empty-host normalization; findings/security_flags hardening; README drift guards;
  audit/hash/report/vuln; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/
  wifi/mongodb+ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service; mac/osdetect/hash/
  version_tuple oracles; 3000-trial radix merge; `_assess_web_server_version`, `_parse_url`,
  `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json
  bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`;
  `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless
  authority; `trace._extract_hop_ips` dedup; click 8.2+ support; `_CheckedDefaultMap` coverage;
  `report.py` nested scalars; `nmap._escape` newline handling; `nmap._finding_detail`; `nmap`
  formatters hostile; `vuln.parse_banner`; `nmap.run_nmap` aggregation; `cve._lookup_cve_id`
  whitespace/case normalization; snmp BER round-trip + `_normalize_communities`/`_normalize_valid_
  communities` property; tls `_resolve_versions`/`_validate_ciphers`/`enumerate_tls` property —
  all clean or already fixed.)
- NEW this session (do NOT repeat without new evidence): mysql `_parse_handshake` salt1 fixed
  8-byte read — defect found and fixed; 20000-trial oracle now clean.

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100% on a clean run. Do NOT repeat verification-only
  sessions without NEW evidence or a NEW angle.
- If future work is needed, reproduce a concrete gap first (focused failing check or behavioral
  evidence vs the documented protocol/contract), apply the smallest safe fix, then rerun focused then
  broader gates. Candidate untouched areas NOT yet oracle-verified in prior handoffs: `redis._parse_resp`
  RESP round-trip vs an independent oracle; `mysql._parse_handshake` full-field round-trip (salt2 /
  auth_plugin_name offsets) vs an independent builder. Reproduce before changing anything.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate
  (`python -m coverage erase && python -m coverage run -m pytest -q`, `python -m coverage report`,
  `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`,
  `python3 check_readme.py`). NOTE: `coverage`/`mypy`/`ruff` are invoked via `python -m`
  (bare `coverage` is not on PATH).

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence),
  then rerun the full gate. If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change
  without a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2) is INTENTIONAL and tested; do NOT
  align to cidr's anycast convention without a reproduced failure.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded
  stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change
  without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests).
- `snmp._assess_snmp_version` requires a DOTTED version; `windows server` threshold unreachable for
  bare "Windows Server 2016". Do NOT change the regex without a reproduced functional failure.
- MySQL `_parse_handshake` is "best-effort"; the salt1 field is now spec-correct (fixed 8 bytes +
  filler). Do not reintroduce null-terminated salt scanning.
- Do not commit manually; the workflow controller stages and commits.

(End of file)