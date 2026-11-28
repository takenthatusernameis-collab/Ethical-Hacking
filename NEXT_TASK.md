# Next task

One precise, evidence-based, NOT-yet-done lead: add a durable property test for
`ethscan.validate._ports_to_ranges` (validate.py:357).

- Why: it is a pure helper with non-trivial logic (int-coercion with `""`
  fallback on `TypeError`/`ValueError`, sort, consecutive-run collapsing into
  `start-end`, single ports, `", "` join). It has ONLY example tests
  (`tests/test_validate.py:437-458, 686-687, 799-802`) and NO property test
  (there is no `tests/test_validate_property.py`). A regression in the run
  collapsing or the non-numeric fallback would pass the examples.
- FIRST re-run a differential fuzz vs an INDEPENDENT hand oracle to confirm it
  is still correct (do NOT change source without a reproduced defect). Then add
  `tests/test_validate_ports_to_ranges_property.py` with a LOCAL oracle (do not
  import source helpers), mutation-check it (break the source, confirm the test
  fails, restore), and rerun the full gate.

## Full gate (run after the change)

`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`;
`python check_readme.py`.

## Last change (this session)

- The prior handoff's "next task" (add `tests/test_whois_referral_property.py`)
  was ALREADY DONE in HEAD (commits 19003f0/6775678) — stale handoff again.
  The committed test worked but its `oracle` carried DEAD code (a `candidates`
  /`finditer` block computed then never used; the live logic was `cand2`) and
  omitted the documented empty-value-no-cross-line behaviour.
- Improved `tests/test_whois_referral_property.py` in place (test-only; NO
  `ethscan/` source changed): removed the dead oracle code, replaced the oracle
  with a clean from-scratch recomputation, widened the random generator
  (2000 -> 5000 richer cases: empty same-line values, `\r\n`/`\n`, scheme/port/
  path/query/fragment forms, mixed case, iana with/without port), and added
  deterministic tests for empty-value-no-cross-line, no-match, and fragment
  stripping. Strict superset of the prior coverage (7 tests vs 6).

## Verified this session (evidence)

- Differential fuzz BEFORE editing: 50,000 random cases vs an independent
  oracle -> 0 mismatches (function correct; source untouched).
- Baseline HEAD test re-run first-hand: 6 passed (stale-handoff check).
- Mutation checks (each caught; source restored, `git diff ethscan/whois.py`
  empty): remove final `.lower()` -> 2 fail; remove `rstrip(".")` -> 2 fail;
  remove iana exclusion -> 2 fail; remove scheme strip -> 3 fail; remove path
  strip -> 2 fail; pattern-priority sort instead of position -> 2 fail.
- `python -m pytest tests/test_whois_referral_property.py -q` -> 7 passed.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50084 passed,
  147 skipped, 0 failed; TOTAL 100% (16292 stmts, 6178 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success (288 files).
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift.
- `git status` -> only `tests/test_whois_referral_property.py` modified;
  `git diff --check` clean; nothing committed.

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional —
  out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do
  not change to game coverage.
- redis `_parse_info`/`_parse_config`, osdetect matchers, `cert._extract_subdomains`,
  and `whois.extract_referral_server` are now property-tested — do not re-probe
  unchanged.
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
- Full coverage gate takes ~2.9 min (50084 tests). Do not commit manually; the
  workflow controller stages and commits.
- Always re-verify HEAD first-hand rather than trusting the handoff's "green" claim —
  prior handoffs were repeatedly stale.