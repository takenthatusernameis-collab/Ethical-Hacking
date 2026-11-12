# Next Task

## Status
Session 119 closed the `smb` formatter `security_flags` hostile-shape gap (the source hardening from session 118 was already in place; this session fixed its defective test so the sweep is green).

## One precise next task
None pending. Repository is fully green:
- `python -m pytest -q` → 6252 passed, 53 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 189 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.

## Notes
- `oracle` and `postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).
- Other hostile-shape gaps noted by the session 117 fuzzer (wrong-typed iterable fields in ftp/ntp/oracle/smtp/snmp and others; `ldap` `root_dse` non-dict) remain open but are separate bounded families — pick one at a time and reproduce first.
- Do not weaken CLI validation or tests. Preserve oracle/postgresql in-band exit-0 contract vs usage-error exits elsewhere.