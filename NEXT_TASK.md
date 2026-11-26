## Next task
No queued assignment. Repository fully green and re-verified first-hand this session
(2026-11-26, Python 3.14.4):
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 49903 passed, 147 skipped,
  0 failed; TOTAL 100% (16294 stmts, 6174 branches, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session reproduced and fixed ONE library-boundary wrong-output defect:
`s3._normalize_target` used a `parsed.netloc` fallback, so a hostless authority with a non-empty
netloc (`https://:8080`, `https://user@:8080`) returned a bogus "domain" (`:8080` /
`user@:8080`, leaking userinfo) instead of raising `TargetSpecError`. Fixed to use only
`parsed.hostname` (matches `normalize_host`); added
`tests/test_s3.py::test_normalize_target_rejects_hostless_authority`. The CLI already masks this
via `_validate_enum_target`, so it is a library-API fix, not user-facing via the CLI today.

Fresh-angle probes this session found NO other reproducible defect:
1. `s3._bucket_name_problem` vs a reference AWS rule impl (20,016 names) -> 0 mismatches.
2. `whois.extract_referral_server` vs a hand oracle (5,010 snippets) -> 0 mismatches.
3. ssl/tls cert extraction: Python 3.14 `_test_decode_cert` no longer returns
   `publicKeyInfo`/`signatureAlgorithm`, so ssl `key_size`/`signature_algorithm` are always None
   on 3.14 for real certs — a CPython limitation, not a bounded ethscan fix (documented).
Nothing else to fix — do not fabricate work or repeat verification-only sessions without new
evidence.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check), then rerun the full
  gate. If nothing reproduces, record the negative result and stop — do not fabricate work or
  repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not
  "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not
  change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` retain surrounding whitespace in the scheme branch
  of URL construction; cosmetic only — do not change without a reproduced failure.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is
  INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure
  + explicit design decision.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14 (CPython 3.14 removed the fields
  from `_test_decode_cert`); do not chase without a bounded stdlib approach.

## Evidence-based lead for a future session (only if a session is needed)
- All five quality gates are green, coverage is 100%, and all four oracle scripts pass. No pending
  defect.
- Already property-checked / inspected clean (do not repeat): all pure helpers in
  ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; radix math; target.py parsers; hash/passwords/
  jwt/scanner/cidr; fileio/completion/whois/dns normalize; redis/mysql/snmp/cert/nmap/config/
  report/vuln parser inspection; whois.extract_referral_server; dnssec helpers;
  fileio.sanitize_csv_cell; completion.generate_completion_script; dns.run_dns record-type
  filtering; _assess_web_server_version; validate<->cidr network info; validate<->scanner ports;
  osdetect._checksum; geo/urlcheck/stale/subdomains review; s3._bucket_name_problem; s3/recon URL
  builders; ssl/tls cert extraction (3.14-limited).
- Candidate untouched angles (reproduce a wrong output vs a stdlib oracle FIRST):
  `completion.generate_completion_script` complete-var derivation; `headers.run_headers` URL
  construction; `dns.run_dns` record-type filtering. Apply the smallest safe fix, keep coverage
  100%, rerun the full gate. If green and nothing reproduces, record the negative result,
  preserve the baseline, and hand off again — do not fabricate work.

(End of file)