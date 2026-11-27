# Handoff

## Status
Repository fully green. This session independently re-verified the full gate first-hand (Python 3.14.4):
- `python -m pytest -q` -> 49912 passed, 147 skipped, 0 failed (EXIT 0, 187s)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0
- Coverage: TOTAL 100% (unchanged; enforced by pyproject fail_under=100)
- Oracle scripts (5): target, whois, dnssec, mac, service — all "ALL VERIFICATIONS PASSED", exit 0

## What changed (this session)
No source or test changes. Working tree clean (git status: nothing to commit, clean).
Only this handoff file and NEXT_TASK.md were updated to record the new negative result.

## What was actually verified (first-hand this session — NEW evidence)
- Full gate green (pytest/mypy/ruff/check_readme) reproduced this session — exact prior numbers.
- All five oracle verification scripts re-run and PASS.
- Fresh differential probes NOT in prior ruled-out lists, with running stdlib-oracle evidence (0 mismatches):
  - `mac._is_mac_address` / `_strip_mac_port` over 9 tricky vectors — correct.
  - `osdetect._checksum` vs an independent ones-complement oracle — correct.
  - `hash._compute_hash` vs `hashlib` — correct.
  - `vuln._version_tuple` vs a manual digit-run oracle — correct.
  - `radix._merge_networks` vs `ipaddress.collapse_addresses` over 3000 RANDOMIZED IPv4/IPv6 vectors — 0 mismatches.
- Additional fresh-angle probes this session (all 0 mismatches, running evidence):
  - `ethscan.web._assess_web_server_version` vs an independent hand-derived oracle over 28 server-header shapes (Apache/nginx/lighttpd/IIS/Microsoft-IIS, case variants, prefixes/suffixes, malformed versions) — correct.
  - `ethscan.web._parse_url` vs `urllib.parse.urlparse` oracle over 16 target shapes (scheme/default-port/bare/IPv6 brackets/whitespace/uppercase) — correct.
  - `ethscan.completion.detect_shell` vs a hand-derived SHELL-basename oracle over 17 SHELL values (valid shells, unknown shells, empty, None, whitespace, case variants, Windows paths) — correct.
  - `ethscan.config` coercion/validation (`_normalize_format_key`, `_parse_set_value`, `validate_config`, `build_default_map`) vs hand-derived oracles over 8 normalize cases, 10 parse cases, 8 validate cases — correct.
  - `ethscan.netbios._encode_name_chars` / `_decode_name_chars` vs an independent RFC 1001 first-pair/hex-nibble oracle over 5000 randomised names: encode matches 100%; ASCII-only names round-trip perfectly (0 failures); non-ASCII names replace with `?` via `encode("ascii","replace")` which is intentional, not a defect.

## What remains unresolved
- No reproducible wrong-output defect found in any explored module; repository complete and green.
- ssl `key_size`/`signature_algorithm` reporting is inert on Python 3.14 (documented limitation).

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile
  sweeps; CLI target/option sweeps; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr;
  fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr;
  validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization;
  findings/security_flags CSV/Markdown hardening; README command-presence drift guard; audit/hash/
  report/vuln exploration; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/
  wifi/mongodb + ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service wrong-output probe).
- THIS SESSION: mac helpers / osdetect checksum / hash / version_tuple differential oracles;
  3000-trial randomized radix merge vs collapse_addresses; recon/dns-filtering/urlcheck/version_range
  static review — all clean.
- THIS SESSION (additional): `_assess_web_server_version`, `_parse_url`, `detect_shell`,
  config coercion/validation, netbios encode/decode — all clean vs independent oracles.

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100%.
- Do NOT repeat verification-only sessions without NEW evidence or a NEW angle. If future work is
  needed, pick a fresh angle NOT in the lists above, reproduce a concrete defect FIRST (focused
  failing check with running evidence vs a stdlib oracle), apply the smallest safe fix, add/extend a
  test to keep coverage 100%, then rerun the full gate. If green and nothing reproduces, record the
  negative result, preserve the baseline, and hand off again — do not fabricate work.
- No remaining un-probed deterministic lead in the handoff lists. If a session is needed, the agent
  should invent a genuinely new angle (e.g. a module/helper not yet property-checked for wrong output)
  and reproduce a defect before changing anything.

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
- `dns.run_dns` `record_types_queried` reports the RAW requested types (incl. invalid/lowercase) by
  design and is asserted by tests; do not "fix" without a reproduced failure.

(End of file)