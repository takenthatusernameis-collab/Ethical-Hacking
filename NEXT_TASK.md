## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (2026-11-26, Python 3.14.4):
- `python -m pytest -q` → 49902 passed, 147 skipped, 0 failed
- `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed
- `python3 check_readme.py` → 54 CLI commands, 0 drift both directions, exit 0
- `python -m mypy ethscan/ tests/` → Success: no issues found in 274 source files
- (coverage gate last recorded TOTAL 100%; not re-run since no source/test changed)

Four fresh-angle wrong-output probes this session found NO reproducible defect:
1. validate↔cidr `_format_network_info` cross-oracle (only diffs are intended: `addresses` field, and IPv6 /127 usable_host_count — explicitly tested at tests/test_validate.py:398,962).
2. validate↔scanner port-spec validity/expansion over 9,779 specs → 0 mismatches.
3. osdetect `_checksum` vs reference over 200k inputs + 50k SYN packets → 0 mismatches.
4. geo/urlcheck/stale/subdomains source review → guarded/network-bound, no gap.
Nothing to fix — do not fabricate work or repeat verification-only sessions without new evidence.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check), then rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` retain surrounding whitespace in the scheme branch of URL construction; cosmetic only — do not change without a reproduced functional failure.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced functional failure + explicit design decision.

## Evidence-based lead for a future session (only if a session is needed)
- All five quality gates are green, coverage is 100% (last recorded), and all four oracle scripts pass. No pending defect.
- Already property-checked / inspected clean (do not repeat): all pure helpers in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize; redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection; whois.extract_referral_server; dnssec helpers; fileio.sanitize_csv_cell numeric-vs-formula; completion.generate_completion_script complete-var; dns.run_dns record-type filtering; _assess_web_server_version; hash/passwords/jwt/scanner/cidr wrong-output fuzz; validate↔cidr network info; validate↔scanner ports; osdetect._checksum; geo/urlcheck/stale/subdomains review.
- Candidate untouched angles (reproduce a wrong output vs a stdlib oracle FIRST): `cve.py` version-range comparison; `s3.py`/`recon.py` URL/endpoint builders vs `urllib.parse`; `mac.py` OUI formatting edges; `tls.py`/`ssl.py` cert field extraction with a generated self-signed cert. Apply the smallest safe fix, keep coverage 100%, rerun the full gate. If green and nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.

(End of file)