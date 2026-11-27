## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4):
- `python -m pytest -q` -> 49912 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Coverage: TOTAL 100%
- Oracle verification scripts (5): target, whois, dnssec, mac, service — all PASS (unchanged)

This session performed an honest fresh-angle wrong-output probe (NOT in prior ruled-out lists) of the
pure/deterministic helpers in version, resolve, subtake, ping, netbios, ntp, wifi, mongodb (personal
read) plus a static audit of ldap, memcached, mssql, smb, smtp, ssh, ftp, dnsbrute, fuzz, brute,
service (explore subagent). A running oracle script (stdlib comparisons) reported 0 mismatches:
ssh banner/version (8.3p1->8.3 flagged; 8.4/9.3p1/10.0 not), service banner parse, netbios RFC1001
encode/decode roundtrip, ntp timestamp+ref_id, dnsbrute AXFR query (TCP prefix+header+qname), ldap
BER length roundtrip. The mongodb line-191 off-by-one is real but masked (later loop overwrites with
the correct value) -> not a reproducible defect. No source or test changes were made. Working tree clean.

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

## Evidence-based lead for a future session (only if a session is needed)
- All four quality gates are green, coverage is 100%, and all five oracle scripts pass. No pending defect.
- Already property-checked / inspected clean (do not repeat): all pure helpers in
  ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math; target.py parsers;
  hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize; redis/mysql/snmp/cert/nmap/
  config/report/vuln parser inspection; whois.extract_referral_server; dnssec helpers;
  fileio.sanitize_csv_cell; completion.generate_completion_script; dns.run_dns record-type filtering;
  _assess_web_server_version; validate<->cidr network info; validate<->scanner ports; osdetect._checksum;
  geo/urlcheck/stale/subdomains review; s3._bucket_name_problem; s3/recon URL builders; ssl/tls cert
  extraction (3.14-limited); trace._extract_hop_ips duplicate-IP branch; headers/web wrong-output probe;
  audit/hash/report/vuln exploration; THIS SESSION: version/resolve/subtake/ping/netbios/ntp/wifi/
  mongodb + ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service wrong-output probe.
- Candidate untouched angle (reproduce a wrong output vs a stdlib oracle FIRST): `dns.run_dns`
  record-type filtering vs a stdlib oracle (requires live network; only revisit with a NEW offline
  angle). Apply the smallest safe fix, keep coverage 100%, rerun the full gate. If green and nothing
  reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate.

(End of file)