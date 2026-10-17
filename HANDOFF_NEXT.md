What changed:
- Added targeted tests to `tests/test_passwords.py` achieving 100% coverage for `ethscan/passwords.py`. Tests cover edge cases: unsupported algorithms for peppered hashing (both _compute_peppered_hash and _compute_password_hash paths), no-salt/no-pepper path, and fair verdict range. Fixed minor style issues (bytes literal). All existing tests continue to pass.
- Added additional test cases to `tests/test_passwords.py` to exercise all verdict branches.

What was verified:
- `python -m pytest tests/test_passwords.py` → 59 passed.
- `python -m pytest --cov=ethscan.passwords --cov-report=term-missing` → 135/135 covered (100%).
- `python -m ruff check tests/test_passwords.py` → passes.
- Full suite → 3849 passed, 1 skipped (increased from 3848 passed with previous changes).

What remains unresolved:
- Overall missing statements reduced from 124 to 110. Remaining gaps (by module): radix.py 9, vuln.py 9, s3.py 6, snmp.py 5, resolve.py 4, ssl.py 4, service.py 3, redis.py 2, postgresql.py 1, smtp.py 1, trace.py 1. Some of these are defensive/rare branches.
- No work done on other modules beyond passwords.

Which approaches failed and why:
- Attempted to hit fair verdict with "abc123"/"12345678" initially; had to use "13579246" (non-common digits) to avoid the common-password penalty. Adjusted test accordingly.
- Some defensive branches in postgresql/smtp are hard to trigger naturally (empty msg_type slice, socket close after connect) - not feasible to hit without unnatural test construction; tests focus on practical paths.

Next task:
- Continue improving coverage by tackling modules with smallest remaining gaps. Start with trace.py (1 missing), postgresql.py (1 missing), smtp.py (1 missing) if feasible; otherwise tackle redis.py (2) or service.py (3). Add minimal targeted unit tests to corresponding test files without modifying `ethscan/`. Verify targeted tests pass, ruff on modified test files passes, and full suite remains green (≥3849 passed, 1 skipped). Prefer practical test cases over contrived ones for unreachable defensive code.
