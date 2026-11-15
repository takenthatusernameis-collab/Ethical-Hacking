# Next Task

## Status
Sun Nov 15 2026 (session): closed branch gaps in `ethscan/service.py` (100% statement + branch coverage).
- Extracted `_port_key` to module level for direct, behavior-preserving coverage of defensive fallbacks.
- Added formatter and `_port_key` tests in `tests/test_service.py`.

## Baseline (verified this session)
- `python3 -m pytest tests/test_service.py --cov=ethscan.service --cov-branch --cov-report=term-missing -q` → 42 passed, 100%.
- `python3 -m pytest -q` → 32012 passed, 146 skipped, 1 warning, 0 failed.
- `python3 -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- `ethscan/hash.py` arc `589->596`: requires a list/tuple subclass whose `__bool__` is True when empty; not a valid public-contract input. Do not retry.

## Next task
- Close remaining branch gaps in `ethscan/radix.py` (`315->313`, `359->361`).
  - Reproduce: `python3 -m pytest tests/test_radix.py --cov=ethscan.radix --cov-branch --cov-report=term-missing -q`.
  - Add minimal targeted tests in `tests/test_radix.py`.
  - Run full gate: `python3 -m pytest -q`, `python3 -m mypy ethscan/`, `python3 -m ruff check ethscan/ tests/`, `python3 check_readme.py`.
