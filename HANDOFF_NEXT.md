# Handoff

## Status
Repository is green after a real fix this session (2026-11-26, Python 3.14.4). A second genuine wrong-output defect of the SAME class as the prior `extract_referral_server` fix was reproduced in `ethscan/whois.py::parse_whois`, fixed minimally, and covered by a regression test. All five gates re-run green first-hand.

## What changed (this session)
- **Fixed a genuine wrong-output defect in `ethscan/whois.py::parse_whois` (empty same-line value crosses lines).**
  - Repro (before fix): `parse_whois("Creation Date: \nRegistrar: Example Inc\n")` returned `creation_date == "Registrar: Example Inc"` (the next line's leading label captured as the date); `parse_whois("Registrar: \nCreation Date: 2020-01-01\n")` returned `registrar == "Creation Date: 2020-01-01"`; `parse_whois("Name Server: \nStatus: ok\n")` returned `nameservers == ["Status:"]`; `parse_whois("Status: \nRegistrar: Example\n")` returned `status_codes == ["Registrar:"]` — garbage, not field values.
  - Root cause: every field pattern used `\s*` between the label and the value. `\s` matches newlines, so a label with an empty same-line value spilled onto the next line and `(.+)`/`(\S+)` captured that line's leading label as the value. Identical root cause to the `extract_referral_server` fix in the previous session.
  - Fix: changed `\s*` to `[ \t]*` (horizontal whitespace only) in all four field pattern groups (registrar / creation_date / expiration_date / registrant_org) AND the `Name Server:` / `Status:` `re.findall` patterns, so a value must sit on the label's own line. An empty same-line value now yields an empty string (falsy -> rendered as `N/A`) instead of the next line's label. All other logic (priority order, negative lookbehind for `Sponsoring Registrar`, `.strip()`, dedupe/sort) untouched.
- **Test added** in `tests/test_whois.py`: `test_parse_whois_empty_value_does_not_cross_lines` (the four reproduced mismatches now parse correctly). Coverage stays 100%.

## What was actually verified (evidence, first-hand this session)
- `python -m pytest -q` -> **49844 passed, 147 skipped, 0 failed** (167s; baseline 49843, +1 new test).
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 272 source files**.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**.
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**.
- `python -m coverage run -m pytest -q` then `coverage report` -> **TOTAL 100% (16292 stmts, 0 missing)**.
- Focused `pytest tests/test_whois.py -q` -> 55 passed.

## Candidates checked and found CLEAN this session (do not re-run unchanged)
- `redis._parse_info` / `redis._parse_config` / `redis._parse_resp*`: RESP/INFO/CONFIG parsing correct on inspection (bulk-string length handling, null bulk string, array recursion, even-length config pairs).
- `mysql._parse_handshake`: best-effort HandshakeV10 parser; bounds-checked at each step, returns partial dicts; no wrong-output on inspection.
- `snmp._parse_oid`: base-128 first-subidentifier handling correct (multi-byte arc-2 covered).
- `cert._extract_subdomains`, `nmap._parse_port`/`_parse_host`, `config._parse_set_value`, `report._parse_ports`, `vuln.parse_banner`/`_version_tuple`/`version_in_range`/`_pad_versions`: correct on inspection (version padding handles `1.3`==`1.3.0`).

## What remains unresolved
- Low-severity edge (NOT fixed, no code-execution risk): `fileio.sanitize_csv_cell` leaves `-inf`/`+inf`/`inf`/`nan`/`-nan` unsanitised because `float()` parses them. Only a spreadsheet `#NAME?`/error, not injection. Do not change without a reproduced functional failure.
- Documented limitations unchanged:
  - `ethscan/cli.py:4316` unreachable defensive guard (intentionally uncovered).
  - `oracle`/`postgresql` empty-target handling stays in-band (exit 0) per contract.
  - Do not modify `.github/workflows/**`.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes) by design and is tested; do not "fix" without a reproduced functional failure.

## Approaches already tried / ruled out (do not repeat)
- All pure-helper oracle verifications in ORACLE_VERIFICATION_TARGET.md + prior HANDOFFs; CSV formula-injection sweep; parser/adversarial STRING fuzz; formatter/assessor hostile contracts; CLI target/option hostile sweeps; broad `except Exception` audit; IPv6 transport; empty-target rejection; radix math vs `ipaddress`; `target.py` parsers; hash/passwords/jwt/scanner/cidr wrong-output fuzz; fileio/completion/whois/dns normalize fuzz (prior sessions).
- Prior sessions: `completion.generate_completion_script`, `web.check_security_headers`, `fileio.read_lines`, `whois.parse_whois` (Sponsoring-Registrar priority), `completion.detect_shell`, `web._assess_web_server_version`, `fileio.sanitize_csv_cell`, `whois.extract_referral_server` (empty-value newline spill), `web._parse_url`, `oracle_verify_service.py`, `scanner.parse_port_range` — all clean/fixed; do not repeat unchanged.
- This session: `whois.parse_whois` empty-value newline spill (one defect, now fixed) — do not repeat unchanged. Redis/mysql/snmp/cert/nmap/config/report/vuln parsers inspected clean (above).

## Next task (precise, evidence-based)
- Do NOT repeat a verification-only session. The newline-spill class (`\s*` between a label and a same-line value) is now fixed in `whois.extract_referral_server` AND `whois.parse_whois`. The same `\s*`-vs-`[ \t]*` pattern may exist in OTHER modules that parse labelled text. Fresh angle: grep for `:\s*(\S+)` / `:\s*(.+)` style patterns in the remaining protocol modules (e.g. `ftp._assess_ftp_version`, `smtp._parse_smtp_response`/`_assess_smtp_version`, `ldap._assess_ldap_version`, `oracle._assess_version`, `memcached`, `mongodb`, `mssql`, `postgresql`, `ssh`, `tls`/`ssl`, `geo`, `mac`, `osdetect`) and reproduce a concrete empty-value line-crossing mismatch before changing anything.
- Reproduce a concrete defect first (focused failing check). Only then apply the smallest reversible fix, add/extend a test to keep coverage 100%, and rerun the full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`, coverage).
- If green and no new defect reproduces, record the negative result, preserve the green baseline, and hand off again — do not fabricate work.

(End of file - total 50 lines)