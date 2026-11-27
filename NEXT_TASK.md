## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4):
- `python -m pytest -q` -> 49912 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Coverage: TOTAL 100%
- Oracle verification scripts (5): target, whois, dnssec, mac, service — all PASS (re-run this session)

This session performed NEW differential probes (not in prior ruled-out lists) with running stdlib
evidence, all 0 mismatches: `mac._is_mac_address`/`_strip_mac_port` (9 tricky vectors),
`osdetect._checksum` (independent ones-complement oracle), `hash._compute_hash` (vs hashlib),
`vuln._version_tuple` (manual digit-run oracle), and `radix._merge_networks` vs
`ipaddress.collapse_addresses` over 3000 RANDOMISED IPv4/IPv6 vectors.

Additional fresh-angle probes this session (all 0 mismatches):
- `ethscan.web._assess_web_server_version` vs an independent hand-derived oracle over 28
  server-header shapes (Apache/nginx/lighttpd/IIS/Microsoft-IIS, case variants, prefixes/suffixes,
  malformed versions) — correct.
- `ethscan.web._parse_url` vs `urllib.parse.urlparse` oracle over 16 target shapes
  (scheme/default-port/bare/IPv6 brackets/whitespace/uppercase) — correct.
- `ethscan.completion.detect_shell` vs a hand-derived SHELL-basename oracle over 17 SHELL values
  (valid shells, unknown shells, empty, None, whitespace, case variants, Windows paths) — correct.
- `ethscan.config` coercion/validation (`_normalize_format_key`, `_parse_set_value`,
  `validate_config`, `build_default_map`) vs hand-derived oracles over 8 normalize cases,
  10 parse cases, 8 validate cases — correct.
- `ethscan.netbios._encode_name_chars` / `_decode_name_chars` vs an independent RFC 1001
  first-pair/hex-nibble oracle over 5000 randomised names: encode matches 100%; ASCII-only names
  round-trip perfectly (0 failures); non-ASCII names replace with `?` via `encode("ascii","replace")`
  which is intentional, not a defect.

No source/test changes; working tree clean except this handoff.

Nothing else to fix — do not fabricate work or repeat verification-only sessions without new evidence.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then
  rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate
  work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it
  without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change
  without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` retain surrounding whitespace in the scheme branch of URL
  construction; cosmetic only — do not change without a reproduced failure.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL
  and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14 (CPython 3.14 removed the fields from
  `_test_decode_cert`); do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change
  without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by
  tests/test_dns_record_type_filtering.py:94); do not change without a reproduced failure.

## Evidence-based lead for a future session (only if a session is needed)
- All four quality gates are green, coverage is 100%, and all five oracle scripts pass. No pending defect.
- Already property-checked / inspected clean (do not repeat): all pure helpers in
  ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math (incl. 3000 random merge trials this
  session); target.py parsers; hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize;
  redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection; whois.extract_referral_server;
  dnssec helpers; fileio.sanitize_csv_cell; completion.generate_completion_script; dns.run_dns
  record-type filtering; _assess_web_server_version; validate<->cidr network info; validate<->scanner
  ports; osdetect._checksum; geo/urlcheck/stale/subdomains review; s3._bucket_name_problem; s3/recon URL
  builders; ssl/tls cert extraction (3.14-limited); trace._extract_hop_ips duplicate-IP branch;
  headers/web wrong-output probe; audit/hash/report/vuln exploration; version/resolve/subtake/ping/
  netbios/ntp/wifi/mongodb + ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service
  wrong-output probe; THIS SESSION: mac/osdetect/hash/version_tuple differential oracles + 3000-trial
  randomized radix merge + recon/dns-filtering/urlcheck/version_range static review;
  THIS SESSION (additional): _assess_web_server_version, _parse_url, detect_shell, config
  coercion/validation, netbios encode/decode — all clean vs independent oracles.
- No remaining un-probed deterministic lead in the handoff lists. If a session is needed, the agent
  should invent a genuinely new angle (e.g. a module/helper not yet property-checked for wrong output)
  and reproduce a defect before changing anything.

(End of file)