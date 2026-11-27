## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49944 passed, 147 skipped, 0 failed
- `python -m coverage report` -> TOTAL 100% (16299 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 276 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session reproduced NO defect (fresh-angle property probes of `tls._resolve_versions`/`_validate_ciphers` clean, 0 mismatches across 1000 seeded trials) and added durable test hardening (no production change):
- `tests/test_tls.py`: added `test_resolve_versions_property_vs_oracle` (500 randomized trials vs VERSION_ALIASES oracle), `test_validate_ciphers_property_vs_oracle` (500 randomized trials vs COMMON_CIPHERS oracle). Locks normalization invariants for string aliases, TLSVersion members, whitespace stripping, empty-string skipping, and error collection.
- `tests/test_snmp.py`: removed unused imports `_normalize_communities`, `_normalize_valid_communities` (ruff F401 fix).

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
Fresh-angle probes (clean, 0 mismatches — do not repeat without NEW evidence):
- tls `_resolve_versions`/`_validate_ciphers` property vs independent oracle: `_resolve_versions` (string aliases from VERSION_ALIASES, TLSVersion members, invalid specs collected); `_validate_ciphers` (valid ciphers from COMMON_CIPHERS, whitespace stripping, empty-string skipping, invalid ciphers collected). 1000 seeded trials, 0 mismatches.
- Prior session's snmp BER encode/decode round-trip vs independent oracle: also clean (do not repeat).
Added two property tests to `tests/test_tls.py` (no production change). Full gate green after the change: 49944 passed, 147 skipped, 0 failed; 100% coverage clean; mypy/ruff/check_readme clean.

## Next task (precise, evidence-based)
No queued assignment. All gates green (49944 passed / 147 skipped / 0 failed, 100% coverage clean, mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- The two "untouched candidates" previously listed (`tls.enumerate_tls` aggregation invariants; `snmp._normalize_communities`/`_normalize_valid_communities`) have already been addressed with property tests in prior sessions:
  - `tests/test_tls.py::test_enumerate_tls_aggregation_invariants` (500 trials, locks: `versions_tested`/`supported_version_count` vs list lengths; `supported_versions` subset/order; canonical sorting)
  - `tests/test_snmp.py::test_normalize_communities_property_vs_oracle` (500 trials vs hand oracle)
  - `tests/test_snmp.py::test_normalize_valid_communities_property_vs_oracle` (500 trials vs hand oracle)
- No remaining pure helpers with stdlib/simple oracles are known to be untouched. If future work is needed, reproduce a concrete gap first (focused failing check or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then broader gates (pytest/mypy/ruff/check_readme/coverage), preserve safety.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate (`python -m coverage erase && python -m coverage run -m pytest -q`, `python -m coverage report`, `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`).

(End of file)