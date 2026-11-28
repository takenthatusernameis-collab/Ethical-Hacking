# Next task

One precise, evidence-based, NOT-yet-done lead: add a durable property test for
`ethscan.whois.extract_referral_server` (whois.py:144).

- Why: it has only example tests (`tests/test_whois.py:469+`) and NO property test.
  A prior session probed it clean (~5,010 hand-oracle cases: scheme/port/path
  stripping, `whois.iana.org` exclusion, case-insensitivity, priority-by-position)
  but added no durable test, so a regression in the referral-server heuristic would
  pass the examples.
- FIRST re-run a differential fuzz vs an INDEPENDENT hand oracle to confirm it is
  still correct (do NOT change source without a reproduced defect). Then add
  `tests/test_whois_referral_property.py` with a LOCAL oracle (do not import source
  helpers), mutation-check it (break the source, confirm the test fails, restore),
  and rerun the full gate.

## Full gate (run after the change)

`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`;
`python check_readme.py`.

## Last change (this session)

- Added `tests/test_cert_extract_subdomains_property.py` (6 tests) locking
  `ethscan.cert._extract_subdomains` (cert.py:160) against an INDEPENDENT from-scratch
  oracle: 3000 seeded random cert_data (dict/non-dict entries, name_value/common_name/
  empty/int, multiline, non-list `entries`) + 5 deterministic edge tests (case-
  insensitive dedupe+sort, multiline split, common_name fallback vs name_value
  precedence, non-dict/non-list ignored, empty/missing -> `[]`). No `ethscan/` source
  changed (verified correct, not a defect).

## Verified this session (evidence)

- Differential fuzz before tests: 30,000 cases, 0 mismatches.
- Mutation checks (caught; source restored): remove `.lower()` -> 3 fail; remove
  `sorted()` -> 3 fail.
- `python -m pytest tests/test_cert_extract_subdomains_property.py -q` -> 6 passed.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50077 passed,
  147 skipped, 0 failed; TOTAL 100% (16292 stmts, 6178 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success (287 files).
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift.
- `git status` -> only `tests/test_cert_extract_subdomains_property.py` untracked;
  `git diff --check` clean; nothing committed.

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional —
  out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do
  not change to game coverage.
- redis `_parse_info`/`_parse_config`, osdetect matchers, and
  `cert._extract_subdomains` are now property-tested — do not re-probe unchanged.
- Do not modify `.github/workflows/**`.
- Do NOT fabricate work, repeat verification-only sessions as progress, or make
  empty/control-marker commits.

## Environment / critical notes

- **Test deps are NOT preinstalled.** Run
  `pip install --quiet pytest mypy ruff coverage dnspython` first (installs to
  `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` preinstalled;
  `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.8 min (50077 tests). Do not commit manually; the
  workflow controller stages and commits.
- Always re-verify HEAD first-hand rather than trusting the handoff's "green" claim —
  prior handoffs were repeatedly stale.