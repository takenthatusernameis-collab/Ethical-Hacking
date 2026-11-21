# Next Task

## Status: none pending; repository verified green (this session)

A real gap was found and closed this session: fresh coverage measurement (not the stale `coverage.json`) showed `ethscan/scanner.py` at 99% due to one uncovered branch — `grab_banner`'s `if data:` false path after an empty HTTP HEAD response (`scanner.py:86->92`). Added `test_grab_banner_http_head_empty_data_returns_none` to `tests/test_scanner_service_detect.py` following the existing `_FakeSock` pattern.

## Verification (fresh evidence, this session)
- `python -m pytest tests/test_scanner_service_detect.py -q` -> 15 passed (+1 new).
- `python -m coverage run --branch --source=ethscan -m pytest -q` + `python -m coverage report --fail-under=100` -> **100%** (16081 stmts, 0 miss, 6072 branches, 0 partial).
- `python -m mypy ethscan/ tests/` -> clean; `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed; `python check_readme.py` -> 54 commands, 0 drift.
- Working tree: only `tests/test_scanner_service_detect.py` modified (uncommitted).

## Do not re-implement / do not "fix" (already done / intended)
- Coverage gap above — closed; do not add speculative guards to `scanner.py`.
- `ethscan/cli.py:4336` unreachable defensive guard (`raise click.UsageError("Shell argument is required...")`) — leave; making it reachable is a speculative behavior change.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- Do not count control-marker-only (handoff-doc) commits as progress; this session's change is a real, verified coverage fix.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once and `coverage report --fail-under=100`; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work.
3. If no gap exists, the correct outcome is the tree left as-is (with this one verified test change committed by the controller) plus an honest "verified green, no gap" handoff.

(End of file)
