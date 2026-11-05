# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5872 passed, 53 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- HEAD (committed): `dc23229`; working tree has uncommitted local changes (do not commit unless asked)

## This session (fixed)
- Fixed a deterministic test-helper defect in `tests/test_cli.py`: `_assert_config_usage_error` prepended `--` unconditionally, so config cases passing `--workers`/`--timeout`/etc. asserted against `----...` while the CLI correctly emitted single-dash-prefixed flags. Normalized the flag idempotently. CLI/config behavior unchanged (verified by reproduction).

## Candidate work (only if demonstrated)
- Re-scan `ethscan/cli.py` for bounded numeric option types (`IntRange`, `FloatRange`) not covered by a permanent sweep. Re-verified this session: 58 `IntRange` options and 45 `FloatRange(min=0.001)` options, matching `INT_OPTION_RANGES`/`INT_OPTION_UPPER_BAD` and `_float_range_option_pairs()`; all `clamp=False`. No unbounded-above `FloatRange(min=0.001)` options found.
- If you find a real uncovered bounded option or a range-checked option that can perform work before rejection without a tripwire test, add the smallest permanent guard/test.
- Do not duplicate transport/body/JSON parsing coverage.

## Constraints
- Preserve baseline; smallest reversible change.
- After 5 consecutive failures from the same root cause/approach, choose a materially different evidence-based approach or stop with a handoff.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

(End of file - total 24 lines)
