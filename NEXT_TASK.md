# Next Task

## Status: no pending task; repo green after a one-line lint fix (uncommitted).

## What this session did
- Reproduced a real lint regression the prior handoff missed: `tests/test_scanner.py` had an unused `grab_banner` import (re-added by HEAD commit `0e00780`, previously removed by `50e5ae0`).
- Fix: removed the unused import (single-line deletion; tests reference `scanner_mod.grab_banner`).

## Verification (fresh evidence, this session)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 268 source files.
- `python -m pytest -q` -> **46784 passed, 147 skipped, 0 failed**.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.

## Real work on HEAD (do not re-implement)
- `ethscan.target.format_host_header()` brackets bare IPv6 literals in HTTP `Host` headers; wired into `scanner.grab_banner` and `service.grab_banner`. Tests in `tests/test_target.py`, `tests/test_scanner.py`, `tests/test_service.py`.

## Do not re-implement / do not "fix" (already done / intended)
- `ethscan/cli.py:4318` unreachable defensive guard — documented known limitation; leave it.
- `oracle`/`postgresql` empty-target handling — intentionally in-band (exit 0); out of scope.
- PBKDF2+NTLM intentionally unsupported.
- All remaining `AF_INET` occurrences are `getaddrinfo` hints or IPv4-only raw ICMP; not bugs.

## Next session guidance
1. Verify HEAD hash and handoff claims against `git log`/`git status` before trusting stale docs.
2. Run fast gates first: `ruff`, `mypy ethscan/ tests/`, `check_readme.py`. If green, run `python -m pytest -q` once.
3. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work or repeat verification-only sessions. If probing turns up nothing, leave the baseline intact and record the findings.

(End of file)