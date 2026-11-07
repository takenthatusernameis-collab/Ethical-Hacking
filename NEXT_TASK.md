# Next Task
File-before-target-validation audit complete across all commands; no reproducible gap found, no fix required.

## Baseline (verified this session)
- All `--target`+`file` commands validate the target before reading the file (see HANDOFF_NEXT.md for line references).
- No-target candidates (`nmap`, `radix`, `audit`, `hash`, `jwt`) have no target to validate, so no target-before-file gap is possible there.
- Reproductions: `stale`/`brute` exit 2 with target error before file read; `nmap`/`radix` exit 2 on file path only.
- `python3 -m pytest tests/test_stale.py tests/test_cli.py -q -k stale` → 66 passed.
- `python3 -m ruff check ethscan/cli.py` → clean; `python3 -m mypy ethscan/cli.py` → Success.

## Constraints
- Do not re-sweep the already-verified target-before-file pattern.
- Any future claimed gap must be reproduced before changing code; verify with targeted pytest + ruff + mypy; update TASK.md/NEXT_TASK.md/HANDOFF_NEXT.md; do not commit unless asked.
