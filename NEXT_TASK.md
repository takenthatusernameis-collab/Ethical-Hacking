## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4):
- `python -m pytest -q` -> 49912 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Coverage: TOTAL 100%
- Oracle verification scripts (5): target, whois, dnssec, mac, service — all PASS (per prior session; unchanged)

This session performed honest exploration for a reproducible defect across `audit` (cli.py), `passwords.py`, `hash.py` (run_hash/run_check/PBKDF2/--check), `report.py` (run_report + formatters), and `vuln.py` (version_in_range + match_* + run_vuln + formatters). No user-facing defect reproduces; all are defensively guarded and fully covered by hostile-sweep + branch-gap tests. No source or test changes were made. Working tree clean.

Nothing else to fix — do not fabricate work or repeat verification-only sessions without new evidence.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check), then rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` retain surrounding whitespace in the scheme branch of URL construction; cosmetic only — do not change without a reproduced failure.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design decision.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14 (CPython 3.14 removed the fields from `_test_decode_cert`); do not chase without a bounded stdlib approach.

## Evidence-based lead for a future session (only if a session is needed)
- All four quality gates are green, coverage is 100%, and all four oracle scripts pass. No pending defect.
- Already property-checked / inspected clean (do not repeat): all pure helpers in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize; redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection; whois.extract_referral_server; dnssec helpers; fileio.sanitize_csv_cell; completion.generate_completion_script; dns.run_dns record-type filtering; _assess_web_server_version; validate<->cidr network info; validate<->scanner ports; osdetect._checksum; geo/urlcheck/stale/subdomains review; s3._bucket_name_problem; s3/recon URL builders; ssl/tls cert extraction (3.14-limited); trace._extract_hop_ips duplicate-IP branch; this session's audit/hash/report/vuln exploration.
- Candidate untouched angle (reproduce a wrong output vs a stdlib oracle FIRST): `dns.run_dns` record-type filtering vs a stdlib oracle (requires live network; only revisit with a NEW offline angle). Apply the smallest safe fix, keep coverage 100%, rerun the full gate. If green and nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.

(End of file)
