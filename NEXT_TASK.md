# NEXT_TASK.md

## Status (2026-10-19T23:45:00Z)
- Prior agent task (the `s3` bracketed-IPv6 crash ->
  `http.client.InvalidURL`): **complete**. `s3 --target '[::1]:443'`
  now exits 0 with per-bucket `error` results and no traceback.
- A second crash of the same class was found in the same change and is
  also fixed: `s3 --target example.com --region 'a b'` (the region is
  interpolated into the endpoint URL) used to die with the same
  `InvalidURL` traceback.
- The `--target` leak list is now **empty** for the inputs of the sweep
  below.
- Verified: **4215 passed / 1 skipped**; ruff rule set identical to the
  baseline (48 pre-existing errors, no new ones).

## The `s3` fix in one paragraph
`ethscan/s3.py` now knows which candidates can be S3 bucket names.
`check_bucket_public` reports a name that cannot exist as a failed
probe (`error: "Invalid bucket name: <reason>"`) **without** sending a
request, catches `http.client.HTTPException` (which `InvalidURL`
derives from) and reports it like every other probe failure, and the
worker wrapper of `run_s3` turns any unexpected exception into a failed
probe result so that one bad candidate cannot abort the report. The
candidates themselves are not filtered out, so an explicit
`--wordlist` entry stays visible in the report.

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

Result after this session: **no traceback leaked** (168 invocations).

For `--target ''` the eleven commands that exit 2 are the ten protocol
commands (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`,
`smb`, `smtp`) plus `trace`. Every other command exits 0 and reports the
problem inside its own output.

## Remaining tasks (bounded, high-value)

### 1. A port out of range in the bare `host:port` form -> `OverflowError` traceback (next task)
`--target 'example.com:99999'` still dies with a raw traceback in
`redis`, `ldap`, `memcached`, `netbios`, `ntp`, `smb` and `snmp`:

```
OverflowError: connect(): port must be 0-65535.
EXIT=1
```

The same target with a scheme (`http://example.com:99999`) is already
reported as a usage error (exit 2), so this is an inconsistency between
the two forms of the same target. The seven modules parse the port of a
bare `host:port` target by hand (e.g. `ethscan/redis.py:61-65`) and
never check the range, while the scheme form goes through
`url_port()` (`ethscan/target.py:52`), which already does.

Full root-cause analysis, the seven call sites and the suggested fix
shape (one shared `check_port()` helper in `ethscan/target.py`) are in
`HANDOFF_NEXT.md`.

### 2. Backlog from a wider sweep (15 further hostile inputs)
A wider sweep found two more classes of leaked traceback. They are not
the next task; the evidence and the affected commands are in
`HANDOFF_NEXT.md` ("Backlog found by the same sweep").

| input | commands | error |
|---|---|---|
| `--target '....'` | 13 commands | `UnicodeError: label empty or too long` |
| `--target '%00'` | `fuzz`, `headers`, `urlcheck`, `web` | `InvalidURL: URL can't contain control characters. '\x00'` |
| `--target 'http://user:pass@example.com'` | `fuzz`, `headers`, `urlcheck`, `web` | `InvalidURL: nonnumeric port: 'pass@example.com'` |

## Verified working forms (do not break)
- `host`, `host:443`, `http://host`, `https://host:8443`, `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- `trace` still accepts `example.com`, `example.com:80` and
  `http://example.com/`.
- `s3` still derives the same candidates in the same order, keeps the
  original case of a `--wordlist` entry, and still resolves the DNS of a
  valid candidate before requesting it.
