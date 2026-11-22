# Next Task

## Status: no pending task; repo green.

## What this session did
- Verified HEAD hash against `git log`/`git status`: HEAD `3b3a763` == origin/main; working tree clean. Prior handoff's claimed HEAD `0e00780` is stale and does not exist in this repo.
- Ran fast gates: `ruff` passed, `mypy ethscan/ tests/` passed (269 source files), `check_readme.py` passed (54 commands, 0 drift).
- Ran `python -m pytest -q`: **47393 passed, 147 skipped, 0 failed**.
- No changes made; no genuine gap reproduced.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0); out of scope.
- PBKDF2+NTLM intentionally unsupported.

## Next session guidance
1. Verify HEAD hash and handoff claims against `git log`/`git status` before trusting stale docs.
2. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once.
3. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work or repeat verification-only sessions. If probing turns up nothing, leave the baseline intact and record the findings.
