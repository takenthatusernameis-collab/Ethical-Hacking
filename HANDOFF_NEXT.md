# Handoff

## Status
Repository is fully green. Independently re-verified this session (2026-11-26, Python 3.14.4); working tree clean at start and end (no source/test changes made).

## What changed (this session)
- **None (no source/test changes).** Per the reliability rules I did NOT repeat a verification-only session: I ran a FRESH-ANGLE wrong-output fuzzer (not a repeat of prior exception sweeps) and reproduced NO defect. Recording the negative result durably.

### Fresh-angle investigation (evidence)
Wrote and ran a wrong-output property fuzzer (`/tmp/.../fuzz_wrong_output.py`, not committed) comparing computational helpers against ground-truth oracles. Areas covered (NOT previously property-checked for wrong output):
- `hash.run_hash` / `run_check` vs `hashlib`/`hmac`/`hashlib.pbkdf2_hmac` — all algorithms × {plain, salt, pepper, salt+pepper, iterations, iterations+pepper}. 4000 + 3000 cases.
- `passwords.estimate_entropy` vs the `pool**len` formula; `evaluate_password` score∈[0,100] + verdict/threshold consistency + `too_short` correctness. 6000 cases.
- `jwt.run_jwt` exp/nbf/iat status vs a hand oracle (incl. bool/NaN/Inf/string claims). 4000 cases.
- `scanner.parse_port_range` vs a hand oracle (random valid/inverted/out-of-range/empty/non-numeric specs). 5000 cases.
- `cidr._format_network_info` total/netmask/wildcard/network/broadcast/prefixlen vs `ipaddress` (excluding the intentional IPv6 anycast usable-host convention). 4000 cases.
- Result: **0 genuine defects.** All categories clean except an initial 1005 "mismatches" that were ALL my oracle mis-modeling the PBKDF2+pepper path (see below).

### PBKDF2+pepper is correct, not a defect (verified)
My oracle HMAC'd the RAW PBKDF2 bytes; the implementation HMACs the HEX-STRING digest. Confirmed this is the INTENDED, TESTED behavior:
- `tests/test_hash.py::test_compute_password_hash_iterations_with_pepper` (line ~711) asserts HMAC over `pbkdf2_digest.encode("utf-8")` where `pbkdf2_digest = hashlib.pbkdf2_hmac(...).hex()`.
- `tests/test_hash.py::test_compute_password_hash_iterations_md4_with_pepper` (line ~759) comment: "Uses hex PBKDF2 digest as HMAC message (consistent with SHA256 behavior)".
- `tests/test_hash.py::_peppered_pbkdf2_digest` (line ~1083) and `test_run_hash_iterations_with_pepper` / `test_run_check_iterations_with_pepper_match` codify the same.
- `run_check` round-trip matches `run_hash` for the same params (verified across 3000 random cases). No functional defect.

### Baseline re-verification evidence (2026-11-26, first-hand)
- `python -m pytest -q` -> **49839 passed, 147 skipped, 0 failed** (198s)
- `python -m mypy ethscan/ tests/` -> **Success: no issues found in 272 source files**
- `python -m ruff check ethscan/ tests/ check_readme.py` -> **All checks passed**
- `python3 check_readme.py` -> **54 CLI commands, 0 drift both directions, exit 0**
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> **TOTAL 100% (16282 stmts, 6166 branches, 0 missing)** on Python 3.14.4

Prior oracle probes remain clean: `hash._infer_algorithm` (1.3M+), `target` helpers (~115k), `mac` (40k+), `geo` (8M+), `service._parse_banner_service`/`_parse_banner_version` (~10M+), `vuln.version_in_range` (200k+). All 0 mismatches.

## What was actually verified (evidence)
- All five gates above green (first-hand this session).
- Fresh wrong-output fuzzer: 0 genuine defects across hash/passwords/jwt/scanner/cidr.
- `report.py`/`config.py`/`nmap.py`/`mac.py` source-reviewed: formatters guarded with `isinstance`/`_as_list`; parsers validate ranges; no wrong-output gap.

## What remains unresolved
- None for these checks. Documented limitations unchanged:
  - `ethscan/cli.py:4316` unreachable defensive guard (intentionally uncovered).
  - `oracle`/`postgresql` empty-target handling stays in-band (exit 0) per contract.
  - Do not modify `.github/workflows/**`.
- PBKDF2+pepper HMACs the hex-string digest (not raw bytes). Self-consistent and tested; a raw-bytes reading of the docstring is a possible future doc clarification, NOT a defect. Do not "fix" it without a reproduced functional failure.

## Approaches already tried / ruled out (do not repeat)
- All pure-helper oracle verifications listed above; CSV formula-injection sweep; parser/adversarial STRING fuzz; formatter/assessor hostile contracts; CLI target/option hostile sweeps; broad `except Exception` audit; IPv6 transport; empty-target rejection; radix math vs `ipaddress`; `target.py` parsers.
- This session's fresh wrong-output fuzzer (hash/passwords/jwt/scanner/cidr) — clean; do not repeat unchanged.
- Repeating verification-only sessions with no new evidence is explicitly discouraged; do not do it again without a concrete new probe or a reproduced defect.

## Next task (precise, evidence-based)
- Do NOT repeat a verification-only session. If a session is needed, use a fresh angle not yet covered: property-check the remaining pure-ish helpers for WRONG OUTPUT against a ground-truth oracle. Uncovered candidates: `fileio.load_json`/`csv_writer`/`sanitize_csv_cell`, `completion.detect_shell`/`install_completion` path logic, `headers`/`whois`/`dns` record parsers.
- Reproduce a concrete defect first (focused failing check or oracle mismatch). Only then apply the smallest reversible fix and rerun the full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/ check_readme.py`, `python3 check_readme.py`, coverage).
- If green and no new defect reproduces, record the negative result, preserve the green baseline, and hand off again — do not fabricate work.
- Remaining candidate work (not pure helpers in current form) would require extracting pure helpers from I/O-bound functions (e.g., `grab_banner` transport logic, `run_service` threading logic) before applying the oracle pattern.