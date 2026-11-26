# Handoff

## Status
Repository is green after a real fix this session (2026-11-26, Python 3.14.4). One genuine wrong-output defect in `ethscan/whois.py::parse_whois` was reproduced with a concrete oracle mismatch, fixed minimally, and covered by tests. All five gates re-run green first-hand.

## What changed (this session)
- **Fixed a genuine wrong-output defect in `ethscan/whois.py::parse_whois` (registrar field).**
  - Repro (before fix): `parse_whois("Sponsoring Registrar: Spons Registrar LLC\nRegistrar: Real Registrar Inc\n")["registrar"]` returned `"Spons Registrar LLC"` (the Sponsoring value) instead of `"Real Registrar Inc"`.
  - Root cause: the plain pattern `r"Registrar:\s*(.+)"` is a substring of `Sponsoring Registrar:`. `re.search` finds the earliest occurrence, so when a `Sponsoring Registrar:` line precedes the real `Registrar:` line, the plain pattern matches inside the Sponsoring line and the documented priority order (Registrar > Registrar Name > Sponsoring Registrar) is defeated.
  - Fix: negative lookbehind `(?<!Sponsoring )` on the plain pattern so it no longer matches the `Registrar:` substring inside `Sponsoring Registrar:`. Smallest reversible change; all other patterns and the Sponsoring fallback are untouched.
- **Tests updated/added** in `tests/test_whois.py`:
  - `test_parse_whois_multiple_patterns` expectation corrected `Registrar A` -> `Registrar B` (it previously codified the substring bug: with no plain `Registrar:` line, `Registrar Name:` (priority 2) must beat `Sponsoring Registrar:` (priority 3)).
  - Added `test_parse_whois_plain_registrar_beats_sponsoring` (the reproduced defect) and `test_parse_whois_sponsoring_registrar_fallback` (Sponsoring still used when it is the only registrar line). Coverage stays 100%.

## Candidates checked and found CLEAN this session (do not re-run unchanged)
- `completion.generate_completion_script` `prog_name` -> `_<NAME>_COMPLETE` derivation: matches installed click 8.1.8 exactly (`prog_name.replace("-","_").replace(".","_")` then `.upper()`), verified against `click.core.BaseCommand._main_shell_completion` source.
- `web.check_security_headers` present/missing classification: correct for lowercase-key dicts (its documented contract).
- `fileio.read_lines` comment/blank handling: correct for `skip_comments` True/False, inline `#`, tabs, CRLF.

## What was actually verified (evidence, first-hand this session)
- `python -m pytest -q` -> **49841 passed, 147 skipped, 0 failed** (198s; baseline 49839, +2 new tests).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 272 source files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run -m pytest -q` then `coverage report` -> **TOTAL 100% (16284 stmts, 0 missing)**.

## What remains unresolved
- None for this fix. Documented limitations unchanged:
  - `ethscan/cli.py:4316` unreachable defensive guard (intentionally uncovered).
  - `oracle`/`postgresql` empty-target handling stays in-band (exit 0) per contract.
  - Do not modify `.github/workflows/**`.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" without a reproduced functional failure.

## Approaches already tried / ruled out (do not repeat)
- All pure-helper oracle verifications in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; CSV formula-injection sweep; parser/adversarial STRING fuzz; formatter/assessor hostile contracts; CLI target/option hostile sweeps; broad `except Exception` audit; IPv6 transport; empty-target rejection; radix math vs `ipaddress`; `target.py` parsers; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize fuzz (prior session).
- This session's fresh wrong-output probes over `completion.generate_completion_script`, `web.check_security_headers`, `fileio.read_lines` (all clean) and `whois.parse_whois` (one defect, now fixed) — do not repeat unchanged.
- Repeating verification-only sessions with no new evidence is discouraged; do not do it again without a concrete new probe or reproduced defect.

## Next task (precise, evidence-based)
- Do NOT repeat a verification-only session. If a session is needed, use a fresh angle not yet covered: property-check remaining pure-ish helpers for WRONG OUTPUT against a ground-truth oracle. Still-uncovered candidates: `whois.extract_referral_server` (re-fuzz after the prior scheme fix with a hostname oracle), `web._assess_web_server_version` version/major extraction vs a hand oracle, `web._parse_url` port/scheme defaults, `completion.detect_shell` edge shapes, `fileio.sanitize_csv_cell` numeric-vs-formula classification.
- Reproduce a concrete defect first (focused failing check or oracle mismatch). Only then apply the smallest reversible fix, add/extend a test to keep coverage 100%, and rerun the full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`, coverage).
- If green and no new defect reproduces, record the negative result, preserve the green baseline, and hand off again — do not fabricate work.
- Remaining candidate work (not pure helpers in current form) would require extracting pure helpers from I/O-bound functions before applying the oracle pattern.