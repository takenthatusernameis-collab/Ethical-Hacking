# Next task

None pending. Repository fully green with 100% coverage (49954 passed, 147 skipped, 0 failed; mypy/ruff clean; README 54/54, 0 drift; coverage TOTAL 100%). Do NOT fabricate work or repeat verification-only sessions as progress. If future work is needed, reproduce a concrete gap first (focused failing check, fresh-install failure, or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then the full gate (pytest/coverage/mypy/ruff/check_readme), preserve safety.

Evidence-based lead (fresh angle, not yet done): grep `tests/` for no-op assertions on security-relevant pure helpers (e.g. `isinstance(result, int)` / `0 <= result <= 0xFFFF` that never check a real value) and strengthen them the same way the `_checksum` tests were strengthened this session. Do not change production code without a reproduced defect.

`oracle`/`postgresql` empty-target handling and `ethscan/cli.py` unreachable guard remain intentionally out of scope. Do not modify `.github/workflows/**`.