# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5869 passed, 53 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- HEAD baseline before this session's uncommitted edits: `c9f228c` (working tree now uncommitted; do not commit unless asked)

## This session (closed gap)
- 24 CLI port options (`click.IntRange(0, 65535)`) were missing from `tests/test_cli.py` `INT_OPTION_RANGES`/`INT_OPTION_UPPER_BAD`. Added them; existing sweep tests now cover lower/upper bounds and clean usage errors. No source behavior change (Click already enforced; verified with `--port 65536`/`-1` and no-probe check).

## Candidate work (only if demonstrated)
- Re-scan `ethscan/cli.py` for `click.IntRange`/bounded numeric options not present in `INT_OPTION_RANGES` — none found in this session. Do not add speculative tests.
- If you find a real uncovered bounded option or a range-checked option that can perform work before rejection without a tripwire test, add the smallest permanent guard/test.
- Do not duplicate transport/body/JSON parsing coverage.

## Constraints
- Preserve baseline; smallest reversible change.
- After 5 consecutive failures from the same root cause/approach, choose a materially different evidence-based approach or stop with a handoff.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.
