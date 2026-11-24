## Next task

Repository is green (re-verified this session):
- `pytest -q` -> 47460 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> clean (270 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> all checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- `coverage run -m pytest` + `coverage report` -> 100%, exit 0

This session fixed an inert coverage gate: `pyproject.toml` had `fail_under`,
`source`, and `exclude_lines` under `[tool.coverage]`, which coverage.py ignores
(it only reads `[tool.coverage.run]` / `[tool.coverage.report]`). Moved them to
the correct subsections, added the standard `if TYPE_CHECKING:` exclusion for two
statically-unreachable imports (cidr.py:18, radix.py:17), and declared
`coverage>=7.0` in dev extras. The 100% gate is now genuinely enforced (verified:
fails at 99% before the exclusion, passes at 100% after).

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py:4318` unreachable defensive guard (documented known limitation)

Next: optionally wire coverage into CI (`.github/workflows/main.yml`) via
`python -m coverage run -m pytest -q && python -m coverage report`, so the now-real
100% gate is enforced on every run. Keep it minimal; do not change source/test
behavior. Reproduce any future gap concretely before fixing.

(End of file)