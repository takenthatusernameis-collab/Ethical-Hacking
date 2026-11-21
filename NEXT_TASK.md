# Next Task

No genuine pending task. Repository independently re-verified green this session at HEAD `f9487f9` with FRESH evidence:

- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift
- `mypy ethscan/ tests/` -> Success (267 source files)
- `pytest -q --no-header -p no:cacheprovider` -> 46744 passed, 146 skipped, 0 failed (127.28s) [fresh run this session]

## Do not re-implement / do not "fix" (already done / intended)
- ICMPv6 raw ping in `ethscan/ping.py` — fully implemented and tested.
- All 146 skips are intentional structural skips; none indicate a coverage gap.
- PBKDF2, NTLM, and MD4 all supported in `ethscan/hash.py`; no unsupported gap.
- `hash --check` 32-char ambiguity (md5 preferred; use `--algorithm` for ntlm/md4) — DOCUMENTED + TESTED design, not a bug.
- `oracle`/`postgresql` empty-target in-band handling — documented contract (exit 0).
- `ethscan/cli.py` completion non-install unreachable guard (`# pragma: no cover`) — documented limitation.
- Grep for `TODO|FIXME|XXX|HACK` in `ethscan/` and `tests/` returns no matches.

## Next session guidance
1. Re-run the fast gates first: `ruff`, `mypy`, `check_readme.py`. If all green, run `python -m pytest -q` once to confirm; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; the repo is at a verified steady state.
3. Do not count control-marker-only (handoff-doc) commits as progress; make a real, verifiable change or leave the tree clean.
4. If the orchestration keeps invoking sessions here, the correct outcome is a clean tree + honest "verified green, no gap" handoff — not invented changes.

(End of file)
