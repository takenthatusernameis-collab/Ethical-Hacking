# Next Task

## Candidate (bounded, verify before coding)
Audit `ethscan/cli.py` for any command output path that writes to a user-supplied file (`--out` or similar) **without** using `_write_output`/`write_text` in a way that violates the README contract (invalid/unusable option values → Click usage error, exit 2; no raw tracebacks). Focus only on paths not already covered by existing `--out` directory/error tests.

**How to proceed**
1. For each suspicious site, reproduce with a concrete command (e.g., `--out /tmp` where `/tmp` is a directory, or another unwritable target the test environment can demonstrate safely).
2. If the reproduced behavior is already exit 2 / `Invalid value for '--out'` (or correct for the option), record evidence and do **not** change code.
3. If it leaks a traceback or exits non-2 for an unusable path, apply the smallest fix consistent with `_write_output`/existing patterns and add CLI regression coverage.

## Do not
- Do not re-audit file-before-target-validation or the completion default-output contract.
- Do not re-audit `config --out` / `config --init` (covered).
- Do not make speculative changes without a reproduced gap.
- Do not commit unless explicitly asked.

## Baseline (verified this session)
- `python -m pytest -q` → **5921 passed, 50 skipped**.
- `ruff check ethscan/cli.py tests/test_cli.py tests/test_config.py` → clean.

## Handoff requirements
Update `TASK.md`, `NEXT_TASK.md`, and `HANDOFF_NEXT.md` with what changed, what was verified (commands + outcomes), unresolved items, failed approaches/evidence, and one precise next task.
