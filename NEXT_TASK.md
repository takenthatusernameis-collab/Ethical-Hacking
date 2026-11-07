# Next Task
Run the full test suite and confirm no regressions from the completion default-output fix.

## Baseline (verified this session)
- `completion` default now emits the raw shell script (sourceable; `bash -n` ok); structured report only with explicit `--output-format`/`--format`. `--out` writes raw by default or the requested report.
- Targeted: `python -m pytest tests/test_completion.py tests/test_cli.py -q` → 1103 passed; `tests/test_completion.py` → 46 passed.
- `ruff check ethscan/cli.py ethscan/completion.py tests/test_completion.py tests/test_cli.py` → clean; `mypy ethscan/cli.py ethscan/completion.py` → Success.
- Full baseline at session start: 5910 passed, 50 skipped (not rerun after this change).

## Constraints
- Run `python -m pytest -q` (full suite). If any failure appears, reproduce it, make the smallest evidence-based fix, and re-verify with targeted tests + ruff + mypy before/alongside the full run.
- If full suite is green, pick one bounded, high-value correctness/robustness task verifiable in-session (reproduce before changing code). Do not re-audit the file-before-target-validation pattern (already verified). Do not commit unless asked. Update TASK.md/NEXT_TASK.md/HANDOFF_NEXT.md.
