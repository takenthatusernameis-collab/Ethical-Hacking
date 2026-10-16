What changed:
- Added targeted tests to `tests/test_ldap.py` achieving 100% coverage for `ethscan/ldap.py`. Tests cover BER length/TLV edge cases, _parse_attribute/_parse_search_entry continue paths, _parse_ldap_message validation, _build_banner behavior, markdown referral, and _send_recv timeout/OSError/close-exception paths. Added internal helper imports; minor ruff cleanup applied.

What was verified:
- `python -m pytest tests/test_ldap.py` → 102 passed.
- `python -m pytest --cov=ethscan.ldap --cov-report=term-missing` → 362/362 covered (100%).
- `python -m pytest --cov=ethscan --cov-report=term-missing` → 12681/12481+ (124 missing overall; ldap now 100%).
- Full suite → 3813 passed, 1 skipped.
- `python -m ruff check tests/test_ldap.py` → passes.

What remains unresolved:
- Overall 124 missing statements across several modules (e.g. snmp.py: 15, radix.py: 9, passwords.py: 4, resolve.py: 4, s3.py: 6, ssl.py: 4, service.py: 3, redis.py: 2, postgresql.py: 1, smtp.py: 1). No work done on these yet.

Which approaches failed and why:
- None.

Next task:
- Select one module with the smallest missing set (e.g. passwords.py has 4 missing: 65,108,120,220) and add minimal targeted unit tests to `tests/test_passwords.py` without modifying `ethscan/`, preserving existing test conventions. Verify the targeted tests pass, ruff on modified test files passes, and full suite remains 3813 passed, 1 skipped.
