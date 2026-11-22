# Next Task

## Status: no pending task; repo fully green with fresh evidence.

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 268 source files.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- `python -m pytest -q` -> **46771 passed, 147 skipped, 0 failed**.
- HEAD: `f615b0b` (main). Working tree clean.

## Next task
- None pending. Repository is fully green.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0) per documented contract; out of scope.
- PBKDF2+NTLM intentionally unsupported.
- All remaining `AF_INET` occurrences are `getaddrinfo` name-resolution hints or IPv4-only raw ICMP; not bugs.

## Next session guidance
1. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once; if green, proceed.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work. Do not repeat verification-only sessions. If probing turns up nothing, leave the baseline intact and record the findings.
