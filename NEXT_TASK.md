# Next Task

## Task
None pending. Repository is fully green:
- `python -m pytest -q` → 5957 passed, 50 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` → clean, 187 source files.
- `python -m ruff check ethscan/ tests/` → all checks passed.

## Scope
The typing-hygiene drive and the empty-target normalization drive are both complete.
- `oracle` and `postgresql` are intentionally left unchanged (in-band error, exit 0) per their documented contract — do not change unless a task explicitly asks.
- Last session fixed the 2 ruff errors (`S110` + `BLE001`) in `ethscan/s3.py:312` (blind `except Exception: pass` on `exc.close()`) via the established `# noqa: BLE001, S110` convention; no behavior change, baseline unchanged.

## Candidates
None from the existing backlog (all stale error counts reproduced as 0). If future work is needed, pick a single high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls.

## Verification
- `python -m pytest -q` → 5957 passed, 50 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` → clean on changed files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
