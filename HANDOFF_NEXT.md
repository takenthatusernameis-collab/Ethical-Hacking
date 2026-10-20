# HANDOFF_NEXT.md

## Summary
The **out-of-range port in the bare `host:port` form is fixed for all 14
commands** that parse such a target.

The previous session had already introduced `check_port()` in
`ethscan/target.py` and applied it to seven modules
(`redis`, `ldap`, `memcached`, `netbios`, `ntp`, `smb`, `snmp`), but it
ran out of time: the change was **untested and undocumented**, and the
seven modules with the same hand-written port parser were missed. Those
seven did not crash - they silently probed the **wrong port**.

A second crash in the very same expression was found and fixed as well.

The `--port` **option** (as opposed to the port inside `--target`) is the
next task; it has the same class of bug and is fully measured below.

## What changed
### `ethscan/target.py`
1. **`check_port(port: int | str) -> int`** now takes the port as a number
   **or as the text of a number** (the text as it appears in a
   `host:port` target). It converts the text itself and raises
   `TargetSpecError` for text that `int()` refuses. The range check and
   its message (`Port out of range 0-65535`) are unchanged.
2. The reason for the text form: the port of a bare target is parsed by
   hand with `str.isdigit()`, and `str.isdigit()` accepts characters that
   `int()` refuses - the superscript digits. `example.com:²` used to die
   with a raw `ValueError: invalid literal for int() with base 10: '²'`.

### `ethscan/{ftp,smtp,mysql,mongodb,postgresql,mssql,oracle}.py` (new)
The same hand-written `host:port` parser as in the seven modules the
previous session fixed. These modules now call `check_port()` as well.

**Why they did not crash before:** they connect with
`socket.create_connection()`, which resolves the host with
`socket.getaddrinfo()`, and `getaddrinfo()` *wraps* a port above 65535:

```python
>>> socket.getaddrinfo('127.0.0.1', 99999, 0, socket.SOCK_STREAM)
[(<AddressFamily.AF_INET: 2>, <SocketKind.SOCK_STREAM: 1>, 6, '', ('127.0.0.1', 34463))]
```

So `example.com:99999` was probed on port **34463** and the result was
reported as a normal probe result. A silent wrong port is worse than the
crash of the other seven modules, which raised `OverflowError` (an
`ArithmeticError`, **not** an `OSError`, so the `except OSError` handlers
of the library did not catch it).

### `ethscan/{redis,ldap,memcached,netbios,ntp,smb,snmp}.py`
Completed from the previous session: the call sites now pass the port
*text* to `check_port()` instead of calling `int()` themselves.

### Decisions
1. **Where the failure is reported** follows the convention that is
   already established per command and was not changed:
   - the 9 commands whose contract is "the option is invalid" (`redis`,
     `ldap`, `memcached`, `netbios`, `ntp`, `smb`, `snmp`, `ftp`, `smtp`)
     report a click usage error (exit 2):
     `Error: Invalid value for '--target': Port out of range 0-65535`;
   - the 5 commands whose contract is "the probe failed" (`mysql`,
     `mongodb`, `oracle`, `postgresql`, `mssql`) report the error inside
     their own output and exit 0, exactly like the scheme-qualified form
     of the same target already did.
2. **The message is identical to the one of `url_port()`**
   (`Port out of range 0-65535`), so the bare form and the
   scheme-qualified form of the same target now fail identically.
3. `check_port()` keeps the `TargetSpecError` type, which is a
   `ValueError` subclass, so the `except ValueError` handlers of the
   library keep working.

## Verification
- `python -m ethscan <cmd> --target 'example.com:99999'` for the 9
  usage-error commands -> exit 2, one-line message, no traceback.
- The same target for the 5 probe-failure commands -> exit 0,
  `"error": "Port out of range 0-65535"`.
- `python -m ethscan redis --target 'example.com:²'` -> exit 2,
  `Error: Invalid value for '--target': Invalid port '²'`.
- The valid forms are unchanged in all 14 modules: `host:1234` ->
  `('host', 1234)`, `host:65535` -> `('host', 65535)`,
  `[::1]:443` -> `('::1', 443)`.
- Full suite: **4272 passed, 1 skipped** (4215 before + 57 new tests:
  51 in `tests/test_target.py`, 6 in `tests/test_cli.py`).
- Ruff: **48 errors, the same pre-existing ones**, no new ones. None of
  them is on a line that was changed.
- Sweep: 20 target-consuming commands x 12 hostile targets = 240
  invocations, **0 leaked tracebacks**.

## Next task (bounded, high-value): the explicit `--port` option is not range-checked

### Evidence
23 commands take a port as an option. Every one of them uses `type=int`
without a range, so the value reaches the socket layer:

```
$ python -m ethscan redis --target 127.0.0.1 --port 99999
  File ".../ethscan/redis.py", line 193, in _send_recv
    sock.connect((host, port))
OverflowError: connect(): port must be 0-65535.
EXIT=1
```

**10 commands leak a traceback** (`OverflowError`):

| command | option | message |
|---|---|---|
| `redis`, `ldap`, `memcached`, `smb` | `--port` | `connect(): port must be 0-65535.` |
| `netbios`, `ntp`, `snmp` | `--port` | `sendto(): port must be 0-65535.` |
| `ping` | `--tcp-port` | `connect_ex(): port must be 0-65535.` |
| `trace`, `whois` | `--port` | `connect(): port must be 0-65535.` |

**12 commands probe the wrong port silently** (the `getaddrinfo()` wrap
described above): `brute`, `ftp`, `mongodb`, `mssql`, `mysql`, `oracle`,
`postgresql`, `smtp`, `ssh`, `ssl`, `tls`, `urlcheck`. `recon` passes
`--trace-port` and `--whois-port` on to `trace` and `whois`.

Reproduce:

```python
from click.testing import CliRunner
from ethscan import cli

runner = CliRunner()
cmds = ("brute cert cve dns dnsbrute dnssec ftp fuzz geo headers ldap mac "
        "memcached mongodb mssql mysql netbios ntp oracle osdetect ping "
        "postgresql recon redis report resolve s3 scan service smb smtp snmp "
        "ssh ssl subdomains subtake tls trace urlcheck vuln web whois").split()

for c in cmds:
    res = runner.invoke(cli.cli, [c, "--help"])
    if "--port" not in res.output and "--tcp-port" not in res.output:
        continue
    opt = "--tcp-port" if "--tcp-port" in res.output else "--port"
    res = runner.invoke(cli.cli, [c, "--target", "127.0.0.1", opt, "99999"])
    exc = res.exception
    if exc is not None and not isinstance(exc, SystemExit):
        print(c, opt, res.exit_code, type(exc).__name__, exc)
```

### Root cause
The options are declared as `@click.option("--port", default=443,
type=int, ...)`. The library never sees the option value as a problem:
the port is used as it is.

### Suggested fix shape
Use `click.IntRange(0, 65535)` for the port options, so click rejects the
value before the command runs:

```python
@click.option("--port", default=443, type=click.IntRange(0, 65535),
              help="TLS port (default: 443)")
```

The options to change (`ethscan/cli.py`): `whois` 1132, `ssl` 1522,
`tls` 1569, `urlcheck` 1909, `brute` 1998, `trace` 2179, `ping`
`--tcp-port` 2294, `recon` `--whois-port` 2529 and `--trace-port` 2544,
`memcached` 3656, `mysql` 3724, `mongodb` 3789, `postgresql` 3854,
`ssh` 4117, `smtp` 4263, `ftp` 4355, `ntp` 4431, `snmp` 4507,
`netbios` 4585, `smb` 4667, `redis` 4733, `ldap` 4799, `mssql` 4867,
`oracle` 4932. (The line numbers are from the current working tree.)

Note: the options with `default=None` (the protocol commands) must keep
working - `click.IntRange` leaves a `None` default alone, but verify it.

Verify with `python -m ethscan <cmd> --target 127.0.0.1 --port 99999` ->
exit 2 and a one-line error for every command that has the option, and
that `--port 443` and the defaults keep working. Add one CLI test that
loops over the commands with a port option.

### Backlog found by the same sweep (not the next task)
Reproduce with the script in `NEXT_TASK.md` (42 commands x 3 hostile
targets). Three further classes of leaked traceback remain, unchanged
since the session that recorded them:

| input | commands | error |
|---|---|---|
| `--target '....'` | `cert`, `dnssec`, `ftp`, `geo`, `mac`, `osdetect`, `ping`, `report`, `scan`, `service`, `smtp`, `ssh`, `vuln` (13) | `UnicodeError: label empty or too long` (the idna encoding of a host made only of dots) |
| `--target '%00'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: URL can't contain control characters. '\x00'` (the percent-encoded NUL is decoded after `check_target_path` has inspected the raw path) |
| `--target 'http://user:pass@example.com'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: nonnumeric port: 'pass@example.com'` (the userinfo is not stripped before the host is used) |

All three are the same shape as the tasks above: the target is accepted by
the parser and refused later by the network layer. The established
convention applies - report it as a usage error (exit 2) when the target
is unusable, otherwise as a probe failure inside the output.

## Unchanged / deliberate non-changes
- The valid target forms are untouched: `host`, `host:1234`, `host:65535`,
  `[::1]:443`, `redis://host:6379`, `https://host:8443`.
- The scheme-qualified form of an out-of-range port was already refused
  by `url_port()` and still is, with the same message.
- `s3` is unaffected: it never reads the port of its target.
- The 14 `_normalize_target` copies remain duplicated (separate refactor;
  they differ on `host:` / bracketed-IPv6 edge cases). This session only
  added the same one-line check to the port branch of each copy.
- The 48 pre-existing ruff errors are unrelated and left alone.
- The explicit `--port` option was **not** changed in this session: it is
  a different surface (an option, not the target) and the next task.
