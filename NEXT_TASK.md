## Next task

None pending. Repository verified fully green after completing bounded coverage improvement task:

- `python -m pytest tests/test_brute.py tests/test_ssl.py` -> All 96 tests passed
- `python -m pytest tests/test_brute.py --cov=ethscan.brute` -> 100% coverage (was 96%)
- `python -m pytest tests/test_ssl.py --cov=ethscan.ssl` -> 100% coverage (was 98%)
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 270 source files
- `python -m ruff check ethscan/ tests/` -> All checks passed
- `python3 check_readme.py` -> 54 commands, 0 drift both directions

If future work is needed: reproduce a concrete gap first (focused failing check, behavioral evidence vs documented contract, or reproduced crash), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), and preserve safety/validation. Do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope.