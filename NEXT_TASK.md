# Next task

None pending. Repository fully green with 100% coverage (50017 passed, 147 skipped, 0 failed; mypy/ruff clean; all 5 oracle verification scripts exit 0). Do NOT fabricate work, repeat verification-only sessions as progress, or make empty/control-marker commits.

## Last change (this session)

- None. Independently re-verified the true baseline first-hand (prior HANDOFF_NEXT.md was accurate, not stale). No source or test changes made; no reproducible defect found.
- Oracle review: `mac._is_mac_address` trailing-whitespace "mismatch" is documented intentional strictness (ethscan/mac.py:302-315), not a bug — oracle leniency is an `int()` whitespace artifact. Ruled out; no fix warranted.

## Verified this session (evidence)

- `python -m pytest -q` -> 50017 passed, 147 skipped, 0 failed (verified at HEAD `08cfaed`, unchanged since HEAD `bece502`)
- `python -m mypy ethscan/ tests/` -> Success: no issues in 282 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python oracle_verify_{target,mac,dnssec,whois,service}.py` -> all exit 0
- `git status` -> clean working tree; HEAD `08cfaed` (no source/test change vs `bece502`, not counted as progress)

## Constraints / do-not-touch

- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) is intentional — out of scope.
- `ethscan/cli.py` unreachable defensive guard is a documented known limitation — do not change to game coverage.
- Do not modify `.github/workflows/**`.
- All documented leads are done or probed clean; do not re-probe unchanged.
- `mac._is_mac_address` strict whitespace rejection is documented intent — do not relax to match the loose oracle.

## If future work is genuinely needed

FIRST reproduce a concrete gap (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), then apply the smallest safe fix, rerun the focused check, then the full gate:
`python -m coverage run --branch --source=ethscan -m pytest -q`;
`python -m mypy ethscan/ tests/`;
`python -m ruff check ethscan/ tests/ check_readme.py`; `python3 check_readme.py`.

## Environment/notes

- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.5.
- `coverage` is not on PATH; use `python -m coverage ...`. `python` works here.
- Full coverage gate takes ~2.75 min (50017 tests). Do not commit manually; the workflow controller stages and commits.
