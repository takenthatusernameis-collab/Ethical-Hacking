# Next task

None pending. Repository fully green with 100% coverage (50017 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- None. Independently re-verified the true baseline first-hand (the prior HANDOFF_NEXT.md was stale: its two listed "leads NOT yet done" — `wifi._parse_proc_net_wireless` and `mac._is_mac_address` property tests — are already committed at HEAD `bece502`, along with `tests/test_scanner_port_range_property.py`). No source or test changes made; no reproducible defect found.

## Verified this session (evidence)

- `python -m pytest -q` -> 50017 passed, 147 skipped, 0 failed (verified at HEAD `bece502`, unchanged since HEAD `2d3ad9f`, docs-only vs `bece502`)
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 100% (16292 stmts, 6178 branches, 0 missing)
- `python -m mypy ethscan/ tests/` -> Success: no issues in 282 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python3 check_readme.py` -> 54 CLI commands, 0 drift both directions; exit 0
- `git status` -> clean working tree; HEAD `2d3ad9f` (docs-only vs `bece502`, no source/test change, not counted as progress)

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- All documented leads are done or probed clean; do not re-probe unchanged.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.75 min (50017 tests). Do not commit manually; the workflow controller stages and commits.
