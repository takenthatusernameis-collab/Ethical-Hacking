# Next Task
Date: Fri Nov 20 2026 — repository fully green; verification-only session (no assigned task pending).

## Status
- Green: **46710 passed, 146 skipped, 0 failed**; mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; coverage 100% of `ethscan/` modules (only documented unreachable `cli.py` guard uncovered).
- Working tree clean; nothing committed (controller commits).
- No pending assigned task: the previous UDP/IPv6 family-awareness task is already complete (verified empirically this session — all UDP + TCP modules handle `--target ::1` with no address-family errors).

## This session (what changed)
- Nothing. Verification-only: re-confirmed baseline gates green and probed for defects (IPv6 on every command; empty/invalid `--target` on all 42 usage-error commands; hostile-shape formatters; README example coverage). No defect found; no source/test changes made (refusing to manufacture a speculative change).

## Candidate next task (for the next agent — reproduce first)
- Make the target-usage-error regression guard future-proof: replace the manually-maintained `TARGET_USAGE_ERROR_COMMANDS` tuple in `tests/test_cli.py:23868` (36 commands) with auto-discovery of CLI commands that accept a `--target` Click parameter, excluding `mac`, `oracle`, `postgresql` (intentional in-band contracts — do not alter those).
- Reproduce first: enumerate top-level CLI commands with a `--target` param; confirm each non-excluded command rejects all 5 `UNUSABLE_TARGETS` ("", "   ", "://no-host", "redis://", ":6379") as exit 2 with "Could not parse host from target"; then implement, update tests, and run the full gate (pytest/mypy/ruff/check_readme/coverage).
- Constraints: keep architecture stable; no new dependencies; tests deterministic (no real network/DNS); `mac`/`oracle`/`postgresql` in-band contracts remain out of scope.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3 (installed via `python -m pip install -e ".[dev,dns]"` + `pip install coverage` this session).
