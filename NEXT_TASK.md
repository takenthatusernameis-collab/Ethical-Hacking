## Next task
No queued assignment. Repository fully green and independently re-verified this session (2026-11-26, Python 3.14.4):
- `pytest -q` -> 49844 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (272 files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift, exit 0
- coverage -> TOTAL 100% (16292 stmts, 0 missing)

This session fixed a second genuine wrong-output defect of the same class as the prior `extract_referral_server` fix: `ethscan/whois.py::parse_whois` used `\s*` between each field label and its value, so a label with an empty same-line value (e.g. `Creation Date: \nRegistrar: Example Inc`) captured the next line's leading label as the value (`creation_date == "Registrar: Example Inc"`). Fixed by restricting the separator to `[ \t]*` in all four field pattern groups and the `Name Server:`/`Status:` findall patterns. Added `test_parse_whois_empty_value_does_not_cross_lines`.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py:4316` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check), then rerun the full gate. If nothing reproduces, record the new negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge (spreadsheet error, not injection); do not change without a reproduced functional failure.

## Evidence-based lead for a future session (only if a session is needed)
- The newline-spill class (`\s*` between a label and a same-line value) is now fixed in `whois.extract_referral_server` and `whois.parse_whois`. The same pattern may exist in other labelled-text parsers. Fresh angle: grep the remaining protocol modules for `:\s*(\S+)` / `:\s*(.+)` patterns (`ftp`, `smtp`, `ldap`, `oracle`, `memcached`, `mongodb`, `mssql`, `postgresql`, `ssh`, `tls`/`ssl`, `geo`, `mac`, `osdetect`) and reproduce a concrete empty-value line-crossing mismatch before changing anything.
- Already property-checked / inspected clean (do not repeat): all pure helpers in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs, radix math, `target.py` parsers, hash/passwords/jwt/scanner/cidr, fileio/completion/whois/dns normalize, and this session's redis/mysql/snmp/cert/nmap/config/report/vuln parser inspection.

## Update 2026-11-26 (this session)
Reproduced and fixed the `parse_whois` empty-value newline-spill defect (see above). Independently re-verified the green baseline (pytest 49844/147/0; mypy 272 files; ruff; check_readme 54/54; coverage 100%). No other code changed; no verification-only repeat.

(End of file - total 26 lines)