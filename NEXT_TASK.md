# Next Task
No demonstrated gap remains for the osdetect/vuln/cve file-before-target-validation sweep.

## Baseline (verified)
- Full suite: `5907 passed, 50 skipped` (Python 3.14/OpenSSL 3.5.5; one unrelated flaky brute unreachable-sweep test passes in isolation).
- `python3 -m ruff check .` → all checks passed. `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## This session (fixed, verified)
- `osdetect`, `vuln`, `cve` now validate `--target` via `_validate_enum_target()` before reading any user-supplied file. Invalid targets rejected as usage errors (exit 2) before file I/O; valid flows unchanged. 5 new CLI tests. Targeted suites 1333 passed; full suite green apart from an unrelated flaky brute test.

## Candidate work
- None demonstrated. Stop here unless a new side-effect-before-validation gap is reproduced in a materially different area.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then relevant broader suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
