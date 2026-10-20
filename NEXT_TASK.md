# NEXT_TASK.md

## Status (2026-10-20T00:40:00Z)
- Prior agent task (the `s3` bracketed-IPv6 crash): **complete** (see
  `TASK.md` of that session).
- The task this session inherited (a port out of range in the **bare**
  `host:port` form) is **complete for all 14 commands** that parse such a
  target. The previous session had fixed 7 of them in the code but left
  them untested and undocumented; the other 7 silently connected to the
  **wrong port** and are fixed now.
- A second crash in the same expression (a port text that `int()` refuses)
  is fixed as well.
- Verified: **4272 passed / 1 skipped**; ruff rule set identical to the
  baseline (48 pre-existing errors, no new ones).
- The `--target` leak list is empty for the inputs of the sweep below.

## The port fix in one paragraph
`ethscan/target.py` now owns the validation of a hand-parsed port:
`check_port()` accepts the port as a number **or as the text of a number**,
converts the text itself (so text that `int()` refuses becomes a
`TargetSpecError` and not a raw `ValueError`) and refuses anything outside
0-65535 with `Port out of range 0-65535`. All 14 protocol modules call it
in the branch that parses the port of a bare `host:port` target, so the
bare form and the scheme-qualified form (`redis://host:99999`, which was
already refused by `url_port()`) are now refused the same way.

## Sweep of every `--target` command (current evidence)

All 42 CLI commands that take a `--target` were invoked with four
hostile inputs. Reproduce with:

```python
from click.testing import CliRunner
from ethscan import cli

runner = CliRunner()
cmds = ("brute cert cve dns dnsbrute dnssec ftp fuzz geo headers ldap mac "
        "memcached mongodb mssql mysql netbios ntp oracle osdetect ping "
        "postgresql recon redis report resolve s3 scan service smb smtp snmp "
        "ssh ssl subdomains subtake tls trace urlcheck vuln web whois").split()

for c in cmds:
    for target in ("", "host name", "no-such-host.invalid", "[::1]:443"):
        res = runner.invoke(cli.cli, [c, "--target", target])
        exc = res.exception
        leaked = exc is not None and not isinstance(exc, SystemExit)
        if leaked:
            print(c, repr(target), res.exit_code, type(exc).__name__, exc)
```

Result: **no traceback leaked** (168 invocations).

The port-aware sweep of this session (20 commands x 12 targets, including
`example.com:99999`, `example.com:65536`, `example.com:²`,
`[::1]:99999`, `http://example.com:99999` and
`host:99999999999999999999`) also leaked **0 tracebacks** in 240
invocations.

## Remaining tasks (bounded, high-value)

### 1. The explicit `--port` option is not range-checked (next task)
23 commands take a port as an option (`--port`, and `ping --tcp-port`,
`recon --trace-port`, `recon --whois-port`). Every one of them uses
`type=int` without a range, so an out-of-range value reaches the socket
layer:

```
$ python -m ethscan redis --target 127.0.0.1 --port 99999
  File ".../ethscan/redis.py", line 193, in _send_recv
    sock.connect((host, port))
OverflowError: connect(): port must be 0-65535.
EXIT=1
```

**10 commands leak a traceback**: `ldap`, `memcached`, `redis`, `smb`
(`connect()`), `netbios`, `ntp`, `snmp` (`sendto()`), `ping` (`--tcp-port`,
`connect_ex()`), `trace` and `whois` (`connect()`).

**12 commands probe the wrong port silently**: `brute`, `ftp`, `mongodb`,
`mssql`, `mysql`, `oracle`, `postgresql`, `smtp`, `ssh`, `ssl`, `tls`,
`urlcheck` - `socket.getaddrinfo()` wraps a port above 65535, so
`--port 99999` is probed on port **34463**. `recon --trace-port` and
`recon --whois-port` pass the value on to the same modules.

Root cause and the suggested fix shape (one `click.IntRange(0, 65535)`
per option) are in `HANDOFF_NEXT.md`.

### 2. Backlog from the wider sweep (still reproduces, 21 invocations)
A wider sweep found three more classes of leaked traceback. They are not
the next task; the evidence and the affected commands are in
`HANDOFF_NEXT.md` ("Backlog found by the same sweep").

| input | commands | error |
|---|---|---|
| `--target '....'` | `cert`, `dnssec`, `ftp`, `geo`, `mac`, `osdetect`, `ping`, `report`, `scan`, `service`, `smtp`, `ssh`, `vuln` (13) | `UnicodeError: label empty or too long` |
| `--target '%00'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: URL can't contain control characters. '\x00'` |
| `--target 'http://user:pass@example.com'` | `fuzz`, `headers`, `urlcheck`, `web` (4) | `InvalidURL: nonnumeric port: 'pass@example.com'` |

## Verified working forms (do not break)
- `host`, `host:443`, `host:65535`, `http://host`, `https://host:8443`,
  `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- `trace` still accepts `example.com`, `example.com:80` and
  `http://example.com/`.
- `s3` still derives the same candidates in the same order, keeps the
  original case of a `--wordlist` entry, and still resolves the DNS of a
  valid candidate before requesting it.
- All 14 protocol modules still parse `host:1234`, `host:65535` and
  `[::1]:443` to the same values as before.
