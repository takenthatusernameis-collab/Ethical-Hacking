## Next task
No queued assignment. Repository fully green and independently re-verified this session (2026-11-26, Python 3.14.4):
- `pytest -q` -> 49845 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (272 files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift, exit 0
- coverage -> TOTAL 100% (16292 stmts, 6174 branches, 0 missing)

This session fixed a third genuine wrong-output defect of the same `\s*` newline-spill class as the prior `extract_referral_server` and `parse_whois` fixes: `ethscan/service.py::_parse_banner_version` used `r"Server:\s*([^\r\n]+)"` for the http/https signatures, so a label with an empty same-line value (e.g. `Server: \nDate: ...`) spilled onto the next line and `([^\r\n]+)` captured that line's leading header as the version (`version == "Date: Mon, 01 Jan 2024"`). Fixed by restricting the separator to `[ \t]*` in both the `http` and `https` `Server:` patterns (service.py:57, :61). Added `test_parse_banner_version_empty_value_does_not_cross_lines`.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py:4316` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check), then rerun the full gate. If nothing reproduces, record the new negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge (spreadsheet error, not injection); do not change without a reproduced functional failure.

## Evidence-based lead for a future session (only if a session is needed)
- The newline-spill class (`\s*` between a label and a same-line value) is now fixed in `whois.extract_referral_server`, `whois.parse_whois`, AND `service.py::_parse_banner_version` (`Server:[ \t]*([^\r\n]+)` for http/https). A repo-wide grep for `\s*` label-value separators found no remaining instances of the newline-spill class in protocol modules (the only other `\s*` hits are `wifi.py` `\s*dBm`/trailing and `\s+` between fields, which require a digit-valued capture and do not spill labels).
- Already property-checked / inspected clean (do not repeat): all pure helpers in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs, radix math, `target.py` parsers, hash/passwords/jwt/scanner/cidr, fileio/completion/whois/dns normalize, redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection.

## Update 2026-11-26 (this session)
Reproduced and fixed the `parse_whois` empty-value newline-spill defect (prior session). This session reproduced and fixed the `service.py::_parse_banner_version` empty same-line `Server:` value cross-line spill (see above). Independently re-verified the green baseline (pytest 49845/147/0; mypy 272 files; ruff; check_readme 54/54; coverage 100%). No other code changed; no verification-only repeat.

(End of file - total 26 lines)