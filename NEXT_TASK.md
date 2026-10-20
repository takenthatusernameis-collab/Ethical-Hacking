# NEXT_TASK.md

## Status (2026-10-20T08:20:00Z)
- Prior agent task (the explicit **`--port` option**): **complete**. The
  range check itself was already in the code (`click.IntRange(0, 65535)` on
  all 24 port options), but it was **untested and undocumented**; this
  session verified it end to end and added the regression tests (including
  an invariant test that every port option of the CLI is range-checked and
  a tripwire test that a rejected port starts no connection).
- The three classes of the wider backlog (a percent-encoded control
  character in the host, a userinfo part in the authority, a host that is
  not a valid host name) are **fixed as well**.
- Verified: **4319 passed / 1 skipped**; ruff rule set identical to the
  baseline (48 pre-existing errors, no new ones); `git diff --check` clean.
- The `--target` leak list is empty for the inputs of the sweep below
  (462 invocations, 0 leaked tracebacks).

## The port fix in one paragraph
All 24 port options of the CLI (`--port`, and `ping --tcp-port`,
`recon --trace-port`, `recon --whois-port`) are declared as
`click.IntRange(0, 65535)`, so click refuses a value outside 0-65535
before the command runs, with **exit 2** and the single line
`Error: Invalid value for '--port': 99999 is not in the range 0<=x<=65535.`
The same check applies to a port that comes from the **config file**
(`commands: {redis: {port: 99999}}`), because click validates the default
map as well.

## Sweep of every `--target` command (current evidence)

All 42 CLI commands that take a `--target` were invoked with eleven
hostile inputs. Reproduce with:

```python
from click.testing import CliRunner
from ethscan import cli

runner = CliRunner()
cmds = ("brute cert cve dns dnsbrute dnssec ftp fuzz geo headers ldap mac "
        "memcached mongodb mssql mysql netbios ntp oracle osdetect ping "
        "postgresql recon redis report resolve s3 scan service smb smtp snmp "
        "ssh ssl subdomains subtake tls trace urlcheck vuln web whois").split()
targets = ("....", "%00", "http://user:pass@example.com", "host name",
           "host\tname", "https://example.com/a b", "redis://host:notaport",
           "host:99999", "http://example.com/ho\x00st", "https://host\tname", "")

for c in cmds:
    for target in targets:
        res = runner.invoke(cli.cli, [c, "--target", target])
        exc = res.exception
        leaked = exc is not None and not isinstance(exc, SystemExit)
        if leaked:
            print(c, repr(target), res.exit_code, type(exc).__name__, exc)
```

Result: **no traceback leaked** (462 invocations).

## Remaining tasks (bounded, high-value)

### 1. The `--timeout` option is not range-checked

**DONE.** All 43 `--timeout` CLI options were changed from `type=float` to
`click.FloatRange(min=0.001)` (`ethscan/cli.py`), so click refuses a negative
or zero timeout before the command runs, with exit 2 and a single-line
`Error: Invalid value for '--timeout': ... is not in the range x>=0.001.`.

Previously `--timeout -1` leaked a `ValueError: Timeout value out of range`
traceback in `ldap`, `memcached`, `netbios`, `ntp`, `redis`, `smb`, `snmp`,
`trace` and `whois`, and `--timeout 0` leaked a `BlockingIOError` in `whois`.

Verified: `python -m pytest -q` -> **4323 passed, 1 skipped** (4 new timeout
tests added to `tests/test_cli.py`); ruff unchanged (48 pre-existing errors,
no new ones); `git diff --check` clean; `--timeout -1`/`0` return exit 2 for
all 43 commands and valid timeouts (`0.001`, `0.5`, `5.0`, `10.0`) still work.

### 2. Backlog from the wider sweep
The three classes that were in the backlog of the previous session are
**fixed** (percent-encoded control character, userinfo, invalid host
name). Nothing from that sweep leaks any more.

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
- A target with a userinfo (`http://user:pass@example.com`) is scanned as
  `example.com` (the credentials are dropped), the way whois, mongodb and
  ssh already did it.
- A host that is not a valid host name (`....`) is reported as a failed
  probe (**exit 0**), exactly like a host that cannot be resolved
  (`no-such-host.invalid`).
