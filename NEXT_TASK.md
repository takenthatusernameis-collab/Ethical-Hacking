# Next task

None pending. Repository green (README gate now robust; full gate was green at 49964
passed / 147 skipped / 0 failed, mypy clean over 278 files, ruff clean, README 0 drift,
coverage 100% as of the prior session). Do NOT fabricate work, repeat verification-only
sessions as progress, or make empty/control-marker commits.

## Last change (this session)
- Fixed a concrete, reproduced portability defect in `check_readme.py`: it shelled out to
  bare `python` (line 14) instead of `sys.executable`. On systems where only `python3`
  exists (common on modern Linux/macOS) the documented `python3 check_readme.py` gate
  crashed with `FileNotFoundError: 'python'`.
- Fix: import `sys`; run `[sys.executable, '-m', 'ethscan', '--help']`.

## Verified this session (evidence)
- Reproduced the failure first: `env PATH=/tmp/nopybin python3 check_readme.py` (no bare
  `python` on PATH) -> `FileNotFoundError: 'python'`, exit 1.
- After fix, same no-`python` env -> `54 commands found`, `0 drift` both directions, exit 0.
- Normal env `python3 check_readme.py` -> exit 0, 0 drift.
- `python -m ruff check check_readme.py` -> All checks passed.
- `python -m mypy check_readme.py` -> Success: no issues found.
- `python -m pytest tests/test_readme_sync.py tests/test_readme_examples.py -q` -> 45 passed.

## Constraints / do-not-touch
- `cidr`/`validate` IPv6 `/127`, `oracle`/`postgresql` empty-target handling, and the
  `ethscan/cli.py` unreachable guard remain intentional documented divergences — do not modify.
- Do not modify `.github/workflows/**`.
- `oracle_verify_*.py` scripts are standalone (not wired into the suite by design); not a defect.

## If future work is genuinely needed
FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral
evidence vs documented contract), then apply the smallest safe fix, rerun the focused check,
then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

Env note: `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.