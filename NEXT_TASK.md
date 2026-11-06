# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Repeated the evidence-driven scan of CLI validation/error-handling paths and manually probed offline/CLI-boundary edge cases (`scan --target ''|--ports ''|--timeout 0|--workers 0|--ports 99999|--out /etc`, `hash --iterations 0|-5`, `cidr --cidr ''`, `radix --cidrs ''`, `validate --ports ''|--cidr ''|--cidr not-a-cidr|--ports 99999`, `completion --shell bogus`, `jwt --token ''`, `config --init /unwritable`). No new demonstrated gap; no code change.

## Candidate work (only if demonstrated)
- Add smallest permanent guard/test only with a reproducible case (option/callback reaches side effects before clean rejection).
- Do not duplicate existing sweeps or intentional in-output reporting semantics (`--contains` invalid IP → `in_network:false`; `hash --check`/`validate` structured error fields).

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
