# Handoff

## Status
Repository fully green. This session independently re-verified the full gate first-hand (Python 3.14.4):
- `coverage erase && coverage run -m pytest -q` -> 49917 passed, 147 skipped, 0 failed (EXIT 0, 143s)
- `coverage report` -> TOTAL 100% (16299 stmts, 0 missing) on a CLEAN run
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

## What changed (this session)
Fixed a real defect in `ethscan/nmap.py:_escape`: the function only escaped pipe characters (`|`) but not newlines (`\n`), causing Markdown table rows and list items to break when service product/version/other fields contained newlines. The fix adds newline escaping (replacing `\n` with space), matching the pattern used in other modules' `_markdown_escape` helpers (e.g., `dnsbrute`, `geo`). Added two tests: `test_escape_newlines` (unit) and `test_format_nmap_report_markdown_newlines_in_fields` (end-to-end Markdown table integrity).

## What was actually verified (first-hand this session)
- Reproduced the defect: `format_nmap_report_markdown` with newlines in `product` field produced a broken table (3 table lines became 4+ due to embedded newlines) and malformed "Details" list items.
- Fix verified: after change, table structure is preserved (exactly 3 table lines: header, separator, data), newlines replaced with spaces in both table cells and finding details.
- Full gate green: 49917 passed, 147 skipped, 0 failed; mypy clean (274 files); ruff clean; check_readme 54/54; coverage 100% (16299 stmts, 6180 branches, 0 missing).

## What remains unresolved
- None.

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile sweeps; CLI target/option sweeps; radix math; target.py parsers; hash/passwords/jwt/scanner/cidr; fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr; validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization; findings/security_flags hardening; README drift guard; audit/hash/report/vuln; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/wifi/mongodb+ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service; mac/osdetect/hash/version_tuple oracles; 3000-trial radix merge; `_assess_web_server_version`, `_parse_url`, `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`; `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless authority; `trace._extract_hop_ips` dedup; `click` 8.2+ support; `click.__version__` migration; `_CheckedDefaultMap` coverage; `report.py` nested scalars) — all clean or already fixed.
- This session's fresh-angle probes (ALL clean, 0 mismatches — do not repeat without NEW evidence): `snmp` BER encode/decode round-trip + full-message round-trip + malformed-truncation + 20k random-byte fuzz (ValueError-only contract); `cve._extract_cve_summary` vs from-spec oracle; `tls._resolve_version` alias/passthrough/unknown; `tls._version_name`/`_version_sort_key`/`_cipher_sort_key`/`_truncate`; `nmap._parse_port` boundaries + `_parse_host`/`parse_nmap_xml`; read-clean `ssl._parse_cert`/`_rdn_to_str`/`_estimate_key_size`, `geo` CSV 17-col alignment + `_normalize_hops`/`_normalize_geo`, `recon._normalize_domain`, `snmp._normalize_target`, `cve._severity_rank`.
- `nmap._escape` newline handling: FIXED this session (was listed as "untouched fresh angle" in prior handoff).

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100% on a clean run. Do NOT repeat verification-only sessions without NEW evidence or a NEW angle. If future work is needed, pick a fresh angle NOT in the lists above, reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle), apply the smallest safe fix, add/extend a test to keep coverage 100%, then rerun the full gate. If green and nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.
- Untouched fresh angles still available (not yet property-checked): `snmp._assign_varbind`/`_probe_community`/`_assess_snmp_version` (transport-coupled, harder to oracle); `tls.enumerate_tls` aggregation/`_version_sort_key` ordering under mixed known/unknown; `cve._lookup_cve_id` product/version normalization; `nmap._finding_detail` (signature-matching edge cases); `ssl._get_chain` (transport). Prefer pure helpers with a stdlib oracle.

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then rerun the full gate. If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` now strip the target before building the transport URL (fixed this session); keep this behavior.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types (incl. invalid/lowercase) by design and is asserted by tests; do not "fix" without a reproduced failure.

(End of file)