## Next task

None pending. Repository is fully green (re-verified this session):
- `pytest -q` -> 47460 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> clean (270 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> all checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- working tree clean; branch up to date with origin/main

This session restored test coverage the prior session had deleted: added
`test_run_jwt_non_finite_time_claim_is_not_a_timestamp` (inf/-inf/nan) asserting
non-finite exp/iat/nbf are flagged "not a number" and do not crash the Markdown
formatter. No source behavior changed.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py:4318` unreachable defensive guard (documented known limitation)

Next: if future work is needed, reproduce a concrete gap first (a weakened/deleted
test, fresh-install failure, focused failing check, or behavioral evidence vs
documented contract), apply the smallest safe fix, rerun focused then broader
gates (pytest/mypy/ruff/check_readme), preserve safety.

(End of file)