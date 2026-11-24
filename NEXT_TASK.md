## Next task

None pending. Repository verified fully green this session:

- `python -m pytest -q` -> 47448 passed, 150 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 270 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 commands, 0 drift both directions
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 100%, 0 missing

Two bounded defects were found and fixed this session:
- Removed unused import `get_all_ports` from `ethscan/validate.py` (ruff F401).
- Documented missing `--profile [fast|normal|full]` on the README `validate` bullet (README drift caught by `test_readme_documents_every_cli_option`).

No source or test behavior changes were made beyond those fixes; no speculative changes introduced. Working tree has uncommitted changes (ethscan/validate.py + README.md) — not committed (controller commits).

If future work is needed: reproduce a concrete gap first (focused failing check, behavioral evidence vs documented contract, or reproduced crash), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), and preserve safety/validation. Do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error). `ethscan/cli.py:4318` unreachable defensive guard is a documented known limitation, left unchanged.

(End of file)
