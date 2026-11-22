# Handoff
Date: Sun Nov 22 2026

## State
- HEAD: `0e00780` (main). Working tree: clean except one uncommitted fix (see below).
- The previous handoff (HEAD `0c4014a`) was stale: commits `e40fda8`, `50e5ae0`, `0e00780` landed AFTER it and did real feature work, and `0e00780` re-introduced a lint failure the earlier handoff had already fixed. That regression is now fixed (uncommitted; controller stages/commits).

## What changed this session
- `tests/test_scanner.py`: removed the unused `grab_banner` import (was dead — tests reference `scanner_mod.grab_banner`, not the direct name). This is the same line commit `50e5ae0` removed, which `0e00780` re-added. Single-line deletion; no behavior change.

## Real work already on HEAD (context for reviewers)
- `e40fda8`: added `ethscan.target.format_host_header()` (brackets bare IPv6 literals per RFC 3986 3.2.2 / RFC 7230 5.4); wired it into `scanner.grab_banner` and `service.grab_banner` HTTP `Host` headers. Covered by `tests/test_target.py` (`test_format_host_header_*`), `tests/test_scanner.py` (`test_grab_banner_http_ipv{6,4}_host_header_*`), `tests/test_service.py`.

## What was actually verified this session (fresh evidence)
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python -m mypy ethscan/ tests/` -> Success: no issues in 268 source files.
- `python -m pytest -q` -> **46784 passed, 147 skipped, 0 failed** (101s).
- Targeted re-run `tests/test_scanner.py tests/test_service.py tests/test_target.py` -> 359 passed, 1 skipped.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- `git diff --check` -> clean.

## What remains unresolved
- Nothing functional. Known limitations unchanged (documented, intentional):
  - `ethscan/cli.py:4318` unreachable defensive guard (leave it; do not game coverage or remove validation).
  - `oracle`/`postgresql` empty-target exit-0 in-band contract (intentional, out of scope).
  - PBKDF2+NTLM intentionally unsupported.

## Approaches already failed / why
- No failed line of work this session. The only issue was a stale handoff plus one lint regression, both resolved by reproducing (ruff) and removing the dead import.

## Next task
- None pending; repository is green after the uncommitted one-line fix.
- Next session: run fast gates first (`ruff`, `mypy ethscan/ tests/`, `check_readme.py`); if green run `python -m pytest -q` once. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; do not repeat verification-only sessions. Verify HEAD/handoff hashes against reality before trusting stale handoff claims.

## Environment/notes
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.4 via `python -m coverage`.
- Do not commit manually unless explicitly asked; the workflow controller stages and commits.

(End of file)