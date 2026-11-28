# Next task

None pending. Repository fully green with 100% coverage (50033 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift; coverage TOTAL 100%). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- Added `tests/test_redis_resp_property.py` (test-only, no production change): property tests locking `redis._parse_resp` (RESP response parser for untrusted network bytes) against an independent from-scratch encoder — round-trip, exact prefix consumption, truncation-incompleteness, malformed inputs, known vectors, `_build_resp_array` round-trip. 16 cases, seed 20261128.
- Verified correct via a 20,000-case differential fuzz BEFORE writing tests (0 mismatches); mutation-checked (3 source mutations each caught; source restored).

## Verified this session (evidence)

- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50033 passed, 147 skipped, 0 failed (baseline 50017; +16 new tests); TOTAL 100% (16292 stmts, 6178 branches, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 283 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 commands, 0 drift both directions
- `git status` -> only new `tests/test_redis_resp_property.py` (untracked); `git diff --check` clean

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- `redis._parse_resp` is verified correct and now property-tested — do not re-probe unchanged or "fix" it.
- All documented leads are done or probed clean; do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

- Evidence-based lead NOT yet done: property-check `redis._parse_info` / `redis._parse_config` (parse `key:value` / `key value` lines from an INFO/CONFIG response; only example tests) vs an independent line oracle, or `osdetect._match_os_from_ttl` / `_match_os_from_banner` vs a hand oracle. Revisit only with a NEW angle.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.75 min (50033 tests). Do not commit manually; the workflow controller stages and commits.