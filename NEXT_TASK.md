## Next task
No queued assignment. Repository fully green and independently re-verified this session (2026-11-26, Python 3.14.4):
- `pytest -q` -> 49842 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (272 files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift, exit 0
- coverage -> TOTAL 100% (16284 stmts, 0 missing)

This session fixed a genuine wrong-output defect in `ethscan/whois.py::extract_referral_server`: the `\s*` between a label and its value matched newlines, so a label with an empty same-line value (e.g. `Registrar WHOIS Server: \nWHOIS Server: whois.other.com`) captured the next line's leading keyword (`whois`, `refer:`) as the referral hostname. Fixed by restricting the separator to `[ \t]*`; the real referral on the following line is now returned. Added `test_extract_referral_server_empty_value_does_not_cross_lines`. Also verified `completion.detect_shell`, `web._assess_web_server_version`, and `fileio.sanitize_csv_cell` are clean.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py:4316` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check or oracle mismatch), then rerun the full gate. If nothing reproduces, record the new negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.
- `sanitize_csv_cell` leaving `-inf`/`+inf`/`nan` unsanitised is a low-severity edge (spreadsheet error, not injection); do not change without a reproduced functional failure.

## Evidence-based lead for a future session (only if a session is needed)
- Use a fresh angle not yet covered: property-check `web._parse_url` port/scheme defaults against a `urllib.parse` ground-truth oracle (non-http schemes, explicit default ports, userinfo, IPv6, uppercase scheme). Not yet fuzzed.
- Already property-checked (do not repeat): all pure helpers listed in ORACLE_VERIFICATION_TARGET.md + HANDOFF_NEXT.md, radix math, `target.py` parsers, hash/passwords/jwt/scanner/cidr, fileio/completion/whois/dns normalize, and the completion/headers/read_lines/parse_whois/detect_shell/server_version/sanitize_csv_cell/extract_referral_server helpers.