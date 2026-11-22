# Next Task

## Status: none pending; repository verified green this session (fresh evidence)

This session ran the full fast-gate + test verification and confirmed everything is green. No changes were made; no gap was found to fix. Working tree left clean at HEAD `9daf1ca`.

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python -m mypy ethscan/ tests/` -> clean (268 source files; only informational `--check-untyped-defs` notes).
- `python check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m pytest -q` -> **46767 passed, 147 skipped, 0 failed**.
- `git status --short` -> clean working tree.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py` unreachable defensive guard — leave; making it reachable is a speculative behavior change.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once and (optionally) `coverage report --fail-under=100`; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work.
3. If no gap exists, the correct outcome is the tree left clean plus an honest "verified green, no gap" handoff.
