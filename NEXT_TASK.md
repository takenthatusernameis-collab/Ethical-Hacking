# Next Task for Agent

## Status
- Working tree on main (HEAD pending commit of radix fix; local only)
- Working tree: CLEAN
- Tests: 3908 passed, 1 skipped (green baseline)
- Compilation: 57 source files compile clean via `python -m py_compile ethscan/*.py`
- CLI: `python -m ethscan --help` / `--version` OK
- Lint: 48 ruff errors (33 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py, 1 S110 in ethscan/cve.py:350) — intentional/unsafe to fix per constraints; unchanged

## Constraints (do not touch)
- Do not modify code to "fix" the 48 documented ruff errors (BLE001/TRY002/PLR0402/S110)
- Preserve baseline; avoid speculative refactors touching those lint exceptions
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests
- Only fix genuine bugs with definitive proof and a failing test; only remove provably-dead code with definitive proof
- Do not delete user data, disable validation, or weaken safety controls
- Do not count control-marker-only commits as project progress

## Completed work (reference)
- 19777ff: `,cover` artifact cleanup
- c6b6fc2: web.py dead-duplicate strptime removal (1 line); verified tests/lint/compile unchanged (3906/1 skip, 48 errors)
- 5cba856: ssl.py dead-duplicate strptime removal (1 line); verified tests/lint/compile unchanged (3906/1 skip, 48 errors)
- bd662ea: mac.py `run_mac` DEFAULT_API_URL state leak fixed (try/finally); added failing-test repro `tests/test_mac.py::test_run_mac_unresolvable_restores_default_api_url`; verified 3907 passed/1 skipped, 48 errors unchanged, all compile clean
- (pending) radix.py `format_radix_report_csv` host-bits-set crash fixed (`strict=False`); added `tests/test_radix.py::test_format_radix_report_csv_host_bits_set`; verified 3908 passed/1 skipped, 48 errors unchanged, all compile clean

## What remains
- No pending assigned task. No prior handoff work remains unexecuted.
- Pre-existing E303 too-many-blank-lines sites (not regressions): ethscan/cli.py:3600, ethscan/validate.py:279, ethscan/cidr.py:255-256, others
- Documented coverage gaps (environmental/defensive, not closable within constraints): cli.py:4864 __main__ guard; dnssec.py dnspython fallback; hash.py MD4/NTLM/PBKDF2 paths; radix.py defensive edges; network-dependent modules require live services

## Recommended next precise task
- Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan). **Nothing meeting this bar currently exists.**
- If a task is selected, it must have definitive proof (e.g. failing test that reproduces the issue) and be bounded and behavior-preserving where applicable.

## Verification checklist (if you select a task)
1. Reproduce the smallest failure when applicable; verify prerequisites
2. Write/add a failing test that demonstrates the issue (required for bug fixes)
3. Implement the smallest reversible fix
4. Verify focused tests related to change
5. Run full suite: `python -m pytest -q` (must remain green; expect 3908 passed, 1 skipped)
6. Run lint: `python -m ruff check ethscan tests` (should report 48 errors unchanged)
7. Confirm `python -m py_compile ethscan/*.py` passes
8. Confirm `git diff --stat` shows only intended changes; working tree clean
9. Do not claim checks passed without evidence
10. Update HANDOFF_NEXT.md and TASK.md with concrete details (what changed, verified with evidence, unresolved, failed approaches if any, next precise task)

## Evidence
- Current state verified: 3908 passed, 1 skipped; ruff reports 48 errors (unchanged); all files compile clean; working tree clean. The radix CSV host-bits-set crash is fixed with proof (failing test added).

(End of file - total 47 lines)