# Handoff

## Status
Repository is green after a real fix this session (2026-11-26, Python 3.14.4). One genuine wrong-output defect in `ethscan/whois.py::extract_referral_server` was reproduced with concrete oracle mismatches, fixed minimally, and covered by a regression test. All five gates re-run green first-hand.

## What changed (this session)
- **Fixed a genuine wrong-output defect in `ethscan/whois.py::extract_referral_server` (empty same-line value).**
  - Repro (before fix): `extract_referral_server("Registrar WHOIS Server: \nWHOIS Server: whois.other.com\n")` returned `"whois"` (the `WHOIS` keyword of the next line) and `extract_referral_server("Registrar WHOIS Server:\nRefer: whois.other.com\n")` returned `"refer:"` — garbage, not a hostname.
  - Root cause: each pattern used `\s*` between the label and the value. `\s` matches newlines, so when a label had an empty same-line value the match spilled onto the next line and `(\S+)` captured that line's leading keyword (`WHOIS`, `Refer:`) as if it were the referral hostname.
  - Fix: changed `\s*` to `[ \t]*` (horizontal whitespace only) in all five patterns so the value must sit on the label's own line. Smallest reversible change; the value now falls through to the next pattern and the real referral on a following line is returned. All other logic (scheme strip, lowercasing, trailing-dot strip, whois.iana.org exclusion) untouched.
- **Test added** in `tests/test_whois.py`: `test_extract_referral_server_empty_value_does_not_cross_lines` (the two reproduced mismatches now return `whois.other.com`; a bare hostname alone on the line after a label returns `None`). Coverage stays 100%.

## Candidates checked and found CLEAN this session (do not re-run unchanged)
- `completion.detect_shell`: correct for `SHELL` unset/empty, bare names, full paths, trailing slash, `//bash`, deep paths; returns `None` for `/bin/sh`, `/bin/BASH`, `*.exe`, surrounding spaces (documented contract: `Path(name).name` in {bash,zsh,fish}).
- `web._assess_web_server_version`: version/major extraction and old-version thresholds correct across Apache/nginx/lighttpd/IIS/Microsoft-IIS, case-insensitive, space or slash separator, 1-3 component versions, multi-server headers (first match wins), `Apache-Coyote` correctly yields no finding (separator is `-`, not `/`/space).
- `fileio.sanitize_csv_cell` numeric-vs-formula classification: correct for `= + - @ TAB CR` triggers, `-1/+2/3.14/-1.5e3/-.5`, and non-numeric `-cmd`/`+cmd`/`@cmd` get the `'` prefix. (Note: `float()` accepts `inf`/`nan`/`-inf`/`+inf`, so those `-`/`+`-leading tokens are left unsanitised — a low-severity edge, see unresolved; NOT a code-execution vector, do not "fix" without a demonstrated functional failure.)

## What was actually verified (evidence, first-hand this session)
- `python -m pytest -q` -> **49843 passed, 147 skipped, 0 failed** (167s; baseline 49842, no new tests).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 272 source files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run -m pytest -q` then `coverage report` -> **TOTAL 100% (16292 stmts, 0 missing)**.
- Fresh oracle probe `oracle_verify_service.py` (`_parse_banner_service`, `_parse_banner_version`) -> **0 mismatches** (hostile banner/service matrix).
- Fresh oracle probe of `ethscan.scanner.parse_port_range` (independent oracle over 57 directed specs + 4000 randomized fuzz specs) -> **0 mismatches, 0 crashes**.

## What remains unresolved
- Low-severity edge (NOT fixed, no code-execution risk): `sanitize_csv_cell` leaves `-inf`/`+inf`/`inf`/`nan`/`-nan` unsanitised because `float()` parses them, though they begin with a formula trigger char. Only a spreadsheet `#NAME?`/error, not injection. Do not change without a reproduced functional failure.
- Documented limitations unchanged:
  - `ethscan/cli.py:4316` unreachable defensive guard (intentionally uncovered).
  - `oracle`/`postgresql` empty-target handling stays in-band (exit 0) per contract.
  - Do not modify `.github/workflows/**`.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" without a reproduced functional failure.

## Approaches already tried / ruled out (do not repeat)
- All pure-helper oracle verifications in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; CSV formula-injection sweep; parser/adversarial STRING fuzz; formatter/assessor hostile contracts; CLI target/option hostile sweeps; broad `except Exception` audit; IPv6 transport; empty-target rejection; radix math vs `ipaddress`; `target.py` parsers; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize fuzz (prior sessions).
- Prior session: `completion.generate_completion_script`, `web.check_security_headers`, `fileio.read_lines` (clean) and `whois.parse_whois` (fixed).
- This session: `completion.detect_shell`, `web._assess_web_server_version`, `fileio.sanitize_csv_cell` (clean, see above) and `whois.extract_referral_server` (one defect, now fixed) — do not repeat unchanged.
- **This session (additional): `web._parse_url` port/scheme defaults against `urllib.parse` oracle — clean, 0 mismatches. Do not repeat.**
- **This session (additional): `oracle_verify_service.py` (`_parse_banner_service`/`_parse_banner_version`) — clean, 0 mismatches. Do not repeat.**
- **This session (additional): `ethscan.scanner.parse_port_range` independent oracle (57 directed specs + 4000 randomized fuzz specs) — clean, 0 mismatches, 0 crashes. Do not repeat.**
- Repeating verification-only sessions with no new evidence is discouraged; do not do it again without a concrete new probe or reproduced defect.

## Next task (precise, evidence-based)
- Do NOT repeat a verification-only session. If a session is needed, use a fresh angle not yet covered: property-check remaining pure-ish helpers for WRONG OUTPUT against a ground-truth oracle. All pure helpers in `ethscan.target`, `ethscan.web`, `ethscan.completion`, `ethscan.fileio`, `ethscan.whois`, `ethscan.dns` have been oracle-verified.
- Remaining candidates are not pure helpers in current form (I/O-bound) and would require extracting pure helpers before applying the oracle pattern.
- Reproduce a concrete defect first (focused failing check or oracle mismatch). Only then apply the smallest reversible fix, add/extend a test to keep coverage 100%, and rerun the full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`, coverage).
- If green and no new defect reproduces, record the negative result, preserve the green baseline, and hand off again — do not fabricate work.

(End of file - total 43 lines)