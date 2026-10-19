# NEXT_TASK.md

## Status (2026-10-19T23:55:00Z)
- Prior agent task (a `--target` whose **host contains a space or a control
  character** -> click usage error): **complete**.
- Prior agent tasks (non-numeric port, invalid `--ports`, invalid CIDR,
  unusable `--target`) were already complete when this session started.
- Verified: 320-invocation CLI harness, 288 byte-identical, 16 exactly the
  intended conversions, 0 differences caused by the change; full suite
  4159 passed / 1 skipped; ruff rule set identical to the baseline (48
  pre-existing errors).

## Next task (bounded, high-value)

The **path and query** of a `--target` are still not validated. A target
whose path contains a space or a control character still crashes with a
raw Python traceback. Make it a clean click usage error (exit code 2),
reusing the machinery this project already has (`TargetSpecError` and
`check_target_host` in `ethscan/target.py`, `_target_usage_errors` in
`ethscan/cli.py`).

Evidence (re-verified on `main` at this commit, after the hostile-host
work above):
```
$ python -m ethscan web --target "https://example.com/a b"
...
http.client.InvalidURL: URL can't contain control characters. '/a b' (found at least ' ')   # traceback, exit 1

$ python -m ethscan headers --target "https://example.com/?q=a b"
http.client.InvalidURL: URL can't contain control characters. '/?q=a b' (found at least ' ')

$ python -m ethscan urlcheck --target "https://example.com/a b"
http.client.InvalidURL: URL can't contain control characters. '/a b' (found at least ' ')
```
`fuzz` is **not** affected: `_normalize_base_url` keeps only
`scheme://netloc`, so the path is never sent. A percent-encoded path
(`https://example.com/a%20b`) already works and must keep working.

### Origin
`http.client.HTTPConnection.putrequest` -> `_validate_path` refuses a
request target that contains a character matched by
`_contains_disallowed_url_pchar_re` (`[\x00-\x20\x7f]`, i.e. the control
characters, the space and DEL) with
`InvalidURL("URL can't contain control characters. %r")`. `InvalidURL`
derives from `HTTPException`, **not** from `ValueError`, so the existing
`except ValueError` handlers in the library do not catch it.

Reachability per command:
- `web`, `headers`, `urlcheck`: the **raw** target is what is sent -
  `web.run_web_checks` and `headers.run_headers` build the request URL
  from `target.strip()` (`ethscan/web.py:230`, `ethscan/headers.py:21`),
  and `urlcheck` reaches the same code through `run_web_checks`. The host
  of that URL is already validated by `check_target_host` (previous
  session); the path and the query are not.
- `fuzz`: unaffected, the path is dropped by `_normalize_base_url`.

### Scope
- **Fix**: validate the **path and query** of the raw target the same way
  the host is validated today, and raise `TargetSpecError` when they
  contain a character matched by `[\x00-\x20\x7f]`. Put the rule next to
  `check_target_host` in `ethscan/target.py` - the extraction helper
  `_host_of(target)` already splits a raw target into scheme, authority,
  path, query and fragment, so the natural shape is a second helper
  (for example `check_target_path(target)`) that reuses it, or one
  combined helper that checks the whole URL. Decide and write the choice
  down in `TASK.md`.
- **Message**: the previous session chose the **stable** message over
  `str(exc)` of the `InvalidURL`, because the raw text quotes the derived
  value that is actually sent. Keep that discipline here; a message such
  as `"Target path contains a space or control character"` fits the
  existing one. The commands must all report the **same** one line.
- The **fragment** (`#...`) is never sent to the server, so it must not be
  rejected; the **userinfo** and the **port** are part of the authority and
  are already covered by `check_target_host` and `url_port`.
- Do **not** change the working forms: `host`, `host:443`, `http://host`,
  `https://host:8443`, `[::1]:443`, `https://example.com/path`,
  `https://example.com/a%20b`, `https://example.com/?q=1`. The
  empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- Do **not** bundle in the other clusters listed below.

### Verification
- New tests asserting exit code 2, an
  `Error: Invalid value for '--target': ...` message and the absence of a
  traceback for `web`, `headers` and `urlcheck`, with targets such as
  `"https://example.com/a b"`, `"https://example.com/a\tb"` and
  `"https://example.com/?q=a b"`.
- A regression test that the valid target forms are still accepted and
  behave exactly as before, including a percent-encoded path and a target
  with a fragment.
- `python -m pytest tests/test_cli.py -q` and the full suite.
- `python -m ruff check ethscan tests` must stay at 48 pre-existing errors
  with no new ones.
- A before/after CLI harness over the affected commands x a set of target
  values to prove the valid cases are byte-identical. The harness used for
  the last three sessions is at `/tmp/host_harness.py`, with
  `/tmp/compare_host_harness.py` for the comparison; a pristine copy of
  the base tree can be recreated with
  `git archive HEAD | tar -x -C /tmp/ethscan_before`.
  Note: `s3` invocations make real AWS requests and are **not reproducible
  between two runs of the same tree** - capture the baseline twice and
  exclude the invocations that differ between the two baseline runs. The
  `s3` command also has a pre-existing non-deterministic crash for a
  bracketed IPv6 target (see below); do not count it as a regression.

## Other traceback clusters (found, re-verified, not fixed - do not bundle them in)
A survey of every command with hostile option values found these remaining
raw-traceback defects. They are separate tasks; pick one at a time.
- `s3` with a bracketed IPv6 target (`--target "[::1]:443"`) ->
  `http.client.InvalidURL: nonnumeric port: '1.s3.amazonaws.com'`. The
  derived bucket names keep the `:`, so the bucket URL is malformed. The
  message is **non-deterministic**: `run_s3` probes the candidates
  concurrently and re-raises whichever exception finishes first, so eight
  runs of the unchanged tree produce four different tracebacks. Two
  things to decide: which bucket names are usable, and whether a failed
  probe should be reported inside the result instead of escaping the
  thread pool.
- `ping`, `geo`, `dnssec`, `vuln`, `osdetect`, `service`, `scan`, `smtp`,
  `ftp`, `ssh`, `s3` with an unresolvable host -> `socket.gaierror` or
  `encoding with 'idna' codec failed`. These are network-dependent, so they
  need a different decision: a failed DNS lookup is arguably a probe result
  (exit 0 with an error field) rather than a usage error.
- `trace` with `--target ''` -> `ValueError: Invalid target`
  (`ethscan/trace.py:79`). Small and self-contained: `trace` has no
  `--target` usage-error handling at all yet.
