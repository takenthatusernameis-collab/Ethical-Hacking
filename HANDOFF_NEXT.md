# Handoff
Date: Wed Nov 18 2026

## This session
- No prior assignment was pending (previous handoff said "None pending"). Inspected the repo and reproduced a real, documented defect:
  `ethscan hash --algorithm ntlm` and `--algorithm md4` returned `"hash": null` with
  "MD4 is not available on this platform (OpenSSL build)." on this environment
  (Python 3.14.4, OpenSSL 3.5.5, `hashlib.algorithms_available` has no `md4`).
  The README documents NTLM and MD4 as supported, so the platform dependency
  contradicted the documented contract.
- Baseline before changes: `pytest -q` -> 39781 passed, 149 skipped; mypy/ruff/check_readme clean.

## What changed
- `ethscan/hash.py`:
  - Added a self-contained RFC 1320 MD4 implementation (`_md4_digest`, `_rol32`)
    and `_md4_hmac_hex` (RFC 2104 HMAC-MD4, including key > block-size hashing).
  - `MD4_AVAILABLE` is now always `True`; `hashlib`'s native MD4 is only used to
    register the name for PBKDF2/HMAC when the OpenSSL build exposes it.
  - `_compute_md4`/`_compute_ntlm` always compute (UTF-8 / UTF-16LE respectively).
  - Extracted `_hmac_hex`; peppered MD4 now uses the pure HMAC-MD4 fallback.
    NTLM HMAC remains unsupported (no hash function of its own), unchanged.
  - Removed the now-impossible "MD4/NTLM unavailable" notes in `run_hash`;
    `_supported_algorithms` always includes `md4`.
- `tests/test_hash.py`: replaced platform-conditional MD4/NTLM tests with
  deterministic RFC 1320 vectors, NTLM("password") = 8846f7..., MD4("password")
  = 8a9d093f..., HMAC-MD4 vectors (independently verified with PHP's
  `hash_hmac`), a `MD4_AVAILABLE is True` assertion, and a real MD4
  `run_check` match test.
- `README.md`: hash bullet now states MD4/NTLM work via the built-in RFC 1320
  implementation; pepper wording lists the concrete HMAC algorithms.

## What was actually verified
- `python -m ethscan hash --password password --algorithm ntlm` -> hash
  `8846f7eaee8fb117ad06bdd830b7586c`, exit 0.
- `python -m ethscan hash --password password --algorithm md4` -> hash
  `8a9d093f14f8701df17732b2bb182c74` (JSON and CSV), exit 0.
- `python -m ethscan hash --password password --algorithm md4 --pepper secretpepper`
  -> `28f58ad8e71156ab54e0513bd039bbfd` (matches independent PHP HMAC-MD4).
- `python -m coverage run --branch --source=ethscan -m pytest tests/test_hash.py -q`
  then `coverage report --include=*/hash.py` -> 100% (327 stmts, 130 branch, 0 miss, 0 partial).
- `python -m pytest tests/test_hash.py tests/test_cli.py -q` -> 1256 passed.
- `python -m pytest -q` -> 39783 passed, 149 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success, 261 files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift; `git diff --check` clean.
- Working tree contains exactly README.md, ethscan/hash.py, tests/test_hash.py.

## What remains unresolved
- PBKDF2 + MD4 (`--algorithm md4 --salt ... --iterations ...`) still requires a
  native `hashlib` MD4 name; on this platform it reports an in-band per-password
  error ("does not support PBKDF2 (no hashlib name)"). PBKDF2-MD4 was not
  claimed by the README and was intentionally left unchanged.
- `ethscan/cli.py` line 4318 remains the known unreachable completion guard
  (unrelated to this change).

## Approaches already tried / ruled out
- Wrapping `hashlib.new("md4")` errors with a friendlier message only: rejected,
  it would keep the documented NTLM/MD4 feature unusable.
- Relying on a third-party MD4 package: rejected, the project is stdlib-only.
- Adding `# pragma: no cover` to the platform-dependent branches: rejected,
  the pure implementation is exercised instead.

## Next task
- Add CLI-boundary regression tests for the new MD4/NTLM behavior in
  `tests/test_cli.py`: assert `hash --algorithm md4` and `--algorithm ntlm`
  emit the real digests in JSON and CSV (evidence: existing CLI tests cover only
  the NTLM pepper/PBKDF2 error paths, not successful MD4/NTLM output).
  Then rerun focused tests plus the full gates (pytest/mypy/ruff/check_readme).

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.
- Native MD4 is absent here (`OpenSSL 3.5.5`), so the pure fallback is the
  active code path. Tests cross-check against native MD4 when present.
- Do not commit manually: the workflow controller stages/commits/pushes.
