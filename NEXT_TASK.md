# Next Task for Agent

## Status
- Working tree on main (HEAD 207cce6, local only; ahead of origin/main by a4a0d04).
- Working tree has UNSTAGED changes: 113 `,cover` deletions + `.gitignore` edit (`git diff --stat`: 114 files, 1 insertion, 91,594 deletions). Not committed.
- Tests: 3906 passed, 1 skipped (green baseline).
- Repository: 57 source files compile clean; 53 CLI commands register; `python -m ethscan --help`/`--version` OK.
- Lint: 44 ruff errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — intentional/unsafe to fix per constraints; unchanged.

## Constraints (do not touch)
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402).
- Preserve baseline; avoid speculative refactors touching those lint exceptions.
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests.
- Only remove provably-dead code if definitive proof exists.

## Current state of fixes
- Cover-file cleanup completed this session (not committed). See HANDOFF_NEXT.md for full details.
- vuln.py E303 regression fixed in a4a0d04 (collapsed 3 blank lines before `_SEVERITY_RANK` to 2). Verified with `ruff check --select E303 --preview ethscan/vuln.py` -> clean.
- Pre-existing E303 too-many-blank-lines sites remain (e.g. ethscan/cli.py:3600, ethscan/validate.py:279 and others); not regressions, left untouched.

## Next precise task
- Commit the pending working-tree changes (113 `,cover` deletions + `.gitignore` edit) if desired, then re-verify: `python -m pytest -q` (expect 3906 passed, 1 skipped) and `python -m ruff check ethscan tests` (expect 44 errors unchanged).
- Otherwise await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan). Do not invent an assignment; nothing meeting the bar currently exists.

## Verification checklist (if selecting a task)
1. Reproduce the smallest failure when applicable; verify prerequisites.
2. Run relevant focused tests.
3. Run full suite: `python -m pytest -q` (must remain green; expect 3906 passed, 1 skipped).
4. Run lint: `python -m ruff check ethscan tests` (should report 44 errors unchanged).
5. Confirm `python -m py_compile ethscan/*.py` passes and no unintended changes via `git diff --stat`.
6. Do not claim checks passed without evidence.

(End of file)
