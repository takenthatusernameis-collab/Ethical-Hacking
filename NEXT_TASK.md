# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5871 passed, 53 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- HEAD baseline before this session's uncommitted edits: `398c8d0` (working tree now uncommitted; do not commit unless asked)

## This session (closed gap)
- The timeout-option sweep in `tests/test_cli.py` filtered on `param.name == "timeout"`, silently skipping two sibling `FloatRange(min=0.001)` options: `subtake --http-timeout` and `cve --service-timeout`. Replaced the name filter with a bound-driven sweep (`_float_range_option_pairs()` walks every `FloatRange` option with `min == 0.001`), added a tripwire test, extended the usage-error/single-line tests to the pairs, and added two "valid value still accepted" tests. No source behavior change (Click already enforced; verified).

## Candidate work (only if demonstrated)
- Re-scan `ethscan/cli.py` for bounded numeric option types (`IntRange`, `FloatRange`) not covered by a permanent sweep. Independently re-verified this session: cli.py declares exactly 58 `IntRange` options and 45 `FloatRange(min=0.001)` options, matching `INT_OPTION_RANGES`/`INT_OPTION_UPPER_BAD` and `_float_range_option_pairs()`; all have `clamp=False`. None are unbounded above, so no upper-bound sweep is needed.
- If you find a real uncovered bounded option or a range-checked option that can perform work before rejection without a tripwire test, add the smallest permanent guard/test.
- Do not duplicate transport/body/JSON parsing coverage.

## Constraints
- Preserve baseline; smallest reversible change.
- After 5 consecutive failures from the same root cause/approach, choose a materially different evidence-based approach or stop with a handoff.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

(End of file - total 22 lines)