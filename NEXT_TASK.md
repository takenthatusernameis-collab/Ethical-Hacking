## Next task

None pending. Repository verified fully green at the start of this session and left green after inspection-only work (no changes made):

- `python -m mypy ethscan/ tests/` -> Success: no issues found in 270 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 commands, 0 drift both directions

If future work is needed: reproduce a concrete gap first (focused failing check, behavioral evidence vs documented contract, or reproduced crash), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), and preserve safety/validation. Do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope.
