# Next Task

## Status
Sun Nov 15 2026: smb partial-branch task resolved. Measured `ethscan/smb.py` at 5 (not 6) partial branches with `pytest tests/test_smb*.py` + branch coverage, then closed all 5 with focused tests in `tests/test_smb_branch_gaps.py`. `ethscan/smb.py` is now 100% statement and 100% branch (156/156). Repo fully green.

## Baseline / verification this session
- `python -m pytest -q` → 32057 passed, 146 skipped, 0 failed (1 preexisting warning: `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m mypy ethscan/ tests/` → Success: no issues found in 239 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.
- Full-suite branch coverage: `ethscan/smb.py` 489 stmts, 0 miss, 156 branch, 0 BrPart (100%); `ethscan/` statement coverage still 0 missing.

## What changed
- Added `tests/test_smb_branch_gaps.py` (5 tests) closing the 5 reachable partial branches:
  - `340->343` (SMB1 `security_mode` without USER bit)
  - `360->363` (SMB1 data blob < 8 bytes → no challenge)
  - `416->418` (`_build_banner` with no challenge)
  - `754->761` (`run_smb2` with both signing bits clear)
  - `902->901` (Markdown formatter with a non-dict negotiate-context entry in a counted list)
- No production-code changes; test-only, fully reversible.

## What remains unresolved
- None for smb. All 5 partial branches are genuinely reachable (unlike smtp's defensive arcs) and are now covered by tests.

## Approaches already tried / ruled out
- Reusing the existing hostile-sweep `SMB2_HOSTILE` case (line 129 of `test_smb_hostile_sweep.py`) does NOT cover `902->901` because that dict omits `negotiate_context_count`, so the context loop is never entered. A dedicated test that sets `negotiate_context_count` with a non-dict entry is required.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Next task
- Continue one module per session by partial-branch count (reproduce each with branch coverage first; do not batch modules; classify reachable vs unreachable before editing tests).
- Highest remaining `ethscan/` partial-branch counts (from full-suite branch coverage): `ntp` 6, then `netbios` 5, `subdomains` 5, `ldap`/`mongodb`/`nmap`/`snmp`/`vuln` 4 each. (`smtp` 5 is already documented unreachable — do not re-attempt.)
- Precise next task: reproduce `ethscan/ntp.py` partial branches `61->74, 63->74, 68->74, 245->243, 393->400, 473->499` with `pytest tests/test_ntp.py tests/test_ntp_hostile_sweep.py` + branch coverage, then either add focused tests for reachable arcs or document unreachable ones with evidence.