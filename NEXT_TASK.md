# Next Task

No genuine pending task. Repository independently re-verified green this session:

- `pytest -q` -> 46744 passed, 146 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (267 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift
- `coverage --fail-under=100 --include='ethscan/*'` -> 100% statement/branch on every module

## Do not re-implement (already done / verified)
- ICMPv6 raw ping in `ethscan/ping.py` — fully implemented and tested at 100% branch coverage.
- All 146 skips are intentional structural skips (no input-file options, no secondary container, no string options, or sweep exclusions); none indicate a coverage gap.
- PBKDF2, NTLM, and MD4 are all supported in `ethscan/hash.py` (including a pure-Python MD4 fallback); no unsupported gap exists.

## Remaining / known limitations (intentional, out of scope — do NOT "fix" blindly)
- `oracle`/`postgresql` empty-target handling: in-band "probe failed" (exit 0) per documented contract (README ~line 215).
- `ethscan/cli.py` completion non-install path has an unreachable `effective_shell is None` guard (`# pragma: no cover`) because `shell` defaults to `"bash"`. Leave as-is unless a task explicitly asks to refactor completion format handling.
- These are documented contracts, not defects.

## Next session guidance
1. Re-run `python -m pytest -q` and `python -m coverage report --fail-under=100 --include='ethscan/*'` once to confirm steady state; if green, stop.
2. Only select new work if a genuine gap is reproduced first (reproduce before changing). Do not fabricate work; the repo is at a verified steady state.
3. Do not count control-marker-only commits as progress; make a real, verifiable change or leave the tree clean.

(End of file)