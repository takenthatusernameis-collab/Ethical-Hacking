# Task
Date: 2026-10-19T09:05:00Z
Status: Bounded bug fix committed; baseline preserved
Branch: main (local, ahead of origin/main by 4 commits: 19777ff + c6b6fc2 + 5cba856 + bd662ea)

Completed
- Inspected repository state (clean working tree at 8f6370a / 5cba856 at session start).
- Verified baseline: `python -m pytest -q` -> 3906 passed, 1 skipped; `python -m ruff check ethscan tests` -> 44 documented intentional errors unchanged; `python -m py_compile ethscan/*.py` clean; `python -m ethscan --help`/`--version` OK.
- Selected and executed a bounded, behavior-preserving bug fix: `mac.run_mac` module-global state leak.

What changed
- `ethscan/mac.py` `run_mac`: wrapped the function body in `try/finally` so `DEFAULT_API_URL` is restored to its original value on every exit path (including the early-return branch taken when the host cannot be resolved).
- Evidence it was a bug: `run_mac` stored a caller-supplied `--api_url` into the module-level `DEFAULT_API_URL` at the top, but the unresolvable-host early `return` happened before the restoration at the bottom. Reproduced empirically: after `run_mac("nonexistent.invalid.domain.tld", api_url="https://custom.example.com")`, `ethscan.mac.DEFAULT_API_URL` remained `"https://custom.example.com"` instead of reverting to `"https://api.macvendors.com/"`. This is a real state-leak bug affecting subsequent MAC lookups (and any other caller reading `DEFAULT_API_URL`).
- Commit: bd662ea "Fix DEFAULT_API_URL state leak in mac.run_mac early-return path" (1 file modified, 1 test added).

What was verified
- New failing test `tests/test_mac.py::test_run_mac_unresolvable_restores_default_api_url` reproduces the leak; passes after fix.
- `python -m pytest -q` -> 3907 passed, 1 skipped (green, +1 new test).
- `python -m ruff check ethscan tests` -> 44 errors unchanged.
- `python -m py_compile ethscan/*.py` -> clean.
- `git diff --stat` -> 2 files changed (ethscan/mac.py, tests/test_mac.py), no unintended edits.
- Working tree CLEAN after commit.

Current state
- Working tree: CLEAN.
- Tests: 3907 passed, 1 skipped (green baseline, +1 new test).
- Lint baseline: 44 errors (BLE001/TRY002/PLR0402) — do not modify per constraints.

Notes
- Pre-existing E303 too-many-blank-lines sites (ethscan/cli.py:3600, ethscan/validate.py:279, ethscan/cidr.py:255-256, and others) are not regressions; left untouched.
- Remaining coverage gaps (ethscan/cli.py:4864 __main__ guard; ethscan/dnssec.py dnspython fallback; ethscan/hash.py MD4/NTLM/PBKDF2 paths; ethscan/radix.py defensive edges; network-dependent modules) are environmental/unreachable-defensive, not closable within constraints.

Constraints
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402).
- Preserve baseline; avoid speculative refactors touching those lint exceptions.
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests.
- Only remove provably-dead code or fix genuine bugs with definitive proof and a failing test.