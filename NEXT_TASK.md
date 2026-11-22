# Next Task

## Status: none pending; repository verified green this session (fresh evidence)

This session ran the full fast-gate + test + coverage verification and confirmed everything is green. No changes were made; no gap was found to fix. Working tree left clean at HEAD `e6ac484`.

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python -m mypy ethscan/ tests/` -> clean (268 files; only informational `--check-untyped-defs` notes).
- `python check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m pytest -q` -> **46767 passed, 147 skipped, 0 failed**.
- `python -m coverage erase && python -m coverage run --branch --source=ethscan -m pytest -q` + `coverage report --fail-under=100` -> **100%** (16117 stmts, 0 miss; 6080 branches, 0 partial).
- `git status --short` -> clean working tree.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py` unreachable defensive guard — leave; making it reachable is a speculative behavior change.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once and `coverage report --fail-under=100`; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work.
3. If no gap exists, the correct outcome is the tree left clean plus an honest "verified green, no gap" handoff.

(End of file)
