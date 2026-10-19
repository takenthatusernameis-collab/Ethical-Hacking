# NEXT_TASK.md

## Status (2026-10-19T19:40:00Z)
- Prior agent task (invalid `--ports` -> click usage error): **complete**
  (see `TASK.md` / `HANDOFF_NEXT.md`).
- Prior agent task (invalid CIDR -> click usage error for `cidr` and `radix`):
  **complete**. The library-side `CidrSpecError` already existed in commit
  `2e823af`; this session added the missing CLI translation, consolidated the
  duplicated `_normalize_cidr`, fixed the pre-existing `TypeError` crash on
  mixed IPv4/IPv6 radix input, and added 29 tests.
- Verified: 243-invocation CLI harness, 178 byte-identical, 62 exactly the
  intended traceback -> usage-error conversions (3 more differ only in the
  temporary file path recorded in argv), no stdout change anywhere,
  `validate` byte-identical in all 8 of its invocations; full suite 4024
  passed / 1 skipped; ruff output identical to the baseline (48 errors).

## Next task (bounded, high-value)
Nine protocol commands still crash with a raw Python traceback when
`--target` is empty or contains no host. Make them report a clean click
usage error (exit code 2), following the `_check_cidr` / `CidrSpecError`
pattern established in the last two sessions.

Evidence (reproduced on `main` at this commit):
```
$ python -m ethscan redis --target ""
...
ValueError: Could not parse host from target ''      # traceback, exit 1
```
The same happens for `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`,
`smb` and `smtp` (9 commands).

### Scope
- 14 modules have a `_normalize_target()` helper that ends with
  `raise ValueError(f"Could not parse host from target {target!r}")` when the
  host ends up empty:
  `ethscan/memcached.py:30`, `ntp.py:26`, `snmp.py:114`, `redis.py:31`,
  `ftp.py:26`, `oracle.py:28`, `postgresql.py:48`, `ldap.py:123`,
  `mssql.py:186`, `mysql.py:27`, `netbios.py:113`, `smb.py:161`,
  `smtp.py:41`, `mongodb.py:28`.
- Only 9 of them crash. `oracle`, `postgresql`, `mssql`, `mysql` and
  `mongodb` already catch the `ValueError` around the probe
  (`ethscan/mysql.py:335`, `mongodb.py:257`, `oracle.py:358`,
  `postgresql.py:308`, `mssql.py:524`) and report it inside their JSON
  output with exit code 0. **Leave those five alone** - their contract is
  "the probe failed", not "the option is invalid".
- The 9 crashing CLI commands call `run_redis`, `run_memcached`, ... which
  call `_normalize_target`. Translate the error at the CLI boundary, the same
  way `_check_cidr` does: a dedicated error type (a `ValueError` subclass,
  so the five graceful modules keep catching it unchanged) raised by
  `_normalize_target`, and a `click.BadParameter` with
  `param_hint="'--target'"` raised only in `ethscan/cli.py`.

### Implementation notes
- The 14 `_normalize_target` copies are **not** identical (some use
  `host.find("]:" )` and some use `host.endswith("]")`), so do not
  consolidate them in this task - that is a separate refactor. Only change
  the exception type that they raise.
- The exception type has no natural home yet: there is no shared "common"
  module, and `ethscan/__init__.py` only holds `__version__`. Either add a
  small `ethscan/target.py` holding the error type (and possibly a shared
  helper later), or give each module its own error class and catch them
  together in the CLI. Pick one and state the choice in the handoff.
- Do not change `--port` handling, the `host:port` / `scheme://host:port`
  forms, or the five graceful commands.
- Do not try to fix the other traceback clusters in the same change; see
  "Other traceback clusters" below.

### Verification
- `python -m pytest tests/test_cli.py -q` plus new tests asserting exit code
  2, an `Error: Invalid value for '--target': Could not parse host from
  target ''` message and the absence of a traceback for each of the 9
  commands.
- A regression test that the five graceful commands still exit 0 and still
  report the error inside their JSON output.
- `python -m ruff check ethscan tests` must stay at 48 pre-existing errors
  with no new ones.
- A before/after CLI harness over the 9 commands x a set of target values
  (empty, blank, `host:port`, `scheme://host:port`, `[::1]:6379`, a valid
  host) to prove the valid cases are byte-identical.

## Other traceback clusters (found, not fixed - do not bundle them in)
A survey of every command with hostile option values found these remaining
raw-traceback defects. They are separate tasks; pick one at a time.
- `headers`, `web`, `urlcheck`, `ssh` with `--target ::not::an::ip::` ->
  `ValueError: Port could not be cast to integer value`. A target that looks
  like `host:port` but whose port is not a number.
- `headers`, `web`, `fuzz`, `urlcheck`, `s3` with a `--target` containing a
  space -> `http.client.InvalidURL: URL can't contain control characters`.
- `ping`, `geo`, `dnssec`, `vuln`, `osdetect`, `service`, `scan`, `smtp`,
  `ftp`, `ssh`, `s3` with an unresolvable host -> `socket.gaierror` or
  `encoding with 'idna' codec failed`. These are network-dependent, so they
  need a different decision: a failed DNS lookup is arguably a probe result
  (exit 0 with an error field) rather than a usage error.
- `trace` with `--target ''` -> `ValueError: Invalid target`
  (`ethscan/trace.py:79`).
