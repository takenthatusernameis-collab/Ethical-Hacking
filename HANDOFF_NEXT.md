# Handoff

## Status
Repository fully green. Full gate re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49944 passed, 147 skipped, 0 failed (EXIT 0, 143s)
- `python -m coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 276 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

## What changed (this session)
No production (`ethscan/`) code changed. Added two seeded property tests vs independent oracles for previously-untouched pure helpers:
- `tests/test_tls.py::test_resolve_versions_property_vs_oracle` (500 randomized trials): `_resolve_versions` normalization of string aliases (from `VERSION_ALIASES`), `ssl.TLSVersion` members, and invalid specs; verifies correct resolution and error collection vs hand oracle.
- `tests/test_tls.py::test_validate_ciphers_property_vs_oracle` (500 randomized trials): `_validate_ciphers` normalization of valid cipher names (exact `COMMON_CIPHERS` matches), whitespace stripping, empty-string skipping, and invalid-cipher error collection vs hand oracle.
- `tests/test_snmp.py`: removed unused imports `_normalize_communities`, `_normalize_valid_communities` (ruff F401 fix).

## What was actually verified (first-hand this session)
- New tests: 2 passed in focused run; full `tests/test_tls.py` 78 passed.
- Full gate re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
  - `python -m coverage erase && python -m coverage run -m pytest -q` -> 49944 passed, 147 skipped, 0 failed (EXIT 0, 143s)
  - `python -m coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
  - `python -m mypy ethscan/ tests/` -> Success: no issues found in 276 source files
  - `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
  - `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Fresh-angle property probes of `_resolve_versions`/`_validate_ciphers` vs independent oracles: 0 mismatches across 1000 seeded trials, no defect reproduced.

## What remains unresolved
- None blocking.

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile sweeps; CLI target/option sweeps; radix math + property tests; target.py parsers; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr; validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization; findings/security_flags hardening; README drift guards; audit/hash/report/vuln; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/wifi/mongodb+ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service; mac/osdetect/hash/version_tuple oracles; 3000-trial radix merge; `_assess_web_server_version`, `_parse_url`, `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`; `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless authority; `trace._extract_hop_ips` dedup; click 8.2+ support; `_CheckedDefaultMap` coverage; `report.py` nested scalars; `nmap._escape` newline handling; `nmap._finding_detail`; `nmap` formatters hostile; `vuln.parse_banner`; `nmap.run_nmap` aggregation; `cve._lookup_cve_id` whitespace/case normalization — all clean or already fixed.)
- Prior session's fresh-angle probe (clean, 0 mismatches — do not repeat without NEW evidence): snmp `_encode_oid_value`/`_parse_oid`/`_encode_tlv`/`_parse_tlv`/`_decode_varbind_value`/`_parse_snmp_message` round-trip vs independent oracle (6 new tests).
- This session's fresh-angle probes (clean, 0 mismatches — do not repeat without NEW evidence): tls `_resolve_versions`/`_validate_ciphers` property vs independent oracle (1000 seeded trials).
- Property tests for `tls.enumerate_tls` aggregation invariants (`test_enumerate_tls_aggregation_invariants`, 500 trials) and `snmp._normalize_communities`/`_normalize_valid_communities` (`test_normalize_communities_property_vs_oracle`, `test_normalize_valid_communities_property_vs_oracle`, 500 trials each) already exist and pass — do not re-add.

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100% on a clean run. Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- The two "untouched candidates" previously listed (`tls.enumerate_tls` aggregation invariants; `snmp._normalize_communities`/`_normalize_valid_communities`) have already been addressed with property tests in prior sessions.
- No remaining pure helpers with stdlib/simple oracles are known to be untouched. If future work is needed, pick a bounded, verifiable improvement and reproduce the gap first — do not fabricate work.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate (`python -m coverage erase && python -m coverage run -m pytest -q`, `python -m coverage report`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`). NOTE: `coverage`/`mypy`/`ruff` are invoked via `python -m` (bare `coverage` is not on PATH).

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then rerun the full gate. If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep this behavior.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests); do not change without a reproduced failure.
- `snmp._assess_snmp_version` requires a DOTTED version (regex `\d+(?:\.\d+){1,3}`); the `windows server` threshold is unreachable for bare "Windows Server 2016". Do NOT change the regex without a reproduced functional failure + explicit design.
- Do not commit manually; the workflow controller stages and commits.

(End of file)