# Task
Date: 2026-10-19T09:00:00Z
Status: Bounded dead-code removal completed and committed; baseline preserved
Branch: main (local, ahead of origin/main by 3 commits: 19777ff + c6b6fc2 + 5cba856)

Completed
- Inspected repository state (clean working tree at c6b6fc2 / 405f2c6 at session start).
- Verified baseline: `python -m pytest -q` -> 3906 passed, 1 skipped; `python -m ruff check ethscan tests` -> 44 documented intentional errors unchanged; `python -m py_compile ethscan/*.py` clean; `python -m ethscan --help`/`--version` OK.
- Selected and executed a bounded, behavior-preserving task: removed one provably-dead duplicate line in `ethscan/ssl.py:224`.

What changed
- `ethscan/ssl.py` `inspect_certificate`: removed the second `expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")` line (was line 224).
- Evidence it was dead: identical to the already-fixed `web.py` case — on Python 3.12 `datetime.strptime(..., "%Z")` parses "GMT"/"UTC" but never attaches tzinfo, so line 224 reassigns `expiry` to the exact value computed on line 222. The subsequent `expiry_tz = expiry.replace(tzinfo=timezone.utc)` uses only the first assignment's result. Confirmed empirically (`tzinfo: None` after parse). No behavior change.
- Commit: 5cba856 "Remove provably-dead duplicate strptime in ssl.py SSL expiry parse" (1 file, 1 deletion).

Current state
- Working tree: CLEAN.
- Verification after change: `python -m pytest -q` -> 3906 passed, 1 skipped (green, unchanged); `python -m ruff check ethscan tests` -> 44 errors unchanged; `python -m py_compile ethscan/*.py` -> clean; `git diff --stat` -> 1 file, 1 deletion.
- Lint baseline: 44 errors (BLE001/TRY002/PLR0402) — do not modify per constraints.
- Tests: 3906 passed, 1 skipped (green baseline).

Notes
- Pre-existing E303 too-many-blank-lines sites (ethscan/cli.py:3600, ethscan/validate.py:279, ethscan/cidr.py:255-256, and others) are not regressions; left untouched.
- Remaining coverage gaps (__main__ guard, dnspython import fallback, hash MD4/platform branches, radix defensive edges, network-dependent modules) are environmental/unreachable-defensive, not closable within constraints.

Constraints
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402).
- Preserve baseline; avoid speculative refactors touching those lint exceptions.
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests.
- Only remove provably-dead code with definitive proof.