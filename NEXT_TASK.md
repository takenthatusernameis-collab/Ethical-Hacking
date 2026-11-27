## Next task
No queued assignment. Repository fully green and re-verified first-hand this session (Python 3.14.4, CLEAN coverage run):
- `python -m coverage erase && python -m coverage run -m pytest -q` -> 49948 passed, 147 skipped, 0 failed
- `python -m coverage report` -> TOTAL 100% (16295 stmts, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 276 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions, exit 0

This session FIXED A REAL REPRODUCED DEFECT (not verification-only):
- `ethscan/mysql.py::_parse_handshake`: `auth-plugin-data-part-1` is a FIXED 8-byte field + 1 filler
  byte. The old code used `payload.find(b"\x00", ...)` to find the salt end, which truncated the salt
  and misaligned capabilities/charset/status whenever a salt byte was 0x00. Reproduced with an
  independent builder oracle: 653 / 20000 mismatches before, 0 / 20000 after. Now reads the fixed
  8-byte window (clamped for truncated packets) and consumes one filler byte.
- `tests/test_mysql.py`: updated ~10 `_parse_handshake` tests from lenient short salts to spec-compliant
  8-byte salts (preserving each early-return branch intent); added
  `test_parse_handshake_null_byte_in_salt` (regression) and `test_parse_handshake_truncated_salt`.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check with running evidence), then
  rerun the full gate. If nothing reproduces, record the negative result and stop — do not fabricate
  work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest by design; do not "fix" without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge; do not change without
  a reproduced failure.
- `headers.run_headers`/`web.run_web_checks` strip the target before building the transport URL; keep.
- `validate._format_network_info` IPv6 /127 is INTENTIONAL and tested; do NOT align to cidr's anycast
  convention without a reproduced failure + explicit design.
- ssl `key_size`/`signature_algorithm` are inert on Python 3.14; do not chase without a bounded stdlib approach.
- mongodb `_parse_buildinfo_response` line 191 off-by-one is masked (output correct); do not change without a
  reproduced functional failure.
- `dns.run_dns` `record_types_queried` reports the RAW requested types by design (asserted by tests).
- `snmp._assess_snmp_version` requires a DOTTED version; `windows server` threshold unreachable for bare
  "Windows Server 2016". Do NOT change the regex without a reproduced functional failure + explicit design.
- MySQL `_parse_handshake` salt1 is now spec-correct (fixed 8 bytes + filler); do not reintroduce
  null-terminated salt scanning.
- Do not commit manually; the workflow controller stages and commits.
- Tooling note: invoke as `python -m coverage|mypy|ruff` (bare `coverage` not on PATH).

## Next task (precise, evidence-based)
No queued assignment. All gates green (49948 passed / 147 skipped / 0 failed, 100% coverage clean,
mypy/ruff/check_readme clean). Do NOT repeat verification-only sessions without NEW evidence or a NEW angle.
- Candidate areas NOT yet oracle-verified in prior handoffs (reproduce a gap BEFORE changing anything):
  - `redis._parse_resp` RESP round-trip vs an independent oracle (simple strings, integers, bulk strings,
    arrays, null bulk/array, truncated inputs).
  - `mysql._parse_handshake` full-field round-trip (salt2 / auth_plugin_name byte offsets) vs an independent
    builder — the salt1 fix this session only covered the misalignment; salt2/plugin-name offsets are
    untouched by an oracle.
- If a defect is fixed: add/extend a test to keep coverage 100%, then rerun the full gate
  (`python -m coverage erase && python -m coverage run -m pytest -q`, `python -m coverage report`,
  `python -m mypy ethscan/ tests/`, `python -m ruff check ethscan/ tests/ check_readme.py`,
  `python3 check_readme.py`).

(End of file)