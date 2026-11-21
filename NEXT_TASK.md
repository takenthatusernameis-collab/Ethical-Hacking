# Next Task
Date: Sat Nov 21 2026

## Status
- Green: **46729 passed, 146 skipped, 0 failed**; mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean.
- Coverage gate now enforced: `coverage report --fail-under=100 --include='ethscan/*'` -> 100% (ethscan/ 16024 statements, 0 missed).
- Working tree has UNCOMMITTED changes from this session (ethscan/cli.py, pyproject.toml, HANDOFF_NEXT.md, NEXT_TASK.md).

## This session (what changed)
- **Task: enforce ethscan/ statement coverage as a gate so coverage regressions fail verification.**
  - Added `# pragma: no cover` to the intentional unreached defensive guard at ethscan/cli.py:4274.
  - Added `[tool.coverage]` to pyproject.toml: fail_under = 100, source = ["ethscan"], exclude_lines = ["pragma: no cover"].
  - Verified gate passes: ethscan/ TOTAL 16024 statements, 0 missed, 100% coverage.
  - No behavior change; purely a verification/durability improvement, fully reversible.

## Verification
- `python -m pytest -q` -> 46729 passed, 146 skipped, 0 failed.
- `python -m coverage report --fail-under=100 --include='ethscan/*'` -> 100% (gate passes; would fail on any future uncovered ethscan line).
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54/54, 0 drift both directions.
- `git diff --check` -> clean.

## Candidate next task (for the next agent)
- Run the full gate suite to confirm steady state is still green.
- If explicitly asked, commit this session's verified coverage-gate changes (ethscan/cli.py, pyproject.toml) plus the handoff files.
- Otherwise select a new bounded durability task only if a genuine gap is demonstrated; the repo is at a steady state with all gates green and 100% ethscan/ coverage. Do not fabricate work.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.
