# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_main.py` (3 errors -> 0):
- Added `from typing import Any, cast`.
- `cli_mod.cli = cast(Any, counting_cli)` at lines 96 and 126 (assigning a plain function to `cli`, typed as `_TargetGroup`/`click.Group`).
- `cast(ast.Constant, comparator).value` at line 155 (narrow `ast.expr` before reading `.value`).

Verified: `mypy tests/test_main.py` clean; `ruff check tests/test_main.py` clean; `pytest tests/test_main.py` → 14 passed; `mypy ethscan/ tests/test_main.py` clean (60 source files); `pytest -q --ignore=tests/test_ping.py` → 5875 passed, 53 skipped, 0 failed (baseline unchanged).

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene across remaining test files (repo-wide `python -m mypy ethscan/ tests/` still reports pre-existing errors). Reproduce each target with `python -m mypy tests/<file>` first, fix per file using the established pattern (TypedDict/Mapping in source where indexing `dict[str, object]` results is the issue; test-only annotations/casts otherwise). Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` blocker). Do not speculate or weaken safety controls. Do not assume prior handoff error counts are current; reproduce per file first.
