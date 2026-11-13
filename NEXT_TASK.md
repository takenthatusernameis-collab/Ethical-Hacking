# Next Task

## Status
Previous handoff task completed: added permanent formatter hostile-sweep coverage for `ping` (coverage-only; formatters already defensive). Baseline at start of this session was fully green (8479 passed, 149 skipped, 0 failed; mypy/ruff clean; check_readme 54/54).

## This session
- Reproduced formatter behavior first (probe-only): 0 crashes for non-mapping top-level and hostile nested ping payloads (`probes`/`notes`/`target`/`host`/`ip`/`count`/`raw_socket_available`/`port`/`rtt` fields) across json/markdown/csv formatters.
- No production fix required.
- Added `tests/test_ping_formatter_hostile_sweep.py` with hostile top-level/nested cases and a well-formed regression.

## Verification
- `python -m pytest tests/test_ping_formatter_hostile_sweep.py -q` → 75 passed.
- `python -m pytest -q` (full suite) → 8554 passed, 149 skipped, 1 warning (pre-existing `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`; +75 vs baseline).
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 215 source files.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Next task
- None pending. Repository is fully green. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first (e.g. probe and add formatter hostile-sweep coverage for one remaining single-arg formatter module lacking a dedicated `*_formatter_hostile_sweep.py`, such as `fuzz` or `nmap`) — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).