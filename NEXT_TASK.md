# Next Task
Search for a demonstrated file-before-target-validation (or side-effect-before-validation) gap in a materially different area than the solved enumeration sweeps.

## Baseline (verified this session)
- Focused: `66 passed` for stale-related tests (`tests/test_stale.py tests/test_cli.py -k stale`).
- `python3 -m ruff check ethscan/cli.py tests/test_cli.py` → all checks passed.
- `python3 -m mypy ethscan/cli.py` → Success.
- Prior full-suite baseline per HANDOFF_NEXT.md: 5909 passed, 50 skipped (re-run full suite only if broader risk is indicated).

## This session (fixed, verified)
- `stale` CLI now validates explicit `--target` values with `_validate_enum_target()` before reading `--file` via `load_domains_from_file()`. Prevents file read side effect / content distraction when an explicit target is unusable. 1 new CLI regression test.

## Candidate work
- Audit commands with user-supplied file inputs for concrete reproducible gaps: file read happens before validation of another required/meaningful input whose failure should be reported first (usage error, exit 2) — but only fix if demonstrated. Quick check candidates: `nmap` has only `--input-file` (no target ordering issue); `radix`/`cidr` validate before compute; `config`/`validate` have specific contracts. Reproduce before changing.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then relevant broader checks, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
