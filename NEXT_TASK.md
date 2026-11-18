# Next Task
Date: Wed Nov 18 2026

## Status
- Repository green: 39783 passed, 149 skipped, 0 failed; mypy/ruff clean;
  README in sync; `ethscan/hash.py` at 100% statement/branch coverage.
- Closed a documented-contract defect: NTLM and MD4 hashing previously failed
  whenever the platform's OpenSSL build did not expose MD4 through `hashlib`.

## This session (what changed)
- `ethscan/hash.py`: added self-contained RFC 1320 MD4 (`_md4_digest`,
  `_rol32`) plus HMAC-MD4 (`_md4_hmac_hex`, `_hmac_hex`); NTLM and MD4 now
  always work. Native hashlib MD4 is used only to register the name for
  PBKDF2/HMAC when available. Removed the impossible "MD4 unavailable" notes.
- `tests/test_hash.py`: RFC 1320 vectors (7 lengths), NTLM/MD4 known digests,
  HMAC-MD4 vectors (short/long key), `MD4_AVAILABLE is True`, successful MD4
  `run_check`.
- `README.md`: hash bullet reflects the built-in MD4 fallback and concrete
  pepper algorithms.

## Verified
- CLI: `hash --algorithm ntlm` -> `8846f7eaee8fb117ad06bdd830b7586c`;
  `hash --algorithm md4` -> `8a9d093f14f8701df17732b2bb182c74`; peppered MD4
  -> `28f58ad8e71156ab54e0513bd039bbfd`; all exit 0.
- `coverage report --include=*/hash.py` -> 100% (327 stmts, 130 branch).
- `pytest tests/test_hash.py tests/test_cli.py -q` -> 1256 passed.
- `pytest -q` -> 39783 passed, 149 skipped.
- `mypy ethscan/ tests/` -> Success (261 files); `ruff` clean;
  `check_readme.py` -> 54 commands, 0 drift.

## Known limitations (intentionally out of scope)
- PBKDF2 + MD4 still needs native hashlib MD4; otherwise the existing in-band
  "does not support PBKDF2 (no hashlib name)" error is returned. Not claimed by
  the README; unchanged.
- `ethscan/cli.py:4318` remains the documented unreachable completion guard.

## Next task
- Add `tests/test_cli.py` regression tests for successful `hash --algorithm md4`
  and `--algorithm ntlm` output (JSON digest and CSV digest assertions).
  Existing CLI tests cover only NTLM pepper/PBKDF2 error paths, so this locks
  the fix at the integration boundary. Then rerun:
  focused tests, `pytest -q`, `mypy ethscan/ tests/`,
  `ruff check ethscan/ tests/ check_readme.py`, `python check_readme.py`.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- Do not commit manually; the workflow controller commits and verifies pushes.
