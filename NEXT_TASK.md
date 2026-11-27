## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `coverage erase && coverage run -m pytest -q` -> 49917 passed, 147 skipped, 0 failed
- `coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session FIXED a real defect (not a negative result):
- `ethscan/nmap.py:_escape` did not escape newlines, breaking Markdown table structure and list items when service fields (product, version, etc.) contained newlines. Fixed by adding `.replace("\n", " ")` to the escape function, matching the pattern used in other modules' `_markdown_escape` helpers (`dnsbrute`, `geo`, etc.). Added `test_escape_newlines` and `test_format_nmap_report_markdown_newlines_in_fields` in `tests/test_nmap.py`.

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

## This session (defect fixed)
Fixed `nmap._escape` newline handling (was listed as "untouched fresh angle" in prior handoff):
- Reproduced: Markdown table rows broken when `product`/`version` fields contained `\n` (table line count > 3, malformed "Details" lines).
- Fix: `_escape` now replaces `\n` with space in addition to escaping `|`.
- Verified: table structure preserved (exactly 3 lines), newlines sanitized in both table cells and finding details.
- Full gate: 49917 passed, 147 skipped, 0 failed; mypy/ruff/check_readme clean; coverage 100%.

## Next task (precise, evidence-based)
No queued assignment. All gates green (49917 passed / 147 skipped / 0 failed, 100% coverage clean, mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Pick ONE remaining untouched pure helper with a stdlib/simple oracle (do NOT repeat angles already in the do-not-repeat lists): `nmap._finding_detail` signature-matching edge cases (ethscan/nmap.py), `snmp._assign_varbind` (ethscan/snmp.py), or `ssl._get_chain` (transport-coupled, harder to oracle).
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