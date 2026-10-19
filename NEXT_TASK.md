# NEXT_TASK.md

## Status (2026-10-19T21:05:00Z)
- Prior agent task (invalid `--ports` -> click usage error): **complete**.
- Prior agent task (invalid CIDR -> click usage error for `cidr` and
  `radix`): **complete**.
- Prior agent task (invalid `--target` -> click usage error for the nine
  protocol commands): **complete**. This session added the shared
  `ethscan/target.py` error type, switched the 14 duplicated
  `_normalize_target` helpers to raise it, and added the single CLI
  translation (`_target_usage_errors` in `ethscan/cli.py`).
- Verified: 196-invocation CLI harness, 151 byte-identical, 45 exactly the
  intended traceback -> usage-error conversions, no other difference; full
  suite 4080 passed / 1 skipped; ruff rule set identical to the baseline
  (48 pre-existing errors).

## Next task (bounded, high-value)
A `--target` whose **port is not a number** still crashes with a raw
Python traceback. Make it a clean click usage error (exit code 2), reusing
the machinery this session already established (`TargetSpecError` in
`ethscan/target.py`, `_target_usage_errors` in `ethscan/cli.py`).

Evidence (re-verified on `main` at this commit, after the `--target` work
above):
```
$ python -m ethscan redis --target "redis://host:notaport"
...
ValueError: Port could not be cast to integer value as 'notaport'   # traceback, exit 1
```
Reproduces for **all 9** protocol commands that were fixed last session
(`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`, `smb`,
`smtp`) and additionally for `web`, `headers`, `urlcheck` and `ssh`:
```
$ python -m ethscan web --target "host:notaport"
$ python -m ethscan web --target "https://host:notaport"
$ python -m ethscan headers --target "::not::an::ip::"
$ python -m ethscan urlcheck --target "https://host:notaport"
$ python -m ethscan ssh --target "host:notaport"
```
The five probe-failure commands (`mysql`, `mongodb`, `oracle`,
`postgresql`, `mssql`) and `s3` already catch it and report it inside their
own output (exit 0) - **leave those alone**.

### Scope
- **Origin**: `urllib.parse`'s `SplitResult.port` property raises
  `ValueError` when the port is not an integer. The access sites are:
  - the 14 protocol modules, at the `parsed = urlparse(normalized)` site
    in each `_normalize_target` (`ethscan/redis.py:45`,
    `ethscan/memcached.py:48`, `ethscan/ntp.py:40`, `ethscan/snmp.py:128`,
    `ethscan/ftp.py:40`, `ethscan/ldap.py:143`, `ethscan/netbios.py:127`,
    `ethscan/smb.py:179`, `ethscan/smtp.py:55`, `ethscan/mysql.py:45`,
    `ethscan/mongodb.py:46`, `ethscan/oracle.py:47`,
    `ethscan/postgresql.py:67`, `ethscan/mssql.py:205`);
  - `ethscan/web.py:49` and `ethscan/web.py:52` (`parsed.port` in
    `_parse_url`), which is what `headers`, `web` and `urlcheck` go
    through;
  - `ethscan/ssh.py:116` (`parsed.port` in `_extract_port`).
- **Fix**: catch that `ValueError` at each site and re-raise it as
  `TargetSpecError` - the type already exists in `ethscan/target.py` and
  already means "this target string cannot be used". **Preserve the
  original message text** (`str(exc)`) so the five graceful commands and
  `s3` keep reporting the identical string inside their output.
- **CLI**: the nine protocol commands already carry the
  `_target_usage_errors` decorator, so they need **no CLI change at all**.
  `headers`, `web`, `urlcheck` and `ssh` need the same decorator added.
- Do **not** change the working forms: `host`, `host:443`, `http://host`,
  `https://host:8443`, `[::1]:443`. In particular
  `ethscan/web.py:_parse_url` currently maps an empty host to
  `"localhost"`, and `ssh.py:_extract_host` lowercases the host - both
  must stay as they are.
- Do **not** change `--port` handling, and do **not** bundle in the other
  traceback clusters listed below.

### Verification
- New tests asserting exit code 2, an
  `Error: Invalid value for '--target': ...` message and the absence of a
  traceback for each affected command, with targets such as
  `redis://host:notaport`, `https://host:notaport` and `host:notaport`.
- A regression test that the valid target forms are still accepted and
  behave exactly as before, and that the five probe-failure commands plus
  `s3` still exit 0 with the **unchanged** error string inside their
  output.
- `python -m pytest tests/test_cli.py -q` and the full suite.
- `python -m ruff check ethscan tests` must stay at 48 pre-existing errors
  with no new ones.
- A before/after CLI harness over the affected commands x a set of target
  values to prove the valid cases are byte-identical. The harness used for
  the last two sessions is at `/tmp/target_harness.py`; a pristine copy of
  the base tree can be recreated with
  `git archive HEAD | tar -x -C /tmp/ethscan_before`.

## Other traceback clusters (found, re-verified, not fixed - do not bundle them in)
A survey of every command with hostile option values found these remaining
raw-traceback defects. They are separate tasks; pick one at a time.
- `headers`, `web`, `fuzz`, `urlcheck`, `s3` with a `--target` containing a
  space -> `http.client.InvalidURL: URL can't contain control characters`.
  `fuzz` with a non-numeric port in a URL is a third variant of the same
  family: `http.client.InvalidURL: nonnumeric port: 'notaport'` (raised by
  `http.client`, not by `urllib.parse`).
- `ping`, `geo`, `dnssec`, `vuln`, `osdetect`, `service`, `scan`, `smtp`,
  `ftp`, `ssh`, `s3` with an unresolvable host -> `socket.gaierror` or
  `encoding with 'idna' codec failed`. These are network-dependent, so they
  need a different decision: a failed DNS lookup is arguably a probe result
  (exit 0 with an error field) rather than a usage error.
- `trace` with `--target ''` -> `ValueError: Invalid target`
  (`ethscan/trace.py:79`).
