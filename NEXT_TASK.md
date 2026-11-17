# Next Task
Date: Tue Nov 17 2026

## Status
- Full baseline verified green this session: pytest 32220 passed, 146 skipped; mypy (default and `--check-untyped-defs`) clean on `ethscan/` and `tests/`; ruff clean; `check_readme.py` reports 54 commands in sync (exit 0); coverage 100% (15661 stmts / 5918 branches).
- No uncommitted source changes beyond prior `check_readme.py` fix; handoff/task docs updated.

## Next task
1. Reproduce and select one bounded, high-value, evidence-backed improvement if present (concrete bug, missing verification for documented behavior, or deterministic tooling gap). Implement smallest reversible fix and verify with focused checks plus relevant gates.
2. If no evidenced gap is found after inspection, document what was checked and leave the baseline intact.

## Constraints / notes
- Keep architecture stable; do not weaken safety/validation. Do not commit unless explicitly asked.
- `oracle`/`postgresql` empty-target handling intentionally out of scope (exit 0, in-band error).
- Dev deps: Python 3.14.4, pytest 9.2.0, mypy 2.4.1, ruff 0.17.5. No pytest-cov plugin.
