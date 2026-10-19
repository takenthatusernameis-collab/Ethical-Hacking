# HANDOFF_NEXT.md

## Summary
Executed the prior agent's assignment: an empty or host-less `--target` is
now a clean click usage error (exit code 2, one-line message, no traceback)
in the nine protocol commands `redis`, `memcached`, `ntp`, `snmp`, `ftp`,
`ldap`, `netbios`, `smb` and `smtp`.

The prior session had already identified the defect and left a precise plan
in `NEXT_TASK.md`; the library side had not been touched, so all nine
invocations still dumped a `ValueError: Could not parse host from target ''`
traceback and exited 1.

## Changes
- **new** `ethscan/target.py`: `TargetSpecError(ValueError)`, the shared
  error type for "this target string has no usable host". The module holds
  nothing else and imports no click.
- 14 protocol modules (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`,
  `netbios`, `smb`, `smtp`, `mysql`, `mongodb`, `oracle`, `postgresql`,
  `mssql`): their duplicated `_normalize_target` helpers now raise
  `TargetSpecError` instead of a bare `ValueError`. **Only the exception
  type changed** - the parsers were not consolidated, as instructed.
- `ethscan/cli.py`: `_invalid_target(exc)` builds the
  `click.BadParameter(..., param_hint="'--target'")`; the
  `_target_usage_errors` decorator applies it. The decorator is attached to
  exactly the nine commands that used to crash.
- `README.md`: the Usage section documents the new usage error.
- `tests/test_target.py` (new, 49 tests) and `tests/test_cli.py` (+7).

### Design choice (the prior task asked for it to be stated)
A **single shared error type in a new module** `ethscan/target.py` was
chosen over giving each protocol module its own error class. Reasons:
`TargetSpecError` subclasses `ValueError`, so the five modules that already
catch `ValueError` around the probe (and report the failure inside their
JSON output) keep working with no change at all; and the CLI has exactly
one import and one `except` clause instead of a tuple of 14 exception types.

The translation itself lives in one place: `_target_usage_errors` in
`ethscan/cli.py`. No library module imports click - the existing
`test_library_modules_stay_free_of_click` guard was extended to cover
`target.py` and all 14 protocol modules so this cannot regress.

## Verification
- **Behavioural equivalence**: a 196-invocation harness (14 commands x 10
  target values, plus `--output-format json|markdown|csv` and `--help` per
  command) was captured from a pristine `git archive HEAD` tree and from the
  working tree, then compared byte for byte.
  **151 of 196 invocations are byte-identical**; the other **45 are exactly
  the intended conversions** (9 commands x 5 unusable targets: stdout
  byte-identical, exit code 1 -> 2, stderr changed from a raw traceback to
  a one-line usage error). **No invocation differs in any other way** - the
  five probe-failure commands are byte-identical in all 14 of their
  invocations, and every usable target (`127.0.0.1`, `127.0.0.1:6379`,
  `redis://127.0.0.1:6379`, `[::1]:6379`, `localhost`) is byte-identical.
- **Full suite**: 4080 passed, 1 skipped (baseline 4024 -> 4080, 56 new).
  No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; the rule set is
  identical once line numbers are normalised (the only diff is the two-line
  import shift in the 14 protocol modules).
- **Manual**: all nine previously-crashing invocations now print
  `Error: Invalid value for '--target': Could not parse host from target ''`
  and exit 2.

## Unresolved
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) still report an unparsable target inside their
  JSON output with exit code 0. Intentional - their contract is "the probe
  failed", not "the option is invalid".
- The 14 `_normalize_target` copies are still duplicated. They are not
  identical (some use `host.find("]:")`, some `host.endswith("]")`), so
  consolidating them is a separate refactor that would change behaviour for
  the `host:` and bracketed-IPv6 edge cases.
- `ethscan/target.py` holds only the error type. A shared normaliser was
  deliberately not added.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.
- The remaining raw-traceback clusters listed in `NEXT_TASK.md` were
  re-verified on this commit and still reproduce; they were deliberately not
  bundled into this change.

## Next agent task
Implement the "host:port with a non-numeric port" cluster described in
`NEXT_TASK.md`: `headers`, `web`, `urlcheck` and `ssh` die with a raw
`ValueError: Port could not be cast to integer value as ':not::an::ip::'`
traceback (exit 1) when the `--target` looks like `host:port` but the port
is not a number. Turn it into a click usage error at the CLI boundary,
mirroring the `_check_cidr` / `CidrSpecError` and `_target_usage_errors` /
`TargetSpecError` patterns already established.
