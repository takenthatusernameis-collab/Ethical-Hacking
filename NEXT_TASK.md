# NEXT TASK

## Status: COMPLETE (ftp + http: a hostile server answer no longer crashes the command)

1. **FTP** (`ethscan/ftp.py`): `run_ftp()` no longer raises on a hostile
   answer. `ftplib` raises `EOFError` (the server closes the connection), a
   bare `OSError` (`ConnectionResetError` when the server resets it) and a
   `UnicodeDecodeError` (a `ValueError`, when the answer is not text); none of
   them was in the module's guard.
   - The connect phase reports `connection failed: server closed the
     connection` / `connection failed: <reason>`.
   - The login phase reports `login failed: <reason>` and leaves
     `anonymous_login` at `None` (the outcome is unknown, not "refused").
2. **HTTP** (`ethscan/web.py`, `ethscan/cve.py`, `ethscan/subtake.py`):
   `http.client.BadStatusLine` derives from `http.client.HTTPException` and
   not from `OSError` or `ValueError`, so it escaped every guard that did not
   name it. `fetch_headers`, `_fetch_cve_data` and `check_http_fingerprint`
   now return the failure signal the module already uses for an unreachable
   server (`{}`, `None`, `None`).
3. **Regression tests added**: 10 (6 in `tests/test_ftp.py`, 2 in
   `tests/test_web.py`, 1 in `tests/test_cve.py`, 1 in `tests/test_subtake.py`).
   8 of them fail on the unfixed modules, 2 are controls.
4. **De-flake**: `tests/test_option_sweep.py` gave `subdomains` a longer
   per-invocation timeout (`DNS_COMMANDS`); the command resolves every
   candidate subdomain and waits for the full DNS timeout.

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
- The 8 new tests that must fail do fail on the unfixed modules
  (`git stash push -- ethscan/ftp.py ethscan/web.py ethscan/cve.py
  ethscan/subtake.py`).
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python -m pytest tests/test_ftp.py tests/test_web.py tests/test_cve.py
  tests/test_subtake.py -q` -> 201 passed.
- `python -m pytest -q` -> 4584 passed, 48 skipped, 2 warnings (was 4574).
- `git diff --check` -> clean.

## Next agent

### The gap that this session found (read this first)

The previous handoff closed the *parser* sweep ("every parser in `ethscan/`")
and that claim was correct about the parsers but wrong about the *receivers*:
a client library raises exception types that the module's guard does not
list, and those types escape as a traceback. The modules that use a client
library and their guards are now:

| Module | Library | Guard | State |
| --- | --- | --- | --- |
| `ftp.py` | `ftplib` | `ftplib.Error`, `OSError`, `ValueError` (+`EOFError` now) | fixed this session |
| `web.py` | `urllib`/`http.client` | `HTTPError`, `URLError`, `OSError`, `ValueError` (+`HTTPException` now) | fixed this session |
| `cve.py` | `urllib`/`http.client` | `OSError`, `ValueError` (+`HTTPException` now) | fixed this session |
| `subtake.py` | `urllib`/`http.client` | `URLError`, `HTTPError`, `OSError`, `ValueError` (+`HTTPException` now) | fixed this session |
| `fuzz.py` | `urllib`/`http.client` | `HTTPError`, `HTTPException`, `URLError`, `OSError`, `ValueError` | already complete |
| `s3.py` | `urllib`/`http.client` | `HTTPError`, `HTTPException`, `URLError`, `OSError` | already complete |
| `cert.py`, `geo.py`, `mac.py` | `urllib`/`http.client` | `except Exception` | complete by construction |
| `ssh.py` | `paramiko` (host key) and raw sockets | `except Exception` (paramiko path), `OSError`/`struct.error`/`UnicodeDecodeError` (stdlib path) | **not checked this session** |
| `dns.py`, `dnssec.py`, `resolve.py`, `subtake.py`, `subdomains.py`, `stale.py`, `dnsbrute.py` | `dnspython` | `dns.exception.DNSException`, `OSError`, `ValueError` (+`IndexError` in two sites since the previous session) | **not checked this session** |

### One precise next task

**Sweep the two client libraries that are not checked yet (dnspython and
paramiko) for the same class of bug: an exception type the library raises
that the module's guard does not list.**

The method that works (it is the one that found the four bugs of this
session) is *not* fuzzing and *not* reading the parser. It is:

1. Write a fake library module (the previous session already did this for
   `dns`: a package on `sys.path` whose `Resolver.resolve` returns what the
   test needs) that raises **one** exception type of the library.
2. Call the module's `run_<module>` (or the helper that calls the library)
   with it.
3. Assert that the call returns the module's documented failure signal and
   does not raise.

For dnspython the candidate types to try are the ones the guard does not
name: `dns.exception.Timeout` and `dns.resolver.NoAnswer` are `DNSException`
subclasses (covered), so look at what is *not*: `IndexError` (the previous
session found it in two sites and added it to the guard there -- check
whether any other call site still indexes an answer set), `AttributeError`,
`KeyError` and a plain `socket.gaierror` (an `OSError`, covered). For
paramiko the candidate types are `paramiko.SSHException`,
`paramiko.AuthenticationException` (a subclass of it) and `EOFError`; the
paramiko path in `ssh.py` is already wrapped in `except Exception`, so the
check must confirm that the *stdlib* path in `run_ssh` cannot raise one of
them.

Encode the result as a permanent test next to the module's own tests (a fake
`dns` package is enough; `paramiko` is not installed in this environment, so
a fake module is the only way to exercise it), and fix a module only if a
call site really escapes.

### The second candidate (a behaviour change, deliberately not done here)

`run_smtp()` is the only `run_<module>()` of a protocol module that has an
`except` net around its probe block; the other protocol modules without one
are `run_redis`, `run_memcached`, `run_ntp`, `run_ldap`, `run_smb2`/`run_smb`,
`run_snmp`, `run_dnssec` and `run_ssh`. They are clean today, but a future
parser bug in them crashes the command instead of being reported. Adding the
net (the `smtp` template: `except Exception as exc: results["error"] = f"...
probe failed: {exc}"`) is a behaviour change, so it was left out of this
session's small fix.

### The third candidate (a one-line close-out)

The commit before the netbios fix (`91ce9aa`, empty message) made `cert`,
`cve`, `geo`, `jwt` and `mac` decode their HTTP responses with
`errors="replace"`. The only behavioural difference is `mac`: a body with a
byte that is not UTF-8 now yields the replaced text as the vendor instead of
a failed fetch. There is no test for it. A single regression test for the
`mac` vendor text is enough to close it.
