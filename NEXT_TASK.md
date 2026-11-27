## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `coverage erase && coverage run -m pytest -q` -> 49915 passed, 147 skipped, 0 failed
- `coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session produced a NEGATIVE result (no source/test changes; working tree clean; baseline preserved). Fresh-angle wrong-output hunt, all 0 mismatches vs independent oracles / self-consistency:
- `snmp` BER codec: OID value + full-message round-trip (multi-byte first subidentifier 2.999->1079, all value types incl. UTF-8), INTEGER round-trip, base128 round-trip, TLV length round-trip; malformed truncation + 20,000 random-byte inputs raise ONLY `ValueError`.
- `cve._extract_cve_summary` vs from-spec oracle (hostile structured matrix).
- `tls._resolve_version` alias/passthrough/unknown; `_version_name`/`_version_sort_key`/`_cipher_sort_key`/`_truncate` read-clean.
- `nmap._parse_port` boundaries + `_parse_host`/`parse_nmap_xml` read-clean.
- Read-clean: `ssl._parse_cert`/`_rdn_to_str`/`_estimate_key_size`, `geo` CSV 17-col alignment + normalizers, `recon._normalize_domain`, `snmp._normalize_target`, `cve._severity_rank`.

Nothing else to fix — do not fabricate work or repeat verification-only sessions without new evidence.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL (fixed in commit 9389d03); keep this behavior.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14 (CPython 3.14 removed the fields from `_test_decode_cert`); do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests/test_dns_record_type_filtering.py:94); do not change without a reproduced failure.

## Evidence-based lead for a future session (only if a session is needed)
- All four quality gates are green, coverage is 100% on a clean run, and no pending defect. Already property-checked / inspected clean (do not repeat): all pure helpers in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize; redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection; whois.extract_referral_server; dnssec helpers; fileio.sanitize_csv_cell; completion.generate_completion_script; dns.run_dns record-type filtering; _assess_web_server_version; validate<->cidr network info; validate<->scanner ports; osdetect._checksum; geo/urlcheck/stale/subdomains review; s3._bucket_name_problem; s3/recon URL builders; ssl/tls cert extraction (3.14-limited); trace._extract_hop_ips duplicate-IP branch; headers/web wrong-output probe; audit/hash/report/vuln exploration; version/resolve/subtake/ping/netbios/ntp/wifi/mongodb + ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service wrong-output probe; mac/osdetect/hash/version_tuple differential oracles; 3000-trial randomized radix merge; `_assess_web_server_version`, `_parse_url`, `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`; `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless authority; `trace._extract_hop_ips` dedup; **NEW this session (clean):** snmp BER encode/decode round-trip + malformed/random fuzz, cve._extract_cve_summary oracle, tls._resolve_version alias, nmap._parse_port boundaries.
- Untouched fresh angles still available: `snmp._assign_varbind`/`_probe_community`/`_assess_snmp_version` (transport-coupled); `tls.enumerate_tls` aggregation/ordering; `cve._lookup_cve_id` product/version normalization; `nmap._finding_detail`/`_escape`; `ssl._get_chain`. Prefer pure helpers with a stdlib oracle.
- If a session is needed, the agent should invent a genuinely new angle (a module/helper not yet property-checked for wrong output) and reproduce a defect before changing anything.
- `oracle`/`postgresql` empty-target handling and `ethscan/cli.py` unreachable guard remain intentionally out of scope. Do not modify `.github/workflows/**`.

(End of file)
