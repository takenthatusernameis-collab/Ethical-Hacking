# Next Task
Date: Mon Nov 16 2026

## Status
- Repository green and warning-free: `python -m pytest -q` -> **32147 passed, 146 skipped, 0 failed, 0 warnings**.
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 258 source files.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python3 check_readme.py` -> 54 CLI commands, 0 drift.
- Branch coverage: `ethscan/s3.py` at **100% / 0 BrPart**; overall `ethscan/` partial branches **18**.

## What changed this session
- Executed the assigned `ethscan/s3.py:check_bucket_public` audit. The prior agent's fix was
  already committed (`024ddcd`) but left two new `else` branches untested (`s3.py:298`,
  `:315`), dropping s3 to 99%/2 BrPart.
- Added 2 regression tests in `tests/test_s3_branch_gaps.py` (test-only, no source edits):
  - `test_check_bucket_public_unexpected_direct_status` (`297->298`, status 418).
  - `test_check_bucket_public_http_error_unexpected_status` (`314->315`, HTTPError 418).
- Result: s3 back to 100%/0 BrPart; ethscan partial branches 20 -> 18.

## What remains unresolved
- 18 partial branches remain; all statically unreachable (per-arc evidence in
  `HANDOFF_NEXT.md`). No known functional defect reproduced.
- Open question (not a defect): `check_bucket_public` treats any 2xx as `exists=True` and
  only `200` as `public`; a 204/206 is "exists but private". Distinguishable from 404 via
  `exists`, so not the previously hypothesized defect. Do not change without a concrete
  scenario.

## Approaches already tried / ruled out
- Chasing remaining BrParts: all unreachable; do not add speculative tests or weaken code.
- Blanket `-W error` suite gate: two pre-existing unrelated unraisable-exception warnings
  fail under it; standard gate is plain `pytest -q` (0 warnings).
- `oracle`/`postgresql` empty-target handling intentionally out of scope (exit 0, in-band).

## Next task
- Coverage/typing is saturated; do not add branch tests for their own sake.
- Perform one focused functional audit with a concrete reproducer. Candidate:
  `ethscan/fuzz.py` finding classification. `run_fuzz` treats every result with
  `status_code is not None and status_code != 404` as a finding (`ethscan/fuzz.py:157-158`;
  CSV `is_finding` at `:228-229`), so **500/401/403/429** are reported as findings (possible
  false positives). Reproduce with a fake `urlopen`/`HTTPError` returning 500 and 403,
  inspect JSON/CSV, and decide whether non-404 statuses should be findings, errors, or a
  separate class. If a defect: smallest fix + regression test + README. Constraints:
  concrete scenario, no speculation, no weakened safety controls, reversible change.
- Alternative if fuzz is intended-by-design: audit `ethscan/web.py` header/status handling
  (`ethscan/web.py:172-188`).

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches are gitignored; the controller (`kilo-controller.sh`) stages and commits
  source/test/handoff files automatically.