# Handoff

## Session (Fri Nov 27 2026, check_readme.py portability fix)

- Prior handoff said "None pending; do not fabricate work." Rather than repeat another
  verification-only session (explicitly warned against), I reproduced the one concrete
  defect the prior handoff had flagged as low-value/optional and fixed it.
- Defect: `check_readme.py` line 14 ran `subprocess.run(['python', ...])` using bare
  `python`. On systems where only `python3` exists (common on modern Linux/macOS) the
  documented `python3 check_readme.py` gate crashes with `FileNotFoundError: 'python'`.
- Fix (smallest safe change): `import sys`; run `[sys.executable, '-m', 'ethscan', '--help']`.

## What changed
- `check_readme.py`: use `sys.executable` instead of bare `python` (2-line change).
- Docs only: this handoff and `NEXT_TASK.md`. No source/test changes beyond check_readme.py.

## What was actually verified (evidence)
- Reproduced first: `env PATH=/tmp/nopybin python3 check_readme.py` (no bare `python` on
  PATH) -> `FileNotFoundError: 'python'`, exit 1.
- After fix, same no-`python` env -> `54 commands found`, `In README but not CLI: set()`,
  `In CLI but not README: set()`, exit 0.
- Normal env `python3 check_readme.py` -> exit 0, 0 drift.
- `python -m ruff check check_readme.py` -> All checks passed.
- `python -m mypy check_readme.py` -> Success: no issues found in 1 source file.
- `python -m pytest tests/test_readme_sync.py tests/test_readme_examples.py -q` -> 45 passed.
- (Full gate not re-run: it was green and unchanged at 49964/147/0; this change touches only
  the standalone check_readme.py, not ethscan/ or tests/.)

## Blockers
- None.

## Approaches already tried / ruled out (do not repeat blindly)
- Verification-only sessions: prior two sessions were green re-verifications. Do NOT run the
  full suite again as "progress" — it is green and unchanged.
- README empty-target list accuracy: COMPLETE (41 commands, test-locked).
- `cidr`/`validate` IPv6 `/127`, `oracle`/`postgresql` empty-target, `ethscan/cli.py`
  unreachable guard: intentional documented divergences. Do not modify.
- `.github/workflows/**`: do not modify.
- `oracle_verify_*.py` scripts: standalone, not wired into suite by design; not a defect.

## Next task
- None pending. Repository green; do NOT fabricate work or make empty/control-marker commits.
- If future work is genuinely needed, FIRST reproduce a concrete gap (focused failing check,
  fresh-install failure, or behavioral evidence vs documented contract), then apply the
  smallest safe fix and rerun the focused check, then the full gate:
  `python -m coverage run --branch --source=ethscan -m pytest -q`;
  `python -m mypy ethscan/ tests/`;
  `python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.
- Env note: `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.