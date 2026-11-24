## Next task

None pending. Repository is fully green on click 8.1.8 with 100% statement/branch coverage.

This session (fix-only; one additive helper in `ethscan/snmp.py`; working tree now clean after commit):
- Fixed the `NameError` crash introduced by commit 86adec1: `_parse_oid`
  referenced `_split_first_subidentifier`, which that commit never defined.
  Added the missing helper (standard ASN.1 BER first-arc split rule).
- `python -m pytest -q` → 47449 passed, 150 skipped, 0 failed (the 21 SNMP
  failures from the prior broken commit are all resolved).
- `python -m mypy ethscan/snmp.py` → Success: no issues found.
- `python -m ruff check ethscan/snmp.py` → All checks passed.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py:4318` unreachable defensive guard (do not weaken safety or game coverage)

Next: if future work is needed, reproduce a concrete gap first (fresh-install failure, focused failing check, or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), preserve safety.