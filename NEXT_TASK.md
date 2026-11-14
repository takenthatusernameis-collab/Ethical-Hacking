# Next Task

## Status
Session 174 (Sat Nov 14 2026): closed reachable branch arcs in `ethscan/ftp.py` target normalization and connection-failure handling.
- Added `tests/test_ftp.py::test_normalize_target_bracket_host_nondigit_port_suffix`
- Added `tests/test_ftp.py::test_normalize_target_host_nondigit_port_suffix`
- Added `tests/test_ftp.py::test_run_ftp_connector_failure_leaves_client_unset`
- `ethscan/ftp.py` branch coverage improved (62 branches, 2 partial remaining: `46->59`, `216->220`).
- Prior queued task (`ethscan/web.py` arcs in old handoff) was stale: focused check shows `ethscan/web.py` 100% branch coverage (`python3 -m pytest tests/test_web.py --cov=ethscan.web --cov-branch -q`).

## Baseline (verified this session)
- `python3 -m pytest -q` → 31986 passed, 146 skipped, 0 failed.
- `python3 -m pytest tests/test_ftp.py tests/test_ftp_hostile_sweep.py --cov=ethscan.ftp --cov-branch -q` → 85 passed, 99% branch on `ethscan/ftp.py` (missing/partial: `46->59, 216->220`).
- `python3 -m pytest tests/test_web.py --cov=ethscan.web --cov-branch -q` → 88 passed, 100% branch on `ethscan/web.py`.
- `python3 -m mypy ethscan/ tests/` → Success: no issues found in 236 source files.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.
- `tests/test_ftp.py` changes are uncommitted (no commit without explicit request).

## Approaches already tried / ruled out
- `ethscan/ftp.py` `46->59`: exercised `[]:21` (empty bracket host, `bracket_end <= 0`) via `_normalize_target` raising `TargetSpecError`; branch path taken but coverage still reports partial arc — investigate exact condition/arc semantics before adding contrived cases.
- `ethscan/ftp.py` `216->220`: exercised `client is None` at `finally` by making connector raise before assignment (caught and returned inside try/finally); arc remains partial — likely needs complementary path exercising `client is not None` close suppression in same coverage context or is structurally hard; do not add contrived production changes.
- `oracle`/`postgresql` empty-target handling intentionally out of scope per documented contract.

## Next task
- Pick the next highest-value small branch-coverage gap outside `web.py` (already 100%). Suggested: inspect `ethscan/hash.py` partial `589->596` or `ethscan/mssql.py` `226->230` via `python3 -m pytest --cov=ethscan --cov-branch --cov-report=term-missing -q` and targeted module tests. Reproduce the specific arc, add a minimal public-contract test if reachable, then run focused module coverage and full gate (`pytest -q`, `mypy ethscan/ tests/`, `ruff check ethscan/ tests/`, `check_readme.py`). If an arc is not reachable without contrivance, document evidence and move to the next module.
