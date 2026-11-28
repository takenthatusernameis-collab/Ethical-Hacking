# Handoff

## Session (Sat Nov 28 2026, password-strength property-test hardening)

- No prior concrete assignment existed (HANDOFF_NEXT/NEXT_TASK said "None pending; repo fully green"). Per the task rules I did NOT repeat a verification-only session: I independently re-verified the true baseline first-hand, ran fresh-angle oracle probes, reproduced NO defect, and added durable test hardening (checksum/netbios/nmap precedent).
- Independently re-verified baseline at HEAD `60f353e`: `python -m pytest -q` -> 49975 passed, 147 skipped, 0 failed; `python -m mypy ethscan/ tests/` clean (279 files); `ruff` clean; `check_readme.py` 54/54, 0 drift; `coverage run --branch --source=ethscan` TOTAL 100%; `git status` clean.
- Fresh-angle oracle probes (all clean, 0 mismatches — ruled out, NOT defects, do not repeat unchanged):
  - Version matching: `vuln.version_in_range` / `cve._lookup_cve_id` / `vuln.match_service_vulns` vs an independent oracle (different comparison algorithm) over 60k random specs + 20k lookup/match consistency cases -> 0 mismatches.
  - Password helpers: `has_repeated_patterns` vs a brute-force repeated-substring oracle, `_character_pool`/`estimate_entropy` vs a from-scratch pool/entropy oracle, `evaluate_password` score/verdict invariants -> 0 mismatches / 100k cases. Implementation is correct.
  - `cert._extract_subdomains` (CT `name_value` newline-split/dedup/sort) vs an independent dedupe/sort oracle over 5000 random entries + hostile crash probes (`entries` non-list/non-dict, CRLF/tab values, non-string `name_value`) -> 0 mismatches, 0 crashes. Lead closed: do not re-probe unchanged.
  - `snmp._decode_varbind_value` / `_assign_varbind` reviewed: defensive `.get()` lookups, `int.from_bytes`, `.decode("utf-8","replace")`, `.hex()` fallbacks, OID-key guard — no gap; `_parse_oid`/`_split_first_subidentifier` already property-tested (50,000 round-trip cases). Lead closed: do not re-probe unchanged.

## What changed

- `tests/test_passwords.py` only (+143 lines, test-only, fully reversible, no production change). Added 3 seeded property tests with independent LOCAL oracles (do not import the module's constants):
  - `test_has_repeated_patterns_matches_bruteforce_oracle` — 3000 random + constructed exact `half+half` repeats at every max pattern length (catches loop-bound off-by-one).
  - `test_estimate_entropy_matches_pool_oracle` — 3000 random vs from-scratch pool/entropy.
  - `test_evaluate_password_score_and_verdict_invariants` — 3000 random + constructed length-swept numeric strings (a length-10 digit string scores ~83, inside the [80,85) band) pinning score in [0,100] and verdict-vs-threshold mapping.
- Why: these security-relevant helpers had only example-based tests; a regression in the pattern loop bounds, entropy pool, or verdict thresholds would pass the examples. Now locked by property tests.

## What was actually verified (evidence)

- Mutation checks (each caught; source restored, `git diff ethscan/passwords.py` empty after):
  1. `for length in range(2, max_pattern + 1)` -> `range(2, max_pattern)` -> `test_has_repeated_patterns_matches_bruteforce_oracle` FAILS (`f-f-`).
  2. UPPER pool `pool += 26` -> `pool += 25` -> `test_estimate_entropy_matches_pool_oracle` FAILS.
  3. verdict `score >= 80` -> `score >= 85` -> `test_evaluate_password_score_and_verdict_invariants` FAILS.
- `python -m pytest -q` -> 49978 passed, 147 skipped, 0 failed (baseline 49975; +3 new tests).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 279 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; exit 0.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 100% (16295 stmts, 6178 branches, 0 missing).
- `git status` -> only `tests/test_passwords.py` modified (143 insertions); `git diff --check` clean. Not committed (controller commits).

## Blockers

- None.

## Approaches already tried / ruled out

- Version matching and password helpers: property-probed correct this session; not defects; do not re-probe unchanged.
- All prior fresh-angle sweeps (CSV injection, parser/formatter/assessor/CLI hostile sweeps, nested-field fuzz, radix/target/hash/jwt/scanner/cidr/whois/s3/mac/nmap/tls/version/netbios/config/service probes): clean; not repeated.

## Next task

- None pending. Repository fully green with 100% coverage (49978 passed). Do NOT fabricate work or repeat verification-only sessions. If future work is needed, reproduce a concrete gap first (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then the full gate (pytest/coverage/mypy/ruff/check_readme), preserve safety.
- Evidence-based leads NOT yet done: none remaining — both previously listed leads (`cert._extract_subdomains`, `snmp._decode_varbind_value`/`_assign_varbind`) were probed clean this session; do not re-probe unchanged.
- `oracle`/`postgresql` empty-target handling and `ethscan/cli.py` unreachable guard remain intentionally out of scope. Do not modify `.github/workflows/**`.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.75 min (49978 tests). Do not commit manually; the workflow controller stages and commits.