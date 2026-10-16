# Next Task for Agent

## Status
`ethscan/hash.py` coverage task DONE (96% → **98%**, 246 stmts, 5 missing). Added 4 targeted unit tests to `tests/test_hash.py` only; no files under `ethscan/` modified. Full suite 3796 passed, 1 skipped; ruff: no new violations.

Remaining 5 misses on hash.py are not coverable in this session without modifying ethscan/:
- lines 34-35, 60, 83: MD4 import-time code, md4 unavailable on this OpenSSL build.
- line 226: logically unreachable (`_compute_pbkdf2_hash` raises first for any algorithm without a hashlib name).

## Next precise task
Improve coverage on `ethscan/ldap.py` (96% coverage, 15 missing statements: lines 284, 340, 345, 364, 367-368, 377, 471-473, 475, 481-482, 493, 650) — add targeted unit tests to `tests/test_ldap.py` following existing conventions, without modifying files under `ethscan/`.

Verification baseline: full suite `3796 passed, 1 skipped`; `tests/test_ldap.py` should pass and `ethscan/ldap.py` coverage should rise from 96%; `python -m ruff check tests/test_ldap.py` must introduce no new violations.
