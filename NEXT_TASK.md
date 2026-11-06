# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Scanned `click.Path`/file-input validation (all 20 `exists` inputs covered by `FILE_OPTIONS`; group `--config` covered; `--out` guarded by `_write_output`; JSON/XML/UTF-8 content covered). No new demonstrated gap; no code change.

## Candidate work (only if demonstrated)
- Add smallest permanent guard/test only with a reproducible case (option/callback reaches side effects before clean rejection).
- Do not duplicate existing sweeps (Choice, IntRange/FloatRange, ports, CIDR, host, offline-input, `FILE_OPTIONS`, JSON/XML content, `--out`, `--config`).

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.
