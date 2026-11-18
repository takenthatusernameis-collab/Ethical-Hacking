# Next Task
Date: Wed Nov 18 2026

## Status
- Repository green: 39786 passed, 149 skipped, 0 failed; mypy/ruff clean;
  README in sync (54 commands).
- Prior fix is now locked at the integration boundary: successful
  `hash --algorithm md4` and `--algorithm ntlm` output is asserted in JSON and
  CSV in `tests/test_cli.py`.

## This session (what changed)
- Added three CLI regression tests in `tests/test_cli.py` (only file touched):
  `test_hash_password_md4_json_uses_builtin_digest`,
  `test_hash_password_ntlm_json_uses_builtin_digest`,
  `test_hash_password_md4_and_ntlm_csv_digests`. The CSV test exercises the
  real hashing path (no monkeypatching of `run_hash`).

## Verified
- `pytest -q` -> 39786 passed, 149 skipped.
- `pytest tests/test_cli.py -q -k "md4 or ntlm"` -> 5 passed.
- `mypy ethscan/ tests/` -> Success (261 files); `ruff` clean;
  `check_readme.py` -> 54 commands, 0 drift; `git diff --check` clean.

## Known limitation (demonstrated, in scope for next session)
- `hash --algorithm md4 --salt saltvalue --iterations 1000` returns
  `hash: null` + `"Algorithm 'md4' does not support PBKDF2 (no hashlib name)."`
  even though the response notes still claim the iterations were applied.
  Cause: `_compute_pbkdf2_hash` in `ethscan/hash.py` requires a native
  hashlib name for MD4, which this OpenSSL build does not provide.
- PBKDF2 + NTLM must stay unsupported (not a byte-oriented hash); keep that
  error path and its existing tests.

## Next task
- Add a pure-Python PBKDF2-HMAC-MD4 fallback in `_compute_pbkdf2_hash`
  (RFC 2898, block index 1, dklen 16 for MD4), reusing `_md4_hmac_hex`.
- Independent vectors (PHP CLI, already verified working here):
  - PBKDF2-HMAC-MD4("password", "saltvalue", 1000, 16)
    = `1a87747a9ec8f83f194a7b279d89e593`
  - HMAC-MD4("secretpepper", that digest)
    = `5743922682e1ee76099abd2680f076bd`
- Cover both in `tests/test_hash.py` and in a real CLI test in
  `tests/test_cli.py`; keep MD4 `hash.py` coverage at 100%; update the README
  only if PBKDF2-MD4 becomes a claimed capability.
- Then rerun: focused tests, `pytest -q`, `mypy ethscan/ tests/`,
  `ruff check ethscan/ tests/ check_readme.py`, `python check_readme.py`.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- `ethscan/cli.py:4318` is a documented unreachable completion guard; leave it.
- Do not commit manually; the workflow controller commits and verifies pushes.
