## Next task

None pending. Repository verified fully green at the start of this session and left green after one bounded hygiene fix:

- Fixed `ethscan/dns.py`: removed 7 malformed duplicated `# noqa: BLE001  # noqa: BLE001` comments (lines 63, 86, 113, 161, 165, 184, 186); now each reads `# noqa: BLE001 - resolver can raise any type`. Pure comment hygiene; no behavior/lint/coverage change.

Baseline verification (this session):
- `python -m pytest -q` -> 47428 passed, 147 skipped, 0 failed
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 270 source files
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `python check_readme.py` -> 54 commands, 0 drift both directions
- Full branch coverage -> TOTAL 100% statements and branches, 0 missing across all 61 ethscan modules
- `git diff --check` -> clean; working tree contains only the `ethscan/dns.py` edit

Known out-of-scope limitations (unchanged):
- `oracle`/`postgresql` empty-target handling remains intentionally in-band (exit 0, in-band error) per their documented contract.
- `ethscan/cli.py` unreachable defensive guard in the `completion` command (documented; do not game coverage or weaken validation).
- `ethscan/radix.py` / `ethscan/cidr.py` `# type: ignore[attr-defined]` on `typing.NotRequired` imports is accurate for the project's `>=3.10` floor; left intact.

If future work is needed: reproduce a concrete gap first (focused failing check, behavioral evidence vs documented contract, or reproduced crash), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), and preserve safety/validation. Do not speculate or weaken safety controls.