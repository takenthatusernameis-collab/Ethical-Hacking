# HANDOFF: state for the next agent

## What changed this session

The previous handoff closed the sweep of the text-protocol and HTTP *answer
parsers* and recorded that "the binary-protocol sweep and the text/HTTP sweep
together cover every parser in `ethscan/`". That is true of the parsers, but
the sweep never looked at the code that **receives** an answer. A client
library raises exception types that the module's guard does not list, and
those types escape as a traceback. Four modules had that gap.

- **`ethscan/ftp.py`** (`run_ftp`): `ftplib` raises four types that the
  module's guard did not name:
  - `EOFError` when the server closes the connection before the greeting
    (`ftp.py:141`, the connect phase);
  - `EOFError` when the server closes the connection instead of answering
    `USER` (`ftp.py:160`, the login phase);
  - `ConnectionResetError` (a bare `OSError`) when the server resets the
    connection during the login (`ftp.py:164`);
  - `UnicodeDecodeError` (a `ValueError`) when the answer to `USER` holds a
    byte that is not UTF-8 (`ftp.py:164`).

  The connect phase now reports `connection failed: ...`, the login phase
  reports `login failed: ...` and leaves `anonymous_login` at `None` (the
  outcome is unknown, not "refused"). The banner read is guarded as well.
- **`ethscan/web.py`** (`fetch_headers`), **`ethscan/cve.py`**
  (`_fetch_cve_data`) and **`ethscan/subtake.py`** (`check_http_fingerprint`):
  `http.client.BadStatusLine` derives from `http.client.HTTPException` and
  not from `OSError` or `ValueError`, so it escaped every guard that did not
  name it. The repository already knew this trap -- `ethscan/fuzz.py:94` and
  `ethscan/s3.py:308` catch `http.client.HTTPException` and say why in a
  comment. The three modules now return the failure signal they already use
  for an unreachable server (`{}`, `None`, `None`).
- **`tests/test_ftp.py`**: a `socketserver`-based fake FTP server (the
  pattern of `tests/test_smtp.py`) with six modes, and 6 regression tests.
- **`tests/test_web.py`**, **`tests/test_cve.py`**, **`tests/test_subtake.py`**:
  a fake HTTP server that answers with a malformed status line, and 4
  regression tests.
- **`tests/test_option_sweep.py`**: `subdomains` resolves every candidate
  subdomain and waits for the full DNS timeout, so the sweep gave it a
  longer per-invocation timeout (`DNS_COMMANDS`, 20s). The command stays in
  the sweep, so the guarantee is unchanged.

## What was actually verified

- Reproduction before the fix, over real sockets: a server that closes
  without a greeting, one that closes during the login, one that resets the
  connection and one that answers `USER` with `0xff` made `run_ftp()` raise
  `EOFError`, `EOFError`, `ConnectionResetError` and `UnicodeDecodeError`.
  `ethscan ftp --target 127.0.0.1 --port <port>` printed `Aborted!` and
  exited 1 (click turns the unhandled exception into an `Abort`). After the
  fix the same answers produce a report and exit 0.
- A server that answers `NOT-HTTP garbage\r\n\r\n` made
  `web.fetch_headers`, `cve._fetch_cve_data` and
  `subtake.check_http_fingerprint` raise `http.client.BadStatusLine`. After
  the fix they return `{}`, `None` and `None`, and `ethscan web` /
  `ethscan headers` print a report and exit 0.
- 8 of the 10 new tests fail on the unfixed modules (`git stash push --
  ethscan/ftp.py ethscan/web.py ethscan/cve.py ethscan/subtake.py`): 4 with
  `EOFError`/`ConnectionResetError`/`UnicodeDecodeError` and 4 with
  `http.client.BadStatusLine`. The other 2 are controls that pin the normal
  answer (a successful and a refused login).
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/test_ftp.py tests/test_web.py tests/test_cve.py
  tests/test_subtake.py -q` -> **201 passed**.
- `python -m pytest -q` -> **4584 passed, 48 skipped, 2 warnings**
  (was 4574).
- `git diff --check` -> clean.

## The class of bug, stated once

Every bug of the last three sessions has the same shape: **the module's
guard names the exception types it expects, and the code raises a type that
is not on the list.**

| Session | Module | Type that escaped |
| --- | --- | --- |
| netbios | `netbios.py` | `IndexError` on a short name |
| smtp | `smtp.py` | `ValueError` from `int()` on a non-decimal digit string |
| dns | `subtake.py`, `subdomains.py` | `IndexError` on an empty answer set |
| this session | `ftp.py` | `EOFError`, `OSError`, `ValueError` from `ftplib` |
| this session | `web.py`, `cve.py`, `subtake.py` | `http.client.HTTPException` |

So the question to ask of every module is not "does the parser handle a
hostile answer?" but **"which exception types can the code that produces the
answer raise, and are all of them on the list the guard names?"** The answer
for a module that wraps a client library is *the exception set of that
library*:

- `ftplib`: `ftplib.Error`, `EOFError`, `OSError`, `UnicodeDecodeError`
  (a `ValueError`), `socket.timeout` (an `OSError`).
- `http.client`/`urllib`: `urllib.error.HTTPError` (an `OSError`),
  `urllib.error.URLError` (an `OSError`), `http.client.HTTPException`
  (`BadStatusLine`, `IncompleteRead`, `InvalidURL`, ...), `OSError`,
  `ValueError`, `json.JSONDecodeError` (a `ValueError`).
- `dnspython`: `dns.exception.DNSException` (and every subclass:
  `Timeout`, `NoAnswer`, `NoNameservers`, `NoRootSOA`, `LifetimeTimeout`,
  `FormError`), `OSError` (`socket.gaierror`), `ValueError` (a bad name),
  and `IndexError` (an empty answer set -- found and fixed by the previous
  session).
- `paramiko`: `paramiko.SSHException` (and `AuthenticationException`), plus
  `socket.timeout` and `OSError`.

### Approaches that failed and why

- **Random / byte-level fuzzing does NOT find this class of bug** (recorded
  by the previous session and still true). The fuzzer was pointed at the
  *known* netbios bug and did not find it: the bug needs a structurally valid
  short name, and a random mutation of a valid packet almost never produces
  one.
- **A generic "feed hostile bytes to every parser" probe does not find it
  either.** It only reports parsers that raise, and every one of them except
  netbios raised the `ValueError` their caller catches.
- **Reading the parser is not enough either.** This session's four bugs were
  invisible to the parser sweeps: the FTP and HTTP ones are in the *client
  library's* error handling, not in the parser. The sweeps looked at the
  wrong layer. What works is: pick the library the module wraps, list the
  exception types that library can raise, and compare that list with the
  guard.

## What remains unresolved

- **dnspython and paramiko are not checked yet.** The guards of the
  dnspython users are `(dns.exception.DNSException, OSError, ValueError)`
  and the guard of the paramiko path in `ssh.py` is `except Exception`; the
  stdlib path of `run_ssh` guards `(socket.timeout, OSError, struct.error)`.
  They are probably fine, but "probably" is not a check. See the next task.
- **`run_smtp()` is the only `run_<module>()` of a protocol module that has
  an `except` net around its probe block.** The other protocol modules
  without one (`run_redis`, `run_memcached`, `run_ntp`, `run_ldap`,
  `run_smb2`/`run_smb`, `run_snmp`, `run_dnssec`, `run_ssh`) are clean
  today, but a future parser bug in them crashes the command instead of
  being reported. Adding the net is a behaviour change and was deliberately
  left out of this session's small fix.
- **The commit before the netbios fix (`91ce9aa`, empty message) is still
  untested.** It made `cert`, `cve`, `geo`, `jwt` and `mac` decode their HTTP
  responses with `errors="replace"`. The only behavioural difference is
  `mac`: a body with a byte that is not UTF-8 now yields the replaced text
  as the vendor instead of a failed fetch. There is no test for it. It is not
  worth a rework; a single regression test for the `mac` vendor text would be
  enough to close it.
- **The file-input surface is exhausted**: the file-option, file-content,
  config-value and cache-content sweeps cover it, and no strict `open(...)`
  read is left in `ethscan/`.

## One precise next task

**Sweep the two client libraries that are not checked yet (dnspython and
paramiko) for the same class of bug: an exception type the library raises
that the module's guard does not list.**

The method (it is the one that found the four bugs of this session):

1. Write a fake library module on `sys.path` -- the previous session already
   did this for `dns` (a package whose `Resolver.resolve` returns what the
   test needs) -- that raises **one** exception type of the library.
2. Call the module's `run_<module>` (or the helper that calls the library)
   with it.
3. Assert that the call returns the module's documented failure signal and
   does not raise.

For dnspython, the types to try are the ones the guard does not name:
`IndexError` (the previous session found it in two answer-set sites and
added it to the guard *there* -- check whether any other call site still
indexes an answer set), `AttributeError`, `KeyError` and a bare
`socket.gaierror` (an `OSError`, so covered). For paramiko, the types are
`paramiko.SSHException`, `paramiko.AuthenticationException` (a subclass of
it) and `EOFError`; the paramiko path in `ssh.py` is already wrapped in
`except Exception`, so the check must confirm that the *stdlib* path in
`run_ssh` cannot raise one of them.

`paramiko` is not installed in this environment, so a fake module is the
only way to exercise it. Encode the result as a permanent test next to the
module's own tests, and fix a module only if a call site really escapes.

Constraints: keep the smallest reversible change (turn the crash into the
module's documented error signal), add the regression test next to the
module's own tests, and do not weaken an existing guard. The `ftp` and
`web`/`cve`/`subtake` fixes are the template: the crash becomes the
module's own failure signal, and the guard gains exactly the type that was
missing.
