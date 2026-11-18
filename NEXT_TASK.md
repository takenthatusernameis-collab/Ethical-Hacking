# Next Task
Date: Wed Nov 18 2026

## Status
- Baseline re-verified and improved this session:
  - `python -m pytest -q` -> 32603 passed, 146 skipped, 0 failed.
  - `python -m mypy ethscan/ tests/` -> Success, no issues in 260 source files.
  - `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
  - `python check_readme.py` -> 54 commands, 0 drift both directions.
  - Coverage: `completion.py` 100%; TOTAL 99% (sole gap = `cli.py:4318` unreachable defensive guard).
  - Working tree modified: `ethscan/completion.py`, `tests/test_completion_hostile_sweep.py` (markdown raw-`message` join fix + regression test).

## What this session did (for context)
- Fixed a real formatter crash: `ethscan/completion.py::format_install_report_markdown` joined a raw `result.get("message", "")` into `"\n".join(...)`, raising `TypeError` for any non-string `message` (None/int/list/dict/bool/bytes). Wrapped it in an f-string to match the five sibling fields. Valid-input output is byte-identical.
- Added `test_install_report_formatters_never_raise_on_hostile_fields` in `tests/test_completion_hostile_sweep.py`.
- Evidence: a 163-formatter x 19,379-call hostile fuzzer found this as the ONLY genuine crash family; after the fix it reports 0 crashes.

## Known limitation (intentionally left open)
- `ethscan/cli.py:4318` defensive `UsageError("Shell argument is required when not using --install")` in the non-install completion path is unreachable via CLI (positional `SHELL` defaults to `"bash"` and is choice-validated). It is the sole coverage gap (99% branch). Covered conceptually by invariant reasoning; do not add `# pragma: no cover`, delete the guard, or make the shell required without explicit task/evidence.

## Next task
- None pending from current evidence. If future work is needed, select one bounded, verifiable improvement: reproduce a concrete gap first (failing check/test or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then relevant broader gates, and preserve safety/validation.
- Optional durable follow-up (NOT done this session; proven safe by a 7,840-call probe): add the install field names (`message`, `shell`, `script_path`, `rc_file`, `installed`, `already_installed`) to `_VALID_REPORT` in `tests/test_all_formatters_hostile_contract.py` so the generic contract sweep also covers them. Rejected this session only to keep the change bounded (it adds ~7,840 parametrized cases).
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error) per documented contract.

## Constraints / notes
- Keep architecture stable; do not weaken safety/validation or permissions. Do not commit unless explicitly asked.
- `rg` (ripgrep) is not installed; use the Grep tool or `grep`. Reconcile any uncommitted changes (`ethscan/completion.py`, `tests/test_completion_hostile_sweep.py`) before starting new work.