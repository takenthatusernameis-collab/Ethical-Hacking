# Next Task
Full suite is green; no unresolved issues remain.

## Baseline (verified this session)
- `completion` default emits the raw shell script (sourceable; `bash -n` ok); structured report only with explicit `--output-format`/`--format`. `--out` writes raw by default or the requested report.
- `config --out <file>` writes the loaded config report to the file (new regression coverage).
- Full suite: `python -m pytest -q` → 5920 passed, 50 skipped.
- Targeted: `tests/test_completion.py tests/test_cli.py tests/test_cli_offline_input_sweep.py` → pass.
- `ruff check tests/test_cli.py` → clean; `mypy tests/test_cli.py` → no new errors (12 pre-existing on the clean tree).

## Constraints
- If starting new work: pick one bounded, high-value correctness/robustness task verifiable in-session. Reproduce any claimed gap before changing code. Do not re-audit the file-before-target-validation pattern or the completion default-output contract. Do not commit unless asked. Update TASK.md/NEXT_TASK.md/HANDOFF_NEXT.md.
