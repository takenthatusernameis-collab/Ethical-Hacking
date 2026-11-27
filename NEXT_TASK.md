## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run) at HEAD `ac582cd`:
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49925 passed, 147 skipped, 0 failed
- `python -m coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 274 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session reproduced NO defect (fresh-angle probe of `snmp._assess_snmp_version` clean, 0 mismatches) and added durable test hardening (no production change):
- `tests/test_snmp.py`: imported `_SNMP_MIN_MAJOR`; added `test_assess_snmp_version_threshold_matrix` (15-case product/version matrix vs independent oracle), `test_assess_snmp_version_requires_dotted_version` (bare versions -> no match), `test_assess_snmp_version_threshold_boundaries` (major==threshold supported, major==threshold-1 old). Fills a real gap (prior tests only covered Linux/Cisco/FreeBSD).

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
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests); do not change without a reproduced failure.
- `snmp._assess_snmp_version` requires a DOTTED version; `windows server` threshold unreachable for bare "Windows Server 2016". Do NOT change the regex without a reproduced functional failure + explicit design.
- Do not commit manually; the workflow controller stages and commits.
- Tooling note: invoke as `python -m coverage|mypy|ruff` (bare `coverage` not on PATH).

## This session (negative result + test hardening)
Fresh-angle probe (clean, 0 mismatches — do not repeat without NEW evidence):
- `snmp._assess_snmp_version` full product/threshold matrix + threshold boundaries + dotted-version contract + case-insensitivity + empty/None.
Added three matrix/boundary tests to `tests/test_snmp.py` to lock the contract durably.

## Next task (precise, evidence-based)
No queued assignment. All gates green (49925 passed / 147 skipped / 0 failed, 100% coverage clean, mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Pick ONE remaining untouched pure helper with a stdlib/simple oracle (do NOT repeat angles in the do-not-repeat lists in HANDOFF_NEXT.md). Untouched candidates:
  - `tls.enumerate_tls` aggregation invariants (`versions_tested`/`supported_version_count` vs list lengths; `supported_versions` subset/order) under randomized monkeypatched probes (unit-tested, no property test).
  - `tls._resolve_versions` / `_validate_ciphers` normalization over randomized alias/cipher inputs vs an independent oracle.
  - `snmp._parse_oid` / `_parse_tlv` / `_decode_varbind_value` round-trip vs an independent encoder oracle (pure, byte-level).
  - `snmp._normalize_communities` / `_normalize_valid_communities` coercion vs a hand oracle.
- Reproduce a concrete defect FIRST (focused failing check with running evidence vs an independent oracle). If nothing reproduces, record the negative result, preserve the baseline, optionally add ONE tight property test that locks a genuinely-new invariant, and hand off again — do not fabricate work.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate (`python -m coverage erase && python -m coverage run -m pytest -q`, `python -m coverage report`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`).

(End of file)