## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run) at HEAD `6accf9c`:
- `coverage erase && coverage run -m pytest -q` -> 49918 passed, 147 skipped, 0 failed
- `coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session reproduced NO defect (fresh-angle probes all clean) and added durable test hardening (no production change):
- `tests/test_nmap.py::test_run_nmap_aggregation_counts_match_xml_oracle` (+ `_build_random_nmap_xml`, `_oracle_nmap_counts`, `_PROPERTY_SEED = 20261127`): 400 seeded random Nmap XML docs; asserts `run_nmap` counts (`hosts_scanned`, `total_ports_scanned`, `total_open_ports`, `services_detected`) match an independent `xml.etree` oracle and `sum(severity_counts.values()) == finding_count`. Mutation-checked (breaking `total_open_ports += 1` fails the test).

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep this behavior.
- `validate._format_network_info` IPv6 /127 is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests/test_dns_record_type_filtering.py:94); do not change without a reproduced failure.
- Do not commit manually; the workflow controller stages and commits.

## This session (negative result + test hardening)
Fresh-angle probes (ALL clean, 0 mismatches — do not repeat without NEW evidence):
- `nmap._finding_detail` vs hand oracle (882 calls): 0 mismatches/crashes.
- `nmap` markdown/csv/json formatters over hostile finding lists: 0 crashes.
- `vuln.parse_banner` curated + 20,000-iteration consistency fuzz: 0 violations.
- `nmap.run_nmap` aggregation vs independent XML oracle (3,000 docs): 0 mismatches.
Added `test_run_nmap_aggregation_counts_match_xml_oracle` (400 cases) to lock the aggregation-count invariants durably.

## Next task (precise, evidence-based)
No queued assignment. All gates green (49918 passed / 147 skipped / 0 failed, 100% coverage clean, mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Pick ONE remaining untouched pure helper with a stdlib/simple oracle (do NOT repeat angles in the do-not-repeat lists): `cve._lookup_cve_id` product/version normalization (hand oracle), `tls.enumerate_tls` aggregation / `_version_sort_key` ordering under mixed known/unknown, or `snmp._assign_varbind` (transport-coupled, harder to oracle).
- Reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle). If nothing reproduces, record the negative result, preserve the baseline, and hand off again — do not fabricate work.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate (`coverage erase && coverage run -m pytest -q`, `coverage report`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`).

## Constraints (carry forward)
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence). If nothing reproduces, record the negative result and stop.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without a reproduced functional failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep this behavior.
- `validate._format_network_info` IPv6 /127 is INTENTIONAL and tested; do NOT align to cidr's anycast convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests/test_dns_record_type_filtering.py:94); do not change without a reproduced failure.

(End of file)