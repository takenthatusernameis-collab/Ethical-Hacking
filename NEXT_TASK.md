## Next task

None pending. Repository is fully green on click 8.1.8 with 100%
statement/branch coverage.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- Defensive unreachable guards (do not weaken safety or game coverage)

Next: if future work is needed, reproduce a concrete gap first
(fresh-install failure, focused failing check, or behavioral evidence vs
documented contract), apply the smallest safe fix, rerun focused then broader
gates (pytest/coverage/mypy/ruff/check_readme), preserve safety.
