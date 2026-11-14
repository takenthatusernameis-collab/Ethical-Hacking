# Next Task

## Status
Session 173 (Sat Nov 14 2026): closed branch arc `307->320` in `ethscan/web.py` (`if not_after:` False path).
- Added `tests/test_web.py::test_check_ssl_cert_missing_not_after`.
- `ethscan/web.py` branch coverage improved (arc `307->320` closed; remaining partials: `421->420, 443->445, 445->447, 447->449, 449->451, 464, 479->482, 483->487, 493`, miss `388`).

## Baseline (verified this session)
- `python3 -m pytest -q` → 31976 passed, 146 skipped, 0 failed.
- `python3 -m pytest tests/test_web.py --cov=ethscan.web --cov-branch` → 81 passed, 97% branch on `ethscan/web.py`.
- `python3 -m mypy ethscan/ tests/` → Success: no issues found in 236 source files.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.
- `tests/test_web.py` changes are uncommitted (no commit without explicit request).

## Approaches already tried / ruled out
- Missing-`notAfter` assertions must reflect initialized defaults (`days_remaining`/`valid` keys exist); do not assert key absence.
- Per-module branch-arc closure is the right bounded granularity.
- `oracle`/`postgresql` empty-target handling intentionally out of scope per documented contract.

## Next task
- Close the next reachable branch arc(s) in `ethscan/web.py`. Reproduce: `python3 -m pytest tests/test_web.py --cov=ethscan.web --cov-branch --cov-report=term-missing -q` and inspect code around the reported partials (`421->420, 443->445, 445->447, 447->449, 449->451, 464, 479->482, 483->487, 493`) and miss `388`. Add minimal tests in `tests/test_web.py` for the simplest reachable case(s), then run focused coverage and full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/`, `check_readme.py`). If an arc is unreachable via public helper/CLI contract, document evidence and move to the next module instead of contrived tests.
