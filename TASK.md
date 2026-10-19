# TASK.md

Date: 2026-10-19T21:05:00Z
Status: a `--target` that contains no usable host is now a clean click usage
error (exit code 2) in the nine protocol commands that used to dump a
traceback, the translation lives in exactly one place, the library modules
stay free of click, and the five commands that report a failed probe keep
their contract.

## What changed (this session)
- **new** `ethscan/target.py`: holds `TargetSpecError(ValueError)`, the
  shared error type for an unusable target. The module is deliberately
  click-free.
- `ethscan/{redis,memcached,ntp,snmp,ftp,ldap,netbios,smb,smtp,mysql,mongodb,oracle,postgresql,mssql}.py`
  (14 modules): the duplicated `_normalize_target` helpers now raise
  `TargetSpecError` instead of a bare `ValueError`. The parsers themselves
  were **not** consolidated - they differ (some use `host.find("]:")`, some
  `host.endswith("]")`) and that is a separate refactor.
  `TargetSpecError` is a `ValueError` subclass, so the five modules that
  already catch `ValueError` around the probe keep working unchanged.
  `memcached.py`, `ldap.py` and `smb.py` list it in `__all__`.
- `ethscan/cli.py`:
  - new `_invalid_target(exc)` builds `click.BadParameter(..., param_hint="'--target'")`.
  - new `_target_usage_errors` decorator translates a `TargetSpecError`
    into that usage error. It is applied to exactly the nine commands that
    used to crash (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`,
    `netbios`, `smb`, `smtp`).
- `README.md`: the Usage section documents the `--target` usage error and
  names the nine commands it applies to.
- `tests/test_target.py` (new, 49 tests): the error type is a `ValueError`
  subclass, all 14 modules raise it for every unusable target, all 14 still
  raise it as a `ValueError`, valid targets are unaffected, and the five
  probe-failure modules still report the error inside their own output.
- `tests/test_cli.py` (+7): usage error for each of the nine commands and
  each of the five unusable target values; the nine previously-crashing
  invocations; a single-line error; the offending value quoted in the
  message; the five probe-failure commands still exit 0 and still report the
  error in their JSON output; no transport helper is reached for a rejected
  target; usable targets are still accepted. The existing
  `test_library_modules_stay_free_of_click` guard now also covers
  `target.py` and the 14 protocol modules.

## Verification
- **Behavioural equivalence**: a 196-invocation harness (14 commands x
  10 target values, plus 3 output formats and `--help` per command) was
  captured from a pristine `git archive HEAD` tree in `/tmp` and from the
  working tree, and compared byte for byte. **151 of 196 invocations are
  byte-identical**; the other **45 are exactly the intended conversions**
  (9 commands x 5 unusable targets: stdout byte-identical, exit code 1 ->
  2, stderr changed from a raw traceback to a one-line usage error).
  **No invocation differs in any other way** - in particular the five
  probe-failure commands are byte-identical in all 14 of their invocations
  and every usable target is byte-identical.
- **Full suite**: **4080 passed, 1 skipped** (baseline 4024 + 56 new).
  No regressions.
- **Lint**: `python -m ruff check ethscan tests --output-format concise`
  reports the same 48 pre-existing errors as the baseline; the rule set is
  byte-identical when the line numbers are normalised (the only diff is the
  two-line import shift in the 14 protocol modules).
- **Manual**: all nine previously-crashing invocations now print
  `Error: Invalid value for '--target': Could not parse host from target ''`
  and exit 2 instead of dumping a traceback and exiting 1.

## Unresolved / deliberate non-changes
- The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
  `postgresql`, `mssql`) still report an unparsable target inside their
  JSON output with exit code 0. That is their documented contract, so it
  was left alone.
- The 14 `_normalize_target` copies are still not consolidated; only the
  exception type changed. The copies differ in how they detect a bracketed
  IPv6 literal, so a consolidation would change behaviour and is a separate
  task.
- `ethscan/target.py` currently holds only the error type. A shared
  normaliser was deliberately not added: it would change the behaviour of
  the five probe-failure commands and of the `host:` / `host:port` edge
  cases.
- The 48 pre-existing ruff errors are unrelated to this work and were
  deliberately left alone.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.
