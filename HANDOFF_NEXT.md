# Handoff

## Status
Repository fully green. This session independently re-verified the full gate first-hand (Python 3.14.4):
- `python -m pytest -q` -> 49912 passed, 147 skipped, 0 failed (EXIT 0)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Coverage: TOTAL 100% (unchanged; enforced by pyproject fail_under=100)

## What changed (this session)
No source or test changes. Working tree clean (git status: nothing to commit, clean).
Only this handoff file and NEXT_TASK.md were updated to record the new negative result.

## What was actually verified (first-hand this session)
- Full gate green (pytest/mypy/ruff/check_readme) — exact prior numbers reproduced.
- Fresh-angle wrong-output probe (NOT in prior ruled-out lists) of the pure/deterministic
  helpers in: version, resolve, subtake, ping, netbios, ntp, wifi, mongodb (personal read),
  plus a static audit of ldap, memcached, mongodb, mssql, smb, smtp, ssh, ftp, dnsbrute,
  fuzz, brute, service (via explore subagent).
- Running oracle evidence (script compared outputs to stdlib oracles; 0 mismatches):
  - ssh `_parse_ssh_banner`/`_assess_ssh_banner`: `8.3p1`->8.3 flagged, `8.4`/`9.3p1`/`10.0`
    NOT flagged (numeric tuple compare, not string compare) — correct.
  - service `_parse_banner_service`/`_parse_banner_version`: first-signature-wins + version
    extraction — correct.
  - netbios `_encode_name_chars`/`_decode_name_chars`: RFC 1001 roundtrip (TEST/WORKSTATION/A)
    + known first-pair vector — correct.
  - ntp `_parse_time_response`: `ntp_to_unix` (epoch 2208988800) + stratum-1 ref_id IPv4 — correct.
  - dnsbrute `build_axfr_query`: 2-byte TCP length prefix + header (id/qd=1/an=0) + qname — correct.
  - ldap `_ber_length`/`_read_length`: roundtrip 0/1/127/128/256/65535/65536 — correct.
- mongodb `_parse_buildinfo_response` off-by-one at line 191 (`version_pos + 8` for a 9-byte
  `\x02version\x00`) is REAL but MASKED: the later loop (lines 204-215) uses the correct
  `len(field_search)` and always overwrites `result['version']` with the correct value whenever
  the first block could set it. Net output is always correct -> NOT a reproducible wrong-output
  defect. Do not "fix" without a reproduced functional failure (repo constraint).

## What remains unresolved
- No reproducible wrong-output defect remains in the explored modules; repository complete and green.
- ssl `key_size`/`signature_algorithm` reporting is inert on Python 3.14 (documented limitation).

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile
  sweeps; CLI target/option sweeps; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr;
  fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr;
  validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization;
  findings/security_flags CSV/Markdown hardening; README command-presence drift guard; audit/hash/
  report/vuln exploration; headers/web wrong-output probe).
- This session: version/resolve/subtake/ping/netbios/ntp/wifi/mongodb + ldap/memcached/mssql/smb/
  smtp/ssh/ftp/dnsbrute/fuzz/brute/service wrong-output probe (all green, running evidence above).

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100%.
- If future work is needed, pick a fresh angle NOT in the lists above, reproduce a concrete defect
  FIRST (focused failing check with running evidence vs a stdlib oracle), apply the smallest safe
  fix, add/extend a test to keep coverage 100%, then rerun the full gate. If green and nothing
  reproduces, record the negative result, preserve the baseline, and hand off again — do not
  fabricate work or repeat verification-only sessions without NEW evidence.

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence),
  then rerun the full gate. If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change
  without a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` retain surrounding whitespace in the scheme branch of
  URL construction; cosmetic only — do not change without a reproduced failure.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is
  INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded
  stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change
  without a reproduced functional failure.

(End of file)