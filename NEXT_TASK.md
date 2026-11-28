# Next task

None pending. Repository is fully green.

## Last completed session (Sat Nov 28 2026)

Added a durable property test for `ethscan.validate._ports_to_ranges`
(validate.py:357): new file `tests/test_validate_ports_to_ranges_property.py`
with a local stdlib-only oracle, a 30,000-case random property test, and
deterministic edge-case tests. Verified correctness first via a 200,000-case
differential fuzz vs an independent oracle (0 mismatches, so no source change
was warranted) and mutation-checked the test (both source mutations caught).

## Full gate (all green)

- `python -m pytest -q` → 50097 passed, 147 skipped, 0 failed
- `python -m coverage run --branch --source=ethscan -m pytest -q` → 50097
  passed; `ethscan/validate.py` 100% (268 stmts, 118 branches, 0 missing)
- `python -m mypy ethscan/ tests/` → Success: no issues in 289 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed
- `python check_readme.py` → 54 CLI commands, 0 drift both directions

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is
  intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known
  limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- Do NOT fabricate work, repeat verification-only sessions as progress, or
  make empty/control-marker commits.

## Environment / critical notes

- **Test deps are NOT preinstalled in this environment.** Run:
  `pip install --quiet pytest mypy ruff coverage dnspython` (installs to
  `~/.local/bin`, not on PATH; use `python -m <tool>`). `click`/`pyyaml` are
  preinstalled; `dnspython` is not.
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
  `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.9 min (50097 tests). Do not commit manually; the
  workflow controller stages and commits.
- ALWAYS re-verify HEAD first-hand (install deps, run the gate) rather than
  trusting the "green" claim — prior handoffs were repeatedly stale.
