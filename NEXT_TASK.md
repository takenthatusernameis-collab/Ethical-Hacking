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

## This session (negative result — no changes made)
Baseline preserved; working tree clean. Property-checked one NEW untouched angle against the documented contract:
- `cve._lookup_cve_id` / `ethscan/vuln.py:version_in_range` (vuln.py:582): inclusive/exclusive min/max, zero-padding (`1.3`==`1.3.0`), numeric-not-lexicographic (`1.10`>`1.2`), invalid/empty version -> False. 0 mismatches across all boundary cases. No defect reproduced; no fix applied.

## Next task (precise, evidence-based)
No queued assignment. All gates green (49915 passed / 147 skipped / 0 failed, 100% coverage clean, mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Pick ONE remaining untouched pure helper with a stdlib/simple oracle (do NOT repeat angles already in the do-not-repeat lists): `nmap._finding_detail`/`_escape` signature-matching (ethscan/nmap.py), `snmp._assign_varbind` (ethscan/snmp.py), or `ssl._get_chain` (transport-coupled, harder to oracle).
- Reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle). If nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate (`coverage erase && coverage run -m pytest -q`, `coverage report`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`).

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence). If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL (commit 9389d03); keep this behavior.
- `validate._format_network_info` IPv6 /127 is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests/test_dns_record_type_filtering.py:94); do not change without a reproduced failure.

(End of file)

(End of file)
