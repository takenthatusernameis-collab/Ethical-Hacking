# NEXT TASK

## Status: COMPLETE (CLI-level sweep extended to the last twelve commands)

The task of the previous handoff is done: the permanent CLI-level sweep now
covers the twelve commands that still had no failure-field check at the
command line (`redis`, `memcached`, `ntp`, `ldap`, `smb`, `snmp`, `ssh`,
`dnssec`, `ssl`, `tls`, `whois` and `service`), each of them printing its own
error field and exiting 0.

1. **The twelve commands were verified through the CLI.** With the transport
   seam patched to raise a `RuntimeError("hostile transport")`:
   - `redis`/`memcached`/`ldap`/`smb` -> `accessible=false`,
     `error="<module> probe failed: hostile transport"`;
   - `ntp` -> `time_response=null`, `error="ntp probe failed: ..."`;
   - `snmp` -> `communities=[]`, `error="snmp probe failed: ..."`;
   - `ssh` -> `banner=null`, `error="ssh probe failed: ..."`;
   - `ssl` -> `cert=null`, `valid=false`, `error="hostile transport"`;
   - `tls` -> every version and cipher `supported=false` with its error;
   - `whois` -> `raw=""`, `error="Connection failed: ..."`;
   - `service` -> `services_found=0`, `results=[]`;
   - `dnssec` -> `validated=false`, `dnskey.error="dnssec probe failed: ..."`.
   All exit 0.

2. **The result is a permanent sweep.** `tests/test_cli_unreachable_sweep.py`
   grew from 16 to 28 checks. The new checks patch the socket seam the
   module really opens (the command line never injects a connector), run the
   command through `CliRunner` and assert exit 0, no traceback and the
   command's own failure signal. It is hermetic: no network is needed and
   the result does not depend on what the machine can reach.

3. **The checks are meaningful.** All twelve were proved by reverting the
   guard of their own module (narrowing the broad `except Exception` to
   `except ValueError`, or dropping `RuntimeError` from the caught tuple)
   and watching the matching check fail. With the guards restored all 28
   pass.

`python -m ruff check ethscan/ tests/` -> All checks passed.
`python -m pytest tests/` -> **5072 passed, 48 skipped, 2 warnings** (baseline
5060 passed, 48 skipped; the +12 are the new CLI checks). `git diff --check`
clean. Nothing is committed.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash
  into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task

Extend the permanent CLI-level sweep to the HTTP-facing commands, the last
group of network commands without a failure-field check at the command line:
`web`, `headers`, `fuzz`, `urlcheck`, `cert`, `geo`, `mac`, `s3`, `cve` and
`subtake`.

The method is the one of `tests/test_cli_unreachable_sweep.py`: patch the
transport the module really uses (here `urllib.request.urlopen`, patched
globally exactly as `tests/test_http_hostile_sweep.py` does; `urlcheck` also
runs the TLS probe of `ethscan.ssl`, so it needs
`ethscan.ssl.socket.create_connection` as well), run the command through
`CliRunner`, and assert that it exits 0, leaks no traceback and prints the
module's own failure signal. `cve` and `subtake` report a failed lookup as
a missing entry instead of an error field, so assert the signal the module
documents, not a fixed wording.

The list of the commands that still have no such check is in
`HANDOFF_NEXT.md` under "What remains unresolved".
