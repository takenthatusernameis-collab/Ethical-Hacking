# NEXT_TASK.md

## Status (2026-10-19T19:41:00Z)
- Prior agent task (a `--target` whose **path or query** contains a space or
  a control character -> click usage error): **complete**.
- This session's task (`trace --target ''` -> `ValueError: Invalid target`):
  **complete**. `trace` now reports the unusable target as a click usage
  error (exit code 2).
- Verified: 4204 passed / 1 skipped; ruff rule set identical to the baseline
  (48 pre-existing errors, no new ones).

## Sweep of every `--target` command (new evidence)

All 42 CLI commands that take a `--target` were invoked with three hostile
inputs. Reproduce with:

```python
from click.testing import CliRunner
from ethscan import cli

runner = CliRunner()
cmds = ("brute cert cve dns dnsbrute dnssec ftp fuzz geo headers ldap mac "
        "memcached mongodb mssql mysql netbios ntp oracle osdetect ping "
        "postgresql recon redis report resolve s3 scan service smb smtp snmp "
        "ssh ssl subdomains subtake tls trace urlcheck vuln web whois").split()

for c in cmds:
    for target in ("", "host name", "no-such-host.invalid"):
        res = runner.invoke(cli.cli, [c, "--target", target])
        exc = res.exception
        leaked = exc is not None and not isinstance(exc, SystemExit)
        if leaked:
            print(c, repr(target), res.exit_code, type(exc).__name__, exc)
```

Result after this session:

| input | traceback leaked by |
|---|---|
| `--target ''` | **none** |
| `--target 'host name'` | `ping` (`socket.gaierror`) |
| `--target 'no-such-host.invalid'` | `ping` (`socket.gaierror`) |

For `--target ''` the eleven commands that exit 2 are the ten protocol
commands (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`,
`smb`, `smtp`) plus `trace`. Every other command exits 0 and reports the
problem inside its own output.

## Remaining tasks (bounded, high-value)

### 1. `ping` with an unresolvable host -> raw `socket.gaierror` traceback
**This is the next task.** It is the only remaining command that leaks an
exception for an unresolvable host.

Reproduction:

```console
$ python -m ethscan ping --target no-such-host.invalid
...
  File "/home/runner/work/Ethical-Hacking/Ethical-Hacking/ethscan/ping.py", line 249, in probe_icmp
    err = send_sock.connect_ex((host, port))
socket.gaierror: [Errno -2] Name or service not known
EXIT=1
```

Root cause (already analysed, no guesswork needed):
- `run_ping` (`ethscan/ping.py:305`) computes `ip = _resolve_host(host)`.
  `_resolve_host` returns `None` for a name that does not resolve.
- When `ip is None`, `run_ping` already appends the note
  `"Could not resolve host {host!r} to an IPv4 address"` - the module
  clearly intends to *report* the failure, not to crash.
- But `run_ping` still calls `probe_icmp(host, ...)` (line 330). In the
  TCP fallback path `probe_icmp` does
  `err = send_sock.connect_ex((host, port))` (line 249).
  `connect_ex` returns an error code for a *failed connect*, but it
  **raises** `socket.gaierror` when the name itself cannot be resolved, and
  that exception is not caught.

Suggested shape of the fix (keep it inside the library, no click import):
catch `socket.gaierror` around the `connect_ex` call and return the same
"no response" result shape the function already returns for a failed
connect, with the resolver error in the `error` field. The command then
exits 0 and reports the failure inside its own output, matching the
contract of every other probe command.

Constraints:
- `ping` needs **no** `TargetSpecError` and **no** `_target_usage_errors`
  decorator: an unresolvable host is a probe failure, not an invalid
  option. Do not turn it into a usage error.
- Keep the existing `"Could not resolve host ..."` note.
- Keep the raw-ICMP path unchanged.
- Add a test that `run_ping` with an unresolvable host exits 0 and reports
  the failure in its output (no traceback).

### 2. `s3` with a bracketed IPv6 target -> `http.client.InvalidURL:
nonnumeric port: '1.s3.amazonaws.com'`
`--target "[::1]:443"` crashes. Two things to decide before writing code:

1. **Which bucket names are usable.** `_normalize_target("[::1]:443")`
   returns `"::1"` (`urlparse(...).hostname`). `_build_bucket_candidates`
   then derives `"::1"`, `"::1-backup"`, `"backup-::1"`, ... - none of which
   is a valid S3 bucket name (S3 bucket names are DNS-compliant: lowercase
   letters, digits and hyphens, 3-63 characters). The question is whether
   invalid candidates are filtered out (which would make the target produce
   zero candidates and take the existing
   `"No bucket candidates could be derived from the target."` path) or
   reported.
2. **Whether a failed probe should be reported inside the result.**
   `check_bucket_public` catches `urllib.error.HTTPError` and
   `(urllib.error.URLError, socket.timeout, OSError)`, but
   `http.client.InvalidURL` derives from `HTTPException` and is not one of
   those, so it escapes. `run_s3` calls `future.result()` in the main
   thread, so the exception escapes the whole command.

Evidence for the non-determinism (six runs of the unchanged tree):
```
nonnumeric port: '1.s3.amazonaws.com'
nonnumeric port: '1-backup.s3.amazonaws.com'
nonnumeric port: '1-backups.s3.amazonaws.com'
```
The candidates are probed concurrently, so whichever thread finishes first
re-raises first. Any fix must make the outcome deterministic.

### 3. Other network-dependent failures
`s3` with an unresolvable host (`socket.gaierror` or
`encoding with 'idna' codec failed`) was in the old list. The sweep above
shows that **no other command** leaks an exception for an unresolvable
host, so this is now part of cluster 2 only.

## Verified working forms (do not break)
- `host`, `host:443`, `http://host`, `https://host:8443`, `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- `trace` still accepts `example.com`, `example.com:80` and
  `http://example.com/`.
