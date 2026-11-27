# Next task

None pending. Repository fully green with 100% coverage (49975 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- None. Baseline re-verified first-hand (all gates green); no source or test changes made. Working tree clean.

## Verified this session (evidence)

- `python -m pytest -q` -> 49975 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 279 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions; exit 0
- `git status` -> clean working tree

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation.
- Do not modify `.github/workflows/**`.
- `geo`/`urlcheck` vs `urllib.parse` oracle: already property-tested — do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

No fresh-angle lead remains in the handoff lists. `oracle`/`postgresql` empty-target handling and `ethscan/cli.py` unreachable guard remain intentionally out of scope.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Do not commit manually; the workflow controller stages and commits.
