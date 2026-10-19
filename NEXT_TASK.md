# NEXT_TASK.md

## Status (2026-10-19T23:40:00Z)
- Prior agent task (a `--target` whose **port is not a number** -> click
  usage error): **complete**.
- Prior agent tasks (invalid `--ports`, invalid CIDR, unusable `--target`)
  were already complete when this session started.
- Verified: 289-invocation CLI harness, 234 byte-identical, 43 exactly the
  intended traceback -> usage-error conversions, 0 unexpected differences;
  full suite 4129 passed / 1 skipped; ruff rule set identical to the
  baseline (48 pre-existing errors).

## Next task (bounded, high-value)

A `--target` whose **host contains a space or a control character** still
crashes with a raw Python traceback. Make it a clean click usage error
(exit code 2), reusing the machinery this project already has
(`TargetSpecError` in `ethscan/target.py`, `_target_usage_errors` in
`ethscan/cli.py`).

Evidence (re-verified on `main` at this commit, after the non-numeric-port
work above):
```
$ python -m ethscan web --target "host name"
...
http.client.InvalidURL: URL can't contain control characters. 'host name' (found at least ' ')   # traceback, exit 1
```
Reproduces for `headers`, `web`, `fuzz`, `urlcheck` and `s3`:
```
$ python -m ethscan headers --target "host name"
$ python -m ethscan fuzz    --target "host name"
$ python -m ethscan urlcheck --target "host name"
$ python -m ethscan s3      --target "host name"
```
For `s3` the quoted host is the *derived* bucket name
(`'host name-backups.s3.amazonaws.com'`), because `s3` turns the target
host into candidate bucket names.

### Origin
`http.client._validate_host` (CPython 3.12,
`/usr/lib/python3.12/http/client.py:1318`) raises
`http.client.InvalidURL` when the host contains a character matched by
`_contains_disallowed_url_pchar_re` (`[\x00-\x20\x7f]`, i.e. control
characters, space and DEL). `InvalidURL` derives from `HTTPException`,
**not** from `ValueError`, so the existing `except ValueError` handlers in
the library do not catch it.

Reachability per command:
- `headers`, `web`, `urlcheck`: `ethscan/web.py:_parse_url` ->
  `fetch_headers` -> `urllib.request.urlopen` ->
  `http.client.HTTPConnection.__init__` -> `_validate_host`.
- `fuzz`: `ethscan/fuzz.py:_normalize_base_url` (which builds
  `f"{parsed.scheme}://{parsed.netloc}"`) -> `fuzz_path` -> `urlopen`.
- `s3`: `ethscan/s3.py` builds `https://<bucket>.s3.amazonaws.com/` from
  the target host -> `check_bucket_public` -> `urlopen`.

### Scope
- **Fix**: validate the *host* the module parsed out of the target and
  raise `TargetSpecError` when it contains a character outside
  `[^\x00-\x20\x7f]`. Put the check in `ethscan/target.py` next to
  `url_port` (for example a `check_target_host(host)` helper) so there is
  a single rule, and call it from the three places that turn a target into
  a host: `ethscan/web.py:_parse_url`, `ethscan/fuzz.py:_normalize_base_url`
  and `ethscan/s3.py:_normalize_host`.
- **CLI**: `web`, `headers` and `urlcheck` already carry
  `@_target_usage_errors`. `fuzz` and `s3` need it added.
- Decide the message deliberately and write it down: either preserve
  `str(exc)` of the `InvalidURL` (which differs per command because `s3`
  quotes a derived bucket name), or use one stable message such as
  `"Target host contains a space or control character"`. Prefer the
  stable message for `s3`; say which one was chosen in `TASK.md`.
- **Adjacent variant, same family** (decide whether to include it):
  `fuzz` hands the whole URL to `http.client`, so a non-numeric port in a
  `fuzz` target raises a *different* `InvalidURL`:
  ```
  $ python -m ethscan fuzz --target "https://host:notaport"
  http.client.InvalidURL: nonnumeric port: 'notaport'
  ```
  Validating the parsed netloc in `ethscan/fuzz.py:_normalize_base_url`
  (host **and** port) covers both fuzz variants in one place.
- Do **not** change the working forms: `host`, `host:443`,
  `http://host`, `https://host:8443`, `[::1]:443`. `web.py:_parse_url`
  maps an empty host to `"localhost"`, `ssh.py:_normalize_host` lowercases
  the host, and `s3.py` lowercases the host - all three must stay as they
  are.
- Do **not** change `--port` handling, and do **not** bundle in the other
  traceback clusters listed below.

### Verification
- New tests asserting exit code 2, an
  `Error: Invalid value for '--target': ...` message and the absence of a
  traceback for each affected command, with targets such as
  `"host name"`, `"host\tname"` and `"https://host name"`.
- A regression test that the valid target forms are still accepted and
  behave exactly as before (host, host:port, scheme URLs, bracketed IPv6),
  and that `s3` and `fuzz` still exit 0 for a normal target.
- `python -m pytest tests/test_cli.py -q` and the full suite.
- `python -m ruff check ethscan tests` must stay at 48 pre-existing errors
  with no new ones.
- A before/after CLI harness over the affected commands x a set of target
  values to prove the valid cases are byte-identical. The harness used for
  the last two sessions is at `/tmp/port_harness.py`; a pristine copy of the
  base tree can be recreated with
  `git archive HEAD | tar -x -C /tmp/ethscan_before`.
  Note: `s3` invocations make real AWS requests and are **not reproducible
  between two runs of the same tree** - capture the baseline twice and
  exclude the invocations that differ between the two baseline runs.

## Other traceback clusters (found, re-verified, not fixed - do not bundle them in)
A survey of every command with hostile option values found these remaining
raw-traceback defects. They are separate tasks; pick one at a time.
- `ping`, `geo`, `dnssec`, `vuln`, `osdetect`, `service`, `scan`, `smtp`,
  `ftp`, `ssh`, `s3` with an unresolvable host -> `socket.gaierror` or
  `encoding with 'idna' codec failed`. These are network-dependent, so they
  need a different decision: a failed DNS lookup is arguably a probe result
  (exit 0 with an error field) rather than a usage error.
- `trace` with `--target ''` -> `ValueError: Invalid target`
  (`ethscan/trace.py:79`). Small and self-contained: `trace` has no
  `--target` usage-error handling at all yet.
