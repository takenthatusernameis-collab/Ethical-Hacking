# Handoff
Date: Wed Nov 18 2026

## This session
- Reconciled the stale handoff with the committed tree: the PBKDF2-HMAC-MD4
  fallback described as "unresolved" was already implemented and committed
  (`_pbkdf2_hmac_md4` in ethscan/hash.py:131; fallback used in
  `_compute_pbkdf2_hash` at ethscan/hash.py:288-294).
- Verified end-to-end: `hash --password password --salt saltvalue --iterations
  1000 --algorithm md4 --format json` returns
  `1a87747a9ec8f83f194a7b279d89e593`, matching the PHP oracle
  `hash_pbkdf2("md4","password","saltvalue",1000,16)`.
- Closed the last coverage gap: added
  `test_pbkdf2_hmac_md4_dklen_too_large` in tests/test_hash.py covering the
  `dklen too large` branch (ethscan/hash.py:137). `ethscan/hash.py` is now
  100% covered.

## What changed
- `tests/test_hash.py` (+1 test): `test_pbkdf2_hmac_md4_dklen_too_large`.
- No source changes needed; `_compute_pbkdf2_hash` already routed md4 to the
  pure-Python PBKDF2-HMAC-MD4 fallback when `_hashlib_name` returns None.

## What was actually verified
- `python -m pytest tests/test_hash.py tests/test_cli.py -q -k "md4 or pbkdf2 or ntlm"` -> 30 passed.
- `python -m pytest -q` -> 39794 passed, 149 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success, 261 files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift.
- `python -m coverage report --include="ethscan/hash.py" -m` -> 100%, 0 missing.
- `git diff --check` clean; `git status` shows only tests/test_hash.py.

## What remains unresolved
- Nothing. PBKDF2 + MD4 is supported; PBKDF2 + NTLM remains intentionally
  unsupported (error path intact, with tests). `ethscan/cli.py:4318` unreachable
  completion guard left in place per documentation.

## Approaches already tried / ruled out (from prior session)
- Third-party crypto packages for PBKDF2-MD4: rejected, project is stdlib-only.
- Making `_hashlib_name("md4")` return "md4" unconditionally: breaks at runtime
  on this OpenSSL 3.5.5 build (no native MD4).
- Native MD4 via hashlib: not exposed by this platform's OpenSSL; pure fallback
  is the only active path.

## Next task
- No pending assigned task. The repository is at a clean, green baseline
  (tests/mypy/ruff/check_readme/coverage all pass). The next agent should
  consult the product backlog; if selecting a self-directed bounded task, a
  coverage sweep of the next-lowest-covered module in ethscan/ is a reasonable
  starting point, but no defect or gap is currently demonstrated.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3;
  PHP CLI available with MD4 in `hash_algos()`.
- Do not commit manually: the workflow controller stages/commits/pushes.
