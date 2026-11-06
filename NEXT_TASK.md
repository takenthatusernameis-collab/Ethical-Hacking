# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Scanned CLI validation/error-handling (`Path` inputs/`FILE_OPTIONS`, `--config`/`--init`/`--out`, `cidr/radix` `--cidr/--cidrs/--diff/--contains`, `hash --check`, `completion`, `vuln --severity`, `scan --ports`, JWT/target/result-reporting commands). No new demonstrated gap; no code change.

## Candidate work (only if demonstrated)
- Add smallest permanent guard/test only with a reproducible case (option/callback reaches side effects before clean rejection).
- Do not duplicate existing sweeps or intentional in-output reporting semantics (`--contains` invalid IP → `in_network:false`; `hash --check`/`validate` structured error fields).

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
