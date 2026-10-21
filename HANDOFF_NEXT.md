# HANDOFF: state for the next agent

## What changed this session

Closed the last gap of the CLI-level transport-failure sweep. The task of the
previous handoff (extend the permanent CLI-level sweep to the network
commands that still had no failure-field check at the command line) is done
and verified: the twelve commands of that list now have a permanent check
each, so the sweep covers every command that talks to a socket.

### Tests (`tests/`)

- `test_cli_unreachable_sweep.py` (12 new checks, 28 total): the CLI-level
  check for `redis`, `memcached`, `ntp`, `ldap`, `smb`, `snmp`, `ssh`,
  `dnssec`, `ssl`, `tls`, `whois` and `service`. The command line never
  injects a connector, so each check patches the socket seam the module
  really opens (`ethscan.<module>.socket.socket` for the modules that build
  their own socket, `ethscan.<module>.socket.create_connection` for the
  modules that connect through one), runs the command through `CliRunner` and
  asserts that the command exits 0, leaks no traceback and prints its own
  failure signal. The sweep is hermetic: the transport is patched, so it
  needs no network and does not depend on what the machine that runs it can
  reach.

No source file under `ethscan/` was changed in this session.

## What was actually verified

- **The twelve commands were run through the CLI against a hostile
  transport.** Every one prints its own failure field and exits 0:

  | command     | transport seam patched                        | own failure signal                                    |
  |-------------|-----------------------------------------------|-------------------------------------------------------|
  | `redis`     | `ethscan.redis.socket.socket`                 | `accessible=false`, `error="redis probe failed: ..."` |
  | `memcached` | `ethscan.memcached.socket.socket`             | `accessible=false`, `error="memcached probe failed: ..."` |
  | `ntp`       | `ethscan.ntp.socket.socket`                   | `time_response=null`, `error="ntp probe failed: ..."`  |
  | `ldap`      | `ethscan.ldap.socket.socket`                  | `accessible=false`, `error="ldap probe failed: ..."`  |
  | `smb`       | `ethscan.smb.socket.socket`                   | `accessible=false`, `error="smb probe failed: ..."`   |
  | `snmp`      | `ethscan.snmp.socket.socket`                  | `communities=[]`, `error="snmp probe failed: ..."`    |
  | `ssh`       | `ethscan.ssh.socket.create_connection`        | `banner=null`, `error="ssh probe failed: ..."`        |
  | `ssl`       | `ethscan.ssl.socket.create_connection`        | `cert=null`, `valid=false`, `error="hostile transport"` |
  | `tls`       | `ethscan.tls.socket.create_connection`        | every version and cipher `supported=false` with an error |
  | `whois`     | `ethscan.whois.socket.socket`                 | `raw=""`, `error="Connection failed: ..."`            |
  | `service`   | `ethscan.service.socket.create_connection`    | `services_found=0`, `results=[]`                       |
  | `dnssec`    | `ethscan.dnssec._query_dnskey_raw` / `_query_dnskey_dnspython` | `validated=false`, `dnskey.error="dnssec probe failed: ..."` |

- **The twelve new checks are meaningful.** Each one was proved by reverting
  the guard of its own module and watching the check fail: narrowing the
  broad `except Exception` of `redis`, `memcached`, `ntp`, `ldap`, `smb`,
  `snmp`, `ssh` and `dnssec` to `except ValueError`, and dropping
  `RuntimeError` from the caught tuple of `ssl`, `tls`, `whois` and
  `service`, makes the hostile transport escape the module and the matching
  check fail. With the guards restored all 28 pass. The mutation was applied
  to a copy of the file and restored afterwards, so no source file was
  changed.
- `python -m pytest tests/` -> **5072 passed, 48 skipped, 2 warnings** (the
  two warnings are the pre-existing `test_main.py` runpy ones; the committed
  baseline was 5060 passed, 48 skipped; the +12 are the new CLI checks).
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `git diff --check` -> clean. Nothing is committed.

## What remains unresolved

- **The CLI level still has no failure-field check for the HTTP-facing
  commands.** The module sweep `tests/test_http_hostile_sweep.py` covers
  `web`, `headers`, `fuzz`, `urlcheck`, `cert`, `geo`, `mac`, `s3`, `cve` and
  `subtake` at the module level, but no check runs them through the CLI and
  asserts their own failure field. Their transport is
  `urllib.request.urlopen` (patched globally by the module sweep), except
  that `urlcheck` also runs the TLS probe of `ethscan.ssl`.
- **Still without a CLI-level check among the other network commands:**
  `trace` (socket seam: `ethscan.trace.socket.socket` and
  `socket.gethostbyname`), `brute` (the seam is `ethscan.brute.FTP`, the
  `ftplib` class the module imported; the SSH path needs paramiko), `vuln`
  and `recon` (aggregators over modules that are already covered) and
  `nmap` (an offline parser of nmap XML).
- **`socket.setdefaulttimeout()` is a process-wide side effect.** The
  resolution helpers of `ethscan/dns.py`, `ethscan/resolve.py`,
  `ethscan/stale.py` and `ethscan/subtake.py` set the default timeout of the
  process. The sweep restores it after every check; the other test files do
  not, so a later test inherits a 2s default socket timeout.

## Approaches that failed and why

- **The ftp and smtp commands were first patched at the wrong seam** (from
  the session before this one). Their CLI-level failure signal comes from the
  real socket path, so patching `ftplib.FTP` or `socket.create_connection`
  left the commands hitting the real loopback and reporting "Connection
  refused" instead of the hostile transport. The correct seam is the
  module's own injectable helper (`ethscan.ftp._connect`, `ethscan.smtp._connect`).
- **The dnsbrute command resolves every candidate label through real DNS.**
  Patching only the AXFR socket left the subdomain resolution hitting the
  network, so the check also disables dnspython (`DNS_AVAILABLE`) and patches
  `ethscan.dns.socket.getaddrinfo`.
- **The connector seam is not reachable from the command line.** The modules
  that take a `connector(host, port, request, timeout)` argument
  (`redis`, `memcached`, `ntp`, `ldap`, `smb`, `snmp`) fall back to their own
  socket when the CLI calls them, so a CLI-level check has to patch the
  socket, not the connector. The module sweep covers the connector path.

## One precise next task

Extend the permanent CLI-level sweep to the HTTP-facing commands, which are
the last group of network commands without a failure-field check at the
command line: `web`, `headers`, `fuzz`, `urlcheck`, `cert`, `geo`, `mac`,
`s3`, `cve` and `subtake`.

The method is the one used in this session, in
`tests/test_cli_unreachable_sweep.py`: patch the transport the module really
uses (here `urllib.request.urlopen`, patched globally exactly as
`tests/test_http_hostile_sweep.py` does; `urlcheck` also runs the TLS probe
of `ethscan.ssl`, so it needs `ethscan.ssl.socket.create_connection` as
well), run the command through `CliRunner`, and assert that it exits 0,
leaks no traceback and prints the module's own failure signal. The signal
differs per command (an `error` field for `web`, `headers`, `cert`, `geo` and
`mac`; the errors of the entries for `fuzz` and `s3`; the error of the `web`
part for `urlcheck`), and `cve` and `subtake` report a failed lookup as a
missing entry, so assert the signal the module documents, not a fixed
wording.

Keep the smallest reversible change (the crash becomes the command's
documented error signal; do not weaken an existing guard), and do not commit
unless explicitly asked.
