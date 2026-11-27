# Handoff

## Status
Repository fully green. This session independently re-verified the full gate first-hand (Python 3.14.4, CLEAN coverage run) at HEAD `6accf9c`:
- `coverage erase && coverage run -m pytest -q` -> 49918 passed, 147 skipped, 0 failed (EXIT 0, 143s)
- `coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

## What changed (this session)
No production (`ethscan/`) code changed and NO defect was reproduced. Added ONE durable, deterministic property test (test hardening, matching the repo's radix-session precedent "test hardening, not a known defect"):
- `tests/test_nmap.py::test_run_nmap_aggregation_counts_match_xml_oracle` (+ helpers `_build_random_nmap_xml`, `_oracle_nmap_counts`, `_PROPERTY_SEED = 20261127`). It generates 400 seeded random-but-well-formed Nmap XML documents and asserts `run_nmap`'s user-visible aggregation counts (`hosts_scanned`, `total_ports_scanned`, `total_open_ports`, `services_detected`) match an INDEPENDENT `xml.etree.ElementTree` count, plus `sum(severity_counts.values()) == finding_count`. This locks the report-count invariants that were previously only checked on one fixed XML sample.

## What was actually verified (first-hand this session)
- Fresh-angle probes (all clean, 0 mismatches — do not repeat without NEW evidence):
  - `nmap._finding_detail` vs a hand-derived oracle over kind x field x value matrix (882 calls): 0 mismatches, 0 crashes.
  - `nmap` markdown/csv/json formatters over hostile finding lists (non-dict entries, wrong types, newline/pipe fields): 0 crashes; table integrity preserved.
  - `vuln.parse_banner` curated expectations + 20,000-iteration consistency fuzz (version must be a substring of the banner, product in the known set): 0 violations.
  - `nmap.run_nmap` aggregation vs independent XML-element oracle over 3,000 random documents: 0 mismatches.
- New property test: 400 cases, 0 mismatches. Mutation-checked: temporarily changing `total_open_ports += 1` to `+= 2` in `ethscan/nmap.py` made the new test FAIL (`assert 2 == 1`); source reverted, only `tests/test_nmap.py` remains modified.
- Full gate green after the change (numbers above).

## What remains unresolved
- None.

## Approaches already tried / ruled out (do not repeat)
- Carry forward all prior handoff items (CSV formula injection; parser/formatter/assessor hostile sweeps; CLI target/option sweeps; radix math + property tests; target.py parsers property-checked; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize; dnssec; geo/urlcheck/stale/subdomains; validate<->cidr; validate<->scanner ports; osdetect checksum; cve version-range; mac OUI; empty-host normalization; findings/security_flags hardening; README drift guards (command + option level); audit/hash/report/vuln; headers/web wrong-output probe; version/resolve/subtake/ping/netbios/ntp/wifi/mongodb+ldap/memcached/mssql/smb/smtp/ssh/ftp/dnsbrute/fuzz/brute/service; mac/osdetect/hash/version_tuple oracles; 3000-trial radix merge; `_assess_web_server_version`, `_parse_url`, `detect_shell`, config coercion/validation, netbios encode/decode; parser STRING fuzz; load_json bracket-in-string; version formatter hostile fields; radix `_common_prefix_of_pair`; `whois.parse_whois` registrar; `fileio.sanitize_csv_cell`; `s3._normalize_target` hostless authority; `trace._extract_hop_ips` dedup; `click` 8.2+ support; `click.__version__` migration; `_CheckedDefaultMap` coverage; `report.py` nested scalars; `nmap._escape` newline handling) — all clean or already fixed.
- This session's fresh-angle probes (ALL clean, 0 mismatches — do not repeat without NEW evidence): `nmap._finding_detail` (all kinds/fields), `nmap` formatters hostile, `vuln.parse_banner` (curated + 20k fuzz), `nmap.run_nmap` aggregation (3000 docs vs XML oracle).

## Next task (precise, evidence-based)
- No queued assignment; all gates green, coverage 100% on a clean run. Do NOT repeat verification-only sessions without NEW evidence or a NEW angle. If future work is needed, pick a fresh angle NOT in the lists above, reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle), apply the smallest safe fix, add/extend a test to keep coverage 100%, then rerun the full gate. If green and nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.
- Untouched fresh angles still available (not yet property-checked): `cve._lookup_cve_id` product/version normalization (pure-ish, hand oracle); `tls.enumerate_tls` aggregation + `_version_sort_key` ordering under mixed known/unknown versions; `snmp._assign_varbind`/`_probe_community`/`_assess_snmp_version` (transport-coupled, harder to oracle); `ssl._get_chain` (transport). Prefer pure helpers with a stdlib/simple oracle.

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then rerun the full gate. If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep this behavior.
- `validate._format_network_info` IPv6 /127 (usable_host_count=2, first_host=network[0]) is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types (incl. invalid/lowercase) by design and is asserted by tests; do not "fix" without a reproduced failure.
- Do not commit manually; the workflow controller stages and commits.

(End of file)