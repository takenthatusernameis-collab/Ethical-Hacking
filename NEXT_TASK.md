# Next task

None pending. Repository fully green with 100% coverage (50065 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift; coverage TOTAL 100%). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- Added `tests/test_vuln_version_range_property.py` (test-only, no production change): property/differential tests locking `vuln.version_in_range` (the security-critical CVE version-range comparison behind `SERVICE_VULNS` / `cve._lookup_cve_id`) against an INDEPENDENT from-scratch oracle — random specs, every real DB entry, numeric zero-padding, non-numeric rejection, over-long-component rejection, and 10 boundary/inclusivity vectors. 15 cases, seed 20261128.
- Fixed a real lint blocker at HEAD: `tests/test_redis_info_config_property.py:115` raised inside `except ValueError` without `from` (ruff B904, enforced via `select = ["B"]`). Changed to `raise ... from None`. No `ethscan/` source changed.
- Verified `version_in_range` correct via a 1,400,000-case differential fuzz BEFORE writing tests (0 mismatches); mutation-checked (3 source mutations each caught; source restored).

## Verified this session (evidence)

- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 50065 passed, 147 skipped, 0 failed (baseline 50050; +15 new tests); TOTAL 100% (16292 stmts, 6178 branches, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 286 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 commands, 0 drift both directions
- `git status` -> modified `tests/test_redis_info_config_property.py` (B904 fix) + new `tests/test_vuln_version_range_property.py` (untracked); `git diff --check` clean

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- `vuln.version_in_range` / `_version_tuple` / `_pad_versions` are verified correct and now property-tested — do not re-probe unchanged or "fix" them.
- All documented leads are done or probed clean; do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

- Evidence-based lead NOT yet done (revisit only with a NEW angle): property-check a still-untested security parser such as `hash` identification ordering, `netbios` name encode/decode, or `dns`/`dnssec` name decompression vs an independent byte oracle.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.8 min (50065 tests). Do not commit manually; the workflow controller stages and commits.
- NOTE: the previous handoff was stale (3 commits behind); always re-verify HEAD first-hand rather than trusting the handoff's "green" claim.