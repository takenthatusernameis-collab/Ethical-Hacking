# NEXT_TASK.md

## Status (2026-10-19T19:35:00Z)
- Prior agent task (a `--target` whose **host contains a space or a control
  character** -> click usage error): **complete**.
- Prior agent tasks (non-numeric port, invalid `--ports`, invalid CIDR,
  unusable `--target`) were already complete when this session started.
- This session's task (a `--target` whose **path or query contains a space
  or a control character** -> click usage error): **complete**.
- Verified: 4189 passed / 1 skipped; ruff rule set identical to the baseline
  (48 pre-existing errors, no new ones).

## Remaining tasks (bounded, high-value)

### 1. `trace` with an empty target -> `ValueError: Invalid target`
`ethscan/trace.py:79` raises a raw `ValueError` for `--target ''`.
`trace` has no `--target` usage-error handling at all yet. Small and
self-contained: add a `check_target` helper (or reuse the existing
machinery) and attach the `_target_usage_errors` decorator to the `trace`
command in `ethscan/cli.py`.

### 2. `s3` with a bracketed IPv6 target -> `http.client.InvalidURL:
nonnumeric port: '1.s3.amazonaws.com'`
`--target "[::1]:443"` crashes because the derived bucket names keep the
`:`. The message is **non-deterministic**: `run_s3` probes the candidates
concurrently and re-raises whichever exception finishes first, so eight
runs of the unchanged tree produce four different tracebacks. Two things
to decide: which bucket names are usable, and whether a failed probe
should be reported inside the result instead of escaping the thread pool.

### 3. Network-dependent commands with an unresolvable host
`ping`, `geo`, `dnssec`, `vuln`, `osdetect`, `service`, `scan`, `smtp`,
`ftp`, `ssh`, `s3` with an unresolvable host -> `socket.gaierror` or
`encoding with 'idna' codec failed`. These need a different decision: a
failed DNS lookup is arguably a probe result (exit 0 with an error field)
rather than a usage error.

## Verified working forms (do not break)
- `host`, `host:443`, `http://host`, `https://host:8443`, `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.