## Next task
No queued assignment. Repository fully green and independently re-verified this session (2026-11-26, Python 3.14.4):
- `pytest -q` -> 49841 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (272 files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift, exit 0
- coverage -> TOTAL 100% (16284 stmts, 0 missing)

This session fixed a genuine wrong-output defect in `ethscan/whois.py::parse_whois`: the plain `Registrar:` regex matched the `Registrar:` substring inside `Sponsoring Registrar:`, so a response with both lines returned the Sponsoring value instead of the real `Registrar:` value. Fixed with a negative lookbehind `(?<!Sponsoring )`; updated one characterization test and added two regression tests. Also verified `completion.generate_completion_script` (matches click 8.1.8), `web.check_security_headers`, and `fileio.read_lines` are clean.

## Constraints
- Do NOT modify `.github/workflows/**`.
- Keep `oracle`/`postgresql` empty-target in-band (exit 0) behavior.
- Do not weaken the `ethscan/cli.py:4316` unreachable guard or game coverage.
- A code change must fix a REPRODUCED defect first (focused failing check or oracle mismatch), then rerun the full gate. If nothing reproduces, record the new negative result and stop — do not fabricate work or repeat verification-only sessions without new evidence.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" it without a reproduced functional failure.

## Evidence-based lead for a future session (only if a session is needed)
- Use a fresh angle not yet covered: property-check remaining pure-ish helpers for WRONG OUTPUT against a ground-truth oracle. Uncovered candidates: `whois.extract_referral_server` (re-fuzz with a hostname oracle after the prior scheme fix), `web._assess_web_server_version` version/major extraction, `web._parse_url` port/scheme defaults, `completion.detect_shell` edge shapes, `fileio.sanitize_csv_cell` numeric-vs-formula classification.
- Already property-checked (do not repeat): all pure helpers listed in ORACLE_VERIFICATION_TARGET.md + HANDOFF_NEXT.md, radix math, `target.py` parsers, hash/passwords/jwt/scanner/cidr, fileio/completion/whois/dns normalize, and this session's completion/headers/read_lines/parse_whois.