# Handoff

## Session (Sat Nov 28 2026, `cert._extract_subdomains` independent property tests)

- Executed the prior handoff's evidence-based lead. The two leads named in the last
  TASK.md session were BOTH already implemented (stale handoff):
  - `redis._parse_info` / `redis._parse_config` -> already covered by
    `tests/test_redis_info_config_property.py` (commits 3da3eaa/4387f70).
  - `osdetect._match_os_from_ttl` / `_match_os_from_banner` -> already covered by
    `tests/test_osdetect_match_property.py` (oracle reads `OS_SIGNATURES`).
  I differential-fuzzed both first (0 mismatches / 20k-30k cases each) and confirmed
  they are correct; I did NOT re-add duplicate tests (removed a redundant osdetect
  file I had started, to respect the no-fabrication rule).
- Pivoted to a genuinely uncovered, security-relevant pure helper:
  `ethscan.cert._extract_subdomains` (cert.py:160) — parses untrusted CT
  `name_value`/`common_name` (multiline, mixed case, padded) into a unique sorted
  subdomain list. It had only 4 example tests and NO property test.

## What changed (test-only; NO production code)

- `tests/test_cert_extract_subdomains_property.py` (new, 6 tests):
  - `_oracle(cert_data)`: INDEPENDENT from-scratch recomputation (does not call any
    ethscan helper).
  - `test_extract_subdomains_matches_oracle_random`: 3000 seeded random cert_data
    (dict/non-dict entries, name_value/common_name/empty/int, multiline, non-list
    `entries`) assert full equality with the oracle.
  - 5 deterministic edge tests: case-insensitive dedupe+sort, multiline `\r\n`/`\n`
    split, common_name fallback vs name_value precedence, non-dict/non-list entries
    ignored, empty/missing -> `[]`.
- No `ethscan/` source changed (verified correct, not a defect).

## What was actually verified (evidence)

- Differential fuzz BEFORE tests: 30,000 random cases, 0 mismatches (correct).
- Mutation checks (each caught; source restored, `git diff ethscan/cert.py` empty):
  1. `token.strip().lower()` -> `token.strip()` -> 3 tests FAIL.
  2. `return sorted(names)` -> `return names` -> 3 tests FAIL.
- `python -m pytest tests/test_cert_extract_subdomains_property.py -q` -> 6 passed.
- Full gate at this working tree:
  - `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50077 passed,
    147 skipped, 0 failed; TOTAL 100% (16292 stmts, 6178 branches, 0 missing).
  - `python -m mypy ethscan/ tests/` -> Success: no issues in 287 source files.
  - `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
  - `python check_readme.py` -> 54 commands, 0 drift.
- `git status`: only `tests/test_cert_extract_subdomains_property.py` untracked; no
  production code touched; nothing committed (controller commits).

## Blockers

- None.

## Approaches already tried / ruled out

- redis `_parse_info`/`_parse_config` and osdetect matchers: now property-tested
  (redis/osdetect) — do NOT re-probe unchanged.
- `_extract_subdomains`: now property-tested — do not repeat unchanged.
- All prior hostile/formatter/assessor/CLI sweeps, radix/target/hash/passwords/jwt/
  scanner/cidr wrong-output fuzz, whois/s3/mac/nmap/tls/version/netbios/config probes:
  covered in prior sessions — do not repeat unchanged.

## Next task

- One precise, evidence-based, NOT-yet-done lead: add a durable property test for
  `ethscan.whois.extract_referral_server` (whois.py:144). It has only example tests
  (`tests/test_whois.py:469+`) and NO property test; a prior session probed it clean
  over ~5,010 hand-oracle cases (scheme/port/path stripping, `whois.iana.org`
  exclusion, case-insensitivity, priority-by-position) but added no durable test.
  FIRST re-run a differential fuzz vs an independent hand oracle to confirm it is
  still correct (do not change source without a reproduced defect), then add
  `tests/test_whois_referral_property.py` with a LOCAL oracle (do not import source
  helpers), mutation-check, and rerun the full gate (commands below).
- Do NOT fabricate work, repeat verification-only sessions as progress, or make
  empty/control-marker commits. `oracle`/`postgresql` empty-target handling and
  `ethscan/cli.py` unreachable guard remain intentionally out of scope.
  Do not modify `.github/workflows/**`.

## Environment / critical notes

- **Test deps are NOT preinstalled in this environment.** Run:
  `pip install --quiet pytest mypy ruff coverage dnspython` (installs to
  `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` are
  preinstalled; `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5. `coverage`
  is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.8 min (50077 tests). Do not commit manually; the
  workflow controller stages and commits.
- ALWAYS re-verify HEAD first-hand (install deps, run the gate) rather than trusting
  this handoff's "green" claim — prior handoffs were repeatedly stale.