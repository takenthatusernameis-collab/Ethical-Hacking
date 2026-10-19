# NEXT_TASK.md

## Status (2026-10-19T23:09:00Z)
- Prior agent task (`--target` path/query with a space or control character
  -> click usage error): **complete**.
- `trace --target ''` -> `ValueError: Invalid target`: **complete** (click
  usage error, exit code 2).
- `ping` with an unresolvable host -> raw `socket.gaierror`: **complete**.
  Fixed in commit `9a86aa0` (`ethscan/ping.py:250` catches `socket.gaierror`
  and returns a `NO-RESPONSE` probe with the resolver error in `error`).
  Verified: `--target no-such-host.invalid` and `--target 'host name'` both
  exit 0 with structured output; `example.com` still exits 0.
- Verified: **4207 passed / 1 skipped**; ruff rule set identical to the
  baseline (48 pre-existing errors, no new ones).

These docs were written before commit `9a86aa0` and listed `ping` as
unresolved; that is stale. `ping` is resolved. See `HANDOFF_NEXT.md`.

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
| `--target ''` | none |
| `--target 'host name'` | none (`ping` fixed) |
| `--target 'no-such-host.invalid'` | none (`ping` fixed) |

For `--target ''` the eleven commands that exit 2 are the ten protocol
commands (`redis`, `memcached`, `ntp`, `snmp`, `ftp`, `ldap`, `netbios`,
`smb`, `smtp`) plus `trace`. Every other command exits 0 and reports the
problem inside its own output.

## Remaining tasks (bounded, high-value)

### 1. `s3` with a bracketed IPv6 target -> `http.client.InvalidURL` traceback
**This is the next task.** `--target "[::1]:443"` crashes, exit 1, with a
raw traceback (`ethscan/s3.py`). Full reproduction, root-cause analysis and
the two decisions to make before writing code are in `HANDOFF_NEXT.md`.

In short: `_normalize_target("[::1]:443")` returns `"::1"`; `_build_bucket_candidates`
derives `::1`, `::1-backup`, `backup-::1`, ...; `check_bucket_public`
catches `HTTPError`/`(URLError, socket.timeout, OSError)` but not
`http.client.InvalidURL`, which escapes `future.result()` in `run_s3`.
Non-deterministic across runs.

Suggested minimal fix shape: in `check_bucket_public` extend the `except (...)`
clause (`ethscan/s3.py:255`) to include `http.client.HTTPException` and set
`result["error"] = str(exc)`, so a malformed S3 URL yields a failed probe
result instead of escaping. Verify `python -m ethscan s3 --target '[::1]:443'`
exits 0 with per-bucket `error` results and no traceback; add a test.

### 2. Other network-dependent failures
None remain for `--target ''` / `--target 'host name'` / `--target
'no-such-host.invalid'` after the `ping` fix. The `s3` bracketed-IPv6 crash
is the only remaining `--target` leak.

## Verified working forms (do not break)
- `host`, `host:443`, `http://host`, `https://host:8443`, `[::1]:443`
- `https://example.com/path`, `https://example.com/a%20b`,
  `https://example.com/?q=1`, `https://example.com/path?query=1#frag`
- The empty-host -> `localhost` mapping of `web._parse_url` and the
  lower-casing of `s3._normalize_target` must stay as they are.
- `trace` still accepts `example.com`, `example.com:80` and
  `http://example.com/`.
