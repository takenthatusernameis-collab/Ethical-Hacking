# Next Task

## Status: none pending; repository independently re-verified green (this session)

This session re-verified the green state with FRESH coverage measurement (not the stale committed `coverage.json`). No new code work was required or fabricated.

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python -m mypy ethscan/ tests/` -> clean (268 files; only informational `--check-untyped-defs` notes).
- `python check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m coverage erase && coverage run --branch --source=ethscan -m pytest -q` + `coverage report --fail-under=100` -> **100%** (16081 stmts, 0 miss; 6072 branches, 0 partial). Tests: **46759 passed, 146 skipped, 0 failed**.
- `python -c "import ethscan"` -> ok; `python -m ethscan --help` -> CLI works.
- `git status --short` -> clean; working tree clean at HEAD `8c22cba` (code state matches `97149dd`; `8c22cba`/`83ad669` are control-marker handoff commits).

## Do not re-implement / do not "fix" (already done / intended)
- Coverage gap in `scanner.py` — closed and committed; do not add speculative guards.
- `ethscan/cli.py:4318` unreachable defensive guard — leave; making it reachable is a speculative behavior change.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- Do not count control-marker-only (handoff-doc) commits as project progress.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once and `coverage report --fail-under=100`; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work.
3. If no gap exists, the correct outcome is the tree left clean plus an honest "verified green, no gap" handoff.

(End of file)
