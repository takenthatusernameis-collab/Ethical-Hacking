# TASK

Status: COMPLETE (ftp + http: a hostile server answer no longer crashes the command)

## What was done

The previous handoff closed the text-protocol and HTTP *parser* sweep and
declared that every parser in `ethscan/` was covered. That claim was wrong
for a second reason than the one it had already fixed: the sweeps read the
code that **parses** an answer, but not the code that **receives** it. A
client library raises exception types that the module's guard does not list,
and those types escape as a traceback. Four modules had that gap, and every
one of them is reachable with the default options.

### FTP (`ethscan/ftp.py`)

`run_ftp()` guards the session with `except ftplib.Error` (and, for the
connect, `OSError`/`ValueError`). `ftplib` raises three more types for a
server that misbehaves, and all three escaped:

| Hostile answer | Exception ftplib raises | Where |
| --- | --- | --- |
| closes the connection before the greeting | `EOFError` | `ftp.py:141` (connect) |
| closes the connection instead of answering `USER` | `EOFError` | `ftp.py:160` (login) |
| resets the connection instead of answering `USER` | `ConnectionResetError` (an `OSError`) | `ftp.py:164` (login) |
| answers `USER` with a byte that is not UTF-8 | `UnicodeDecodeError` (a `ValueError`) | `ftp.py:164` (login) |

`ethscan ftp --target <host>` against such a server printed `Aborted!` and
exited 1 (click turns the unhandled exception into an `Abort`). The banner
read had the same gap and is now guarded as well.

The module now reports its documented failure signals instead of raising:
`connection failed: server closed the connection` for the connect phase, and
`login failed: ...` with `anonymous_login` left at `None` (the outcome is
unknown, not "refused") for the login phase.

### HTTP (`ethscan/web.py`, `ethscan/cve.py`, `ethscan/subtake.py`)

`http.client.BadStatusLine` (a server that answers with a malformed status
line) derives from `http.client.HTTPException` and not from `OSError` or
`ValueError`, so it escaped every guard that did not name it. The repository
already knew this trap: `ethscan/fuzz.py:94` and `ethscan/s3.py:308` catch
`http.client.HTTPException` with a comment about it. Three modules did not:

- `ethscan/web.py:fetch_headers` -> the `web` and `headers` commands.
- `ethscan/cve.py:_fetch_cve_data` -> the `cve` command.
- `ethscan/subtake.py:check_http_fingerprint` -> the `subtake` command.

All three now return the failure signal the module already uses for an
unreachable server (`{}`, `None`, `None`).

### A flaky test in the sweep suite

`tests/test_option_sweep.py` failed once during this session with
`subdomains --resolver '/nonexistent/path' timed out after 5s`. The command
itself is clean (it resolves every candidate subdomain with `getaddrinfo`, so
it waits for the full DNS timeout when the resolver does not answer). The
command stays in the sweep, but it now gets a longer per-invocation timeout
(`DNS_COMMANDS`), so the guarantee is kept and the flake is gone.

## Verification

- Reproduction before the fix, over real sockets: a server that closes
  without a greeting, one that closes during the login, one that resets the
  connection and one that answers `USER` with `0xff` made `run_ftp()` raise
  `EOFError`, `EOFError`, `ConnectionResetError` and `UnicodeDecodeError`.
  `ethscan ftp --target 127.0.0.1 --port <port>` printed `Aborted!` and
  exited 1.
- A server that answers `NOT-HTTP garbage\r\n\r\n` made
  `web.fetch_headers`, `cve._fetch_cve_data` and
  `subtake.check_http_fingerprint` raise `http.client.BadStatusLine`.
- 8 of the 10 new regression tests fail on the unfixed modules
  (`git stash push -- ethscan/ftp.py ethscan/web.py ethscan/cve.py
  ethscan/subtake.py`): 4 with `EOFError`/`ConnectionResetError`/
  `UnicodeDecodeError` and 4 with `http.client.BadStatusLine`. The other 2
  are controls that pin the normal answer (a successful and a refused login).
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/test_ftp.py tests/test_web.py tests/test_cve.py
  tests/test_subtake.py -q` -> **201 passed**.
- `python -m pytest -q` -> **4584 passed, 48 skipped, 2 warnings**
  (was 4574).
- `git diff --check` -> clean.

## Handoff

See `HANDOFF_NEXT.md` and `NEXT_TASK.md`. The baseline is clean: the fixes,
the tests and the de-flake are committed, nothing else is modified.
