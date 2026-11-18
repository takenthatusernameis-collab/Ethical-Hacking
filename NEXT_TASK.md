# Next Task
Date: Wed Nov 18 2026

## Status
- Baseline re-verified and improved this session:
  - `python -m pytest -q` -> 39323 passed, 146 skipped, 0 failed (was 32603; +6720 new parametrized cases).
  - `python -m mypy ethscan/ tests/` -> Success, no issues in 260 source files.
  - `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
  - `python check_readme.py` -> 54 commands, 0 drift both directions.
  - Coverage: `completion.py` 100%; TOTAL 99% (sole gap = `cli.py:4318` unreachable defensive guard).

## What this session did (for context)
- Executed the bounded, evidence-based optional follow-up recorded in the prior handoff: extended the generic repo-wide contract sweep to cover the install report formatters.
- `tests/test_all_formatters_hostile_contract.py` (+10 lines): added the six install report field names (`shell`, `script_path`, `rc_file`, `installed`, `already_installed`, `message`) to the `_VALID_REPORT` fixture, with a comment explaining why. This makes `test_formatter_survives_hostile_report_field` exercise those fields against every single-argument formatter, including the three install formatters (`format_install_report_{json,markdown,csv}`).
- New parametrized cases: 160 single-arg formatters x 6 new fields x 7 hostile values = 6,720 cases (the contract file went from 25,762 to 32,482 collected tests; full suite 32,603 -> 39,323). All pass; 0 crashes.

## Known limitation (intentionally left open)
- `ethscan/cli.py:4318` defensive `UsageError("Shell argument is required when not using --install")` in the non-install completion path is unreachable via CLI (positional `SHELL` defaults to `"bash"` and is choice-validated). It is the sole coverage gap (99% branch). Covered conceptually by invariant reasoning; do not add `# pragma: no cover`, delete the guard, or make the shell required without explicit task/evidence.

## Next task
- None pending from current evidence. If future work is needed, select one bounded, verifiable improvement: reproduce a concrete gap first (failing check/test or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then relevant broader gates, and preserve safety/validation.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error) per documented contract.

## Constraints / notes
- Keep architecture stable; do not weaken safety/validation or permissions. Do not commit unless explicitly asked.
- `rg` (ripgrep) is not installed; use the Grep tool or `grep`. Working tree has this session's one-file change (`tests/test_all_formatters_hostile_contract.py`).

(End of file - total 28 lines)