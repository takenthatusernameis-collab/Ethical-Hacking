# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5872 passed, 53 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- HEAD (committed): `dc23229`; working tree has uncommitted local changes (do not commit unless asked)

## This session
- Re-scanned `ethscan/cli.py`: 58 `IntRange` + 45 `FloatRange(min=0.001)`; no additional bounded Range types. Counts match permanent sweeps; no demonstrated gap found. No code changes.

## Candidate work (only if demonstrated)
- If a real uncovered bounded option or a range-checked option that can perform work before rejection without a tripwire test is found, add the smallest permanent guard/test.
- Do not duplicate transport/body/JSON parsing coverage.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
(End of file)