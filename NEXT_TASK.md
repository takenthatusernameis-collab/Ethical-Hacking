# Next Task

## Status
Session complete (Sat Nov 14 2026, session 166): added `tests/test_readme_sync.py`, a permanent regression guard keeping the README command list in sync with the CLI.
- Parses README command bullets with the same regex as `check_readme.py` and compares against `ethscan.cli.cli.commands` programmatically.
- Three tests: every CLI command is documented; README has no unknown commands; a parser-sanity guard so the check can't become vacuous.
- No production code changed; purely a test addition, fully reversible.

## Baseline (verified this session)
- Environment: dev deps were NOT preinstalled. `python -m pip install -e ".[dev,dns]"` is required first.
- `python -m pytest tests/test_readme_sync.py -q` → 3 passed.
- `python -m pytest -q` → 31930 passed, 146 skipped, 1 warning, 0 failed (baseline was 31927; +3 new tests).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 236 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Verification of the guard itself (negative test)
- Deleting the entire `wifi` command bullet from README made 2 tests fail (missing `wifi`; count 53 vs 54). README restored, diff clean. The guard catches the realistic drift (missing/renamed bullet). A suffix appended to `command` is not caught (regex lacks a word boundary) — accepted, not an observed drift mode.

## Blockers
- None.

## Approaches already tried / ruled out
- Option-by-option README vs `--help` comparison: too brittle/slow for a permanent test. Command-presence only.
- Do not trust handoff numbers without re-running; this checkout ships without pytest/mypy/ruff.

## Next task
- None pending. Repository is fully green (31930 passed, 146 skipped, 0 failed). `oracle` and `postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error). If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls.