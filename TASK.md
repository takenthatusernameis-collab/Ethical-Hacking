# TASK.md

Date: 2026-10-19T23:45:00Z
Status: the **`s3` bracketed-IPv6 crash** (`http.client.InvalidURL`) is
fixed. `python -m ethscan s3 --target '[::1]:443'` now exits 0 with
per-bucket `error` results and no traceback. A second crash of the same
class (a hostile `--region`) was found and fixed in the same change. The
`--target` leak list is now empty; the next task (a port out of range in
the bare `host:port` form) is prepared in `HANDOFF_NEXT.md` /
`NEXT_TASK.md`.

## What changed
- **`ethscan/s3.py`**
  - `_bucket_name_problem()` (new): reports why a candidate cannot be an
    S3 bucket name (length, uppercase, forbidden characters, leading /
    trailing punctuation, adjacent periods, IPv4-like).
  - `check_bucket_public()`: a name that cannot be an S3 bucket name is
    reported as a failed probe (`error: "Invalid bucket name: ..."`)
    **without** a DNS lookup or an HTTP request; `http.client.
    HTTPException` (e.g. `InvalidURL`) is now caught and reported in
    `error`; the `Request` construction moved inside the `try`.
  - `run_s3()`: the worker wrapper turns any unexpected exception into a
    failed probe result, so one bad candidate can no longer abort the
    whole report; a note is added when no derived candidate is a valid
    bucket name.
- **Tests added**: `tests/test_s3.py` (8 library tests) and
  `tests/test_cli.py` (1 CLI test).

## Verification
- Manual: `python -m ethscan s3 --target '[::1]:443'` -> exit 0, JSON
  with 77 per-bucket `error` results, notes
  "None of the 77 derived bucket names is a valid S3 bucket name.",
  no traceback; markdown and CSV outputs render the same data.
- Manual: `python -m ethscan s3 --target example.com --region 'a b'` ->
  exit 0 (was exit 1 + `InvalidURL` traceback), every probe reports
  "URL can't contain control characters.".
- Manual: `python -m ethscan s3 --target example.com --timeout 2` ->
  exit 0, DNS still resolved, probe failures still reported in `error`.
- Full suite: **4215 passed, 1 skipped** (4207 + 8 new). Ruff: the same
  48 pre-existing errors, no new ones.
- Sweep: all 42 `--target` commands x 4 hostile inputs (`''`,
  `'host name'`, `'no-such-host.invalid'`, `'[::1]:443'`) -> **0 leaked
  tracebacks**. A wider sweep (15 further hostile inputs) is recorded in
  `HANDOFF_NEXT.md` as the source of the next task.

## Remaining
- A port out of range in the **bare** `host:port` form still crashes 7
  commands with `OverflowError` (`redis`, `ldap`, `memcached`, `netbios`,
  `ntp`, `smb`, `snmp`), while the same target with a scheme is already
  reported as a usage error. Details, evidence and the suggested fix are
  in `HANDOFF_NEXT.md`.
- Two further classes of hostile `--target` were found by the wider sweep
  (a host of only dots, and a percent-encoded NUL / userinfo in a URL).
  They are recorded in `HANDOFF_NEXT.md` as backlog.
- The 48 pre-existing ruff errors are unrelated and left alone.
