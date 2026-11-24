## Next task

Repository is green (re-verified this session):
- `pytest -q` -> 47464 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> clean (270 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> all checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- `coverage run -m pytest` + `coverage report` -> 100%, exit 0

This session added `tests/test_coverage_config_gate.py`: a deterministic guard
that fails if the 100% coverage gate ever reverts to the inert top-level
`[tool.coverage]` form. It reads coverage's *resolved* config via
`coverage debug config` and asserts `source` includes `ethscan`, `fail_under`
is 100, and the `if TYPE_CHECKING:` exclusion is present. Verified meaningful:
the inert config resolves to `source: None` / `fail_under: 0.0` and is
rejected; the real config is accepted.

Important: the previous handoff's "wire coverage into CI via main.yml" task is
NOT persistable. The controller reverts `.github/workflows/**` before every
checkpoint and excludes it from staging, so agent workflow edits are discarded.
Do not attempt it.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py:4318` unreachable defensive guard (documented known limitation)

Next: pick a bounded, persistable improvement in `ethscan/` or `tests/` (NOT
`.github/workflows/**`). Concrete candidate: audit a pure-logic module
(`cidr.py`, `mac.py`, `jwt.py`, `radix.py`) for a reproducible edge case that is
mis-handled, reproduce with a failing test first, then apply the smallest fix.
Reproduce any gap concretely before fixing; do not delete tests to go green.

(End of file)