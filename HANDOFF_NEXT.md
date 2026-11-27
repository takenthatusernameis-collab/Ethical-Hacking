# Handoff

## Status
Repository fully green. Full gate re-verified first-hand this session at HEAD `ac582cd` (Python 3.14.4, CLEAN coverage run):
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49925 passed, 147 skipped, 0 failed (EXIT 0, 144s)
- `python -m coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

## What changed (this session)
No production (`ethscan/`) code changed and NO defect was reproduced. Added durable, deterministic test hardening (matching the repo's established "test hardening, not a known defect" precedent):
- `tests/test_snmp.py`: added `_SNMP_MIN_MAJOR` to the import list and THREE tests locking `_assess_snmp_version`'s full contract against an independent oracle:
  - `test_assess_snmp_version_threshold_matrix`: 15-case product/version matrix (Linux, Cisco IOS / XE / XR, IOS XE, Windows, FreeBSD, JunOS, Net-SNMP, OpenBSD, HP-UX, VMware ESXi, plus case-insensitivity) asserting the `SNMP system version: <ver>` finding is exact and the `Old SNMP system version` finding appears iff `major < _SNMP_MIN_MAJOR[key]`.
  - `test_assess_snmp_version_requires_dotted_version`: bare (non-dotted) versions ("Windows Server 2016", "Android 9", "Linux 5") yield no findings (the version regex requires `\d+(?:\.\d+){1,3}`).
  - `test_assess_snmp_version_threshold_boundaries`: `major == threshold` is NOT old; `major == threshold-1` IS old (Linux/FreeBSD/OpenBSD).
- These fill a real gap: prior tests only covered Linux/Cisco/FreeBSD; the rest of the threshold table + dotted-version contract + boundaries were untested.

## What was actually verified (first-hand this session)
- Fresh-angle probe of `snmp._assess_snmp_version` vs an independent oracle (product x version matrix + threshold boundaries + case-insensitivity + empty/None): 0 mismatches. (Initial 2 "mismatches" were MY oracle bug — I wrongly expected non-dotted "Windows Server 2016"/"Windows 7" to match; the regex intentionally requires a dotted version. Corrected oracle: 0 mismatches.)
- New tests: 9 passed in the focused `-k assess_snmp_version` run; full gate green after the change (numbers above).

## What remains unresolved
- None blocking. One documented-but-NOT-changed observation (see constraints): `_SNMP_MIN_MAJOR["windows server"] = 2016` is effectively unreachable for the canonical "Windows Server 2016" sys_descr because the version regex requires a dotted version. This is a design limitation, not a reproduced functional failure; do NOT change the regex without a reproduced failure + explicit design.

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile sweeps; CLI target/option sweeps; radix math + property tests; target.py parsers; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr; validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization; findings/security_flags hardening; README drift guards; audit/hash/report/vuln; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/wifi/mongodb+ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service; mac/osdetect/hash/version_tuple oracles; 3000-trial radix merge; `_assess_web_server_version`, `_parse_url`, `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`; `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless authority; `trace._extract_hop_ips` dedup; click 8.2+ support; `_CheckedDefaultMap` coverage; `report.py` nested scalars; `nmap._escape` newline handling; `nmap._finding_detail`; `nmap` formatters hostile; `vuln.parse_banner`; `nmap.run_nmap` aggregation; `cve._lookup_cve_id` whitespace/case normalization (fixed in ac582cd)) — all clean or already fixed.
- This session's fresh-angle probe (clean, 0 mismatches — do not repeat without NEW evidence): `snmp._assess_snmp_version` full threshold matrix + boundaries + dotted-version contract.

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100% on a clean run. Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Pick ONE remaining untouched pure helper with a stdlib/simple oracle (do NOT repeat angles in the do-not-repeat lists). Untouched candidates still available:
  - `tls.enumerate_tls` aggregation invariants (`versions_tested`/`supported_version_count` vs list lengths; `supported_versions` subset/order) under randomized monkeypatched probes — has unit tests but no property test.
  - `tls._resolve_versions` / `_validate_ciphers` normalization over randomized alias/cipher inputs vs an independent oracle.
  - `snmp._parse_oid` / `_parse_tlv` / `_decode_varbind_value` round-trip vs an independent encoder oracle (pure, byte-level).
  - `snmp._normalize_communities` / `_normalize_valid_communities` coercion vs a hand oracle.
- Reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle). If nothing reproduces, record the negative result, preserve the baseline, optionally add ONE tight property test that locks a genuinely-new invariant, and hand off again — do not fabricate work.
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