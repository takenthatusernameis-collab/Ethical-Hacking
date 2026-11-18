# Handoff
Date: Wed Nov 18 2026

## This session
- Executed the prior assignment: CLI-boundary regression coverage for the
  built-in NTLM/MD4 hashing added in the previous session.

## What changed
- `tests/test_cli.py` (+51 lines, only changed file):
  - `test_hash_password_md4_json_uses_builtin_digest`: parses JSON from
    `hash --password password --algorithm md4` and asserts
    `results[0]["hash"] == "8a9d093f14f8701df17732b2bb182c74"` plus no error.
  - `test_hash_password_ntlm_json_uses_builtin_digest`: same for NTLM,
    digest `8846f7eaee8fb117ad06bdd830b7586c`.
  - `test_hash_password_md4_and_ntlm_csv_digests`: real (non-monkeypatched)
    CSV run via `--output-format csv --file`, asserts header row and
    `password,<digest>,<algorithm>` for both algorithms.

## What was actually verified
- `python -m pytest tests/test_cli.py -q -k "md4 or ntlm"` -> 5 passed.
- `python -m pytest -q` -> 39786 passed, 149 skipped, 0 failed (was 39783).
- `python -m mypy ethscan/ tests/` -> Success, 261 files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift.
- `git diff --check` clean; `git status` shows only `tests/test_cli.py`.

## What remains unresolved
- PBKDF2 + MD4 is still rejected at the library boundary:
  `python -m ethscan hash --password password --salt saltvalue --iterations 1000 --algorithm md4 --format json`
  exits 0 but `results[0].hash` is null with
  `"Algorithm 'md4' does not support PBKDF2 (no hashlib name)."`, while the
  response `notes` still says "PBKDF2 iterations: 1000 applied with the salt."
  The root cause is `_compute_pbkdf2_hash` (ethscan/hash.py:236-269) requiring
  `_hashlib_name(...)`, which returns None for md4 on this platform.
- PBKDF2 + NTLM remains intentionally unsupported (NTLM is not a hash of
  arbitrary bytes), so that error path must stay.
- `ethscan/cli.py:4318` remains the known unreachable completion guard.

## Approaches already tried / ruled out
- Third-party crypto packages for PBKDF2-MD4: rejected, project is stdlib-only
  (`requirements.txt` is click/pyyaml/dnspython).
- Making `_hashlib_name("md4")` return the string "md4" unconditionally: would
  break `hashlib.pbkdf2_hmac`/`hmac.new` at runtime on this platform.
- Relying on native MD4 being present: this environment's OpenSSL 3.5.5 does
  not expose it, so the pure fallback is the only active path.

## Next task
- Implement PBKDF2-HMAC-MD4 in pure Python (RFC 2898) as the fallback inside
  `_compute_pbkdf2_hash` when `_hashlib_name("md4")` is None, reusing
  `_md4_hmac_hex`/`_md4_digest`, with default dklen 16 (MD4 digest size).
  Independent oracle available: PHP is installed and supports MD4:
  - `php -r 'echo hash_pbkdf2("md4","password","saltvalue",1000,16);'`
    -> `1a87747a9ec8f83f194a7b279d89e593`
  - peppered layer `php -r 'echo hash_hmac("md4", hash_pbkdf2("md4","password","saltvalue",1000,16), "secretpepper");'`
    -> `5743922682e1ee76099abd2680f076bd`
  Add unit + CLI tests for those values, keep the NTLM error path intact, and
  update the README hash/pepper bullet only if the new support is user-visible.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3;
  PHP CLI available with MD4 in `hash_algos()`.
- Do not commit manually: the workflow controller stages/commits/pushes.
