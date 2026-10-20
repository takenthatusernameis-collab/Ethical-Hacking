# HANDOFF_NEXT.md

## Session summary (2026-10-20T08:20:00Z)

This session finished the task of the previous session (the explicit
`--port` option), added the regression tests that the fix was missing, and
closed the three classes of the wider sweep backlog.

| task | state |
|---|---|
| explicit `--port` option range check | **complete** (the range check was already in the code, the tests were missing) |
| `--target '%00'` (percent-encoded control character in the host) | **complete** |
| `--target 'http://user:pass@example.com'` (userinfo in the authority) | **complete** |
| `--target '....'` (host that is not a valid host name) | **complete** |
| `--timeout` option range check | **open - the next task** |

Verified: **4319 passed / 1 skipped** (4272 before + 47 new tests), ruff
identical to the baseline (48 pre-existing errors, no new ones),
`git diff --check` clean, and a sweep of **42 commands x 11 hostile targets
= 462 invocations with 0 leaked tracebacks**.

## What changed

### 1. The `--port` option: verified and covered by tests
The 24 port options of the CLI were already declared as
`click.IntRange(0, 65535)` (`ethscan/cli.py`), so click refused an
out-of-range value before the command ran. **No source change was needed**;
what was missing was the regression coverage, which is what the previous
session asked for ("add one CLI test that loops over the commands with a
port option").

`tests/test_cli.py` (new section at the end of the file):
- `test_every_port_option_of_the_cli_is_range_checked` - an invariant test:
  every parameter of the CLI whose name contains "port" (except the plural
  `--ports` spec) must be an `IntRange(0, 65535)` that does **not** clamp,
  and the number of them must match the list the other tests use.
- `test_an_out_of_range_port_option_is_a_usage_error` - every command with a
  port option refuses `65536`, `99999`, `-1` and `99999999999999999999`
  with **exit 2** and the line
  `Error: Invalid value for '<option>': <value> is not in the range 0<=x<=65535.`
- `test_an_out_of_range_port_option_is_a_single_line_error` - the failure is
  exactly one `Error:` line, not a traceback.
- `test_an_out_of_range_port_option_does_not_start_a_probe` - a tripwire:
  `socket.socket.connect`, `connect_ex`, `sendto` and `socket.getaddrinfo`
  are replaced, so a rejected port may not start a connection.
- `test_an_out_of_range_port_in_the_config_file_is_a_usage_error` - a port
  that comes from `commands: {redis: {port: 99999}}` is refused as well
  (click validates the default map too).
- `test_a_valid_port_option_is_still_used_for_the_probe` and
  `test_a_valid_port_option_is_handed_to_the_probe` - a valid port (`0`,
  `1`, `65535`) still reaches the probe unchanged.

### 2. `--target '%00'` - a percent-encoded control character in the host
**Root cause:** `urllib.request` decodes the percent escapes of the host
before it uses it (`/usr/lib/python3.12/urllib/request.py`: `self.host =
unquote(self.host)`). The host that reaches `http.client` therefore carries
a control character that the raw target does not show, and `http.client`
refuses it with an `InvalidURL` - which is an `HTTPException` and not a
`ValueError`, so it escaped the `except ValueError` handlers of the library.

**Fix:** `ethscan/target.py`, `check_target_host()` checks the host twice -
as it is written and after its percent escapes are decoded. The message
(`Target host contains a space or control character`) is unchanged, so the
existing tests and the wording of the other commands stay the same.

`web`, `headers`, `urlcheck` and `fuzz` now report the target as a usage
error (**exit 2**).

### 3. `--target 'http://user:pass@example.com'` - a userinfo in the authority
**Root cause:** `urllib.request` keeps the userinfo in the host it connects
to, and `http.client` then reads the text after the last colon of that host
as the port (`InvalidURL: nonnumeric port: 'pass@example.com'`).

**Fix:** `ethscan/target.py` gained `strip_userinfo(url)`, which drops the
userinfo and keeps the scheme, the host, the port, the path, the query and
the fragment exactly as they are. It is used in `ethscan/web.py`
(`fetch_headers`) and `ethscan/fuzz.py` (`_normalize_base_url`), the way the
whois, mongodb and ssh modules already used the host without the userinfo
(`whois._normalize_target("http://user:pass@example.com") == "example.com"`
was already the case).

The target is now scanned as `example.com` instead of crashing.

### 4. `--target '....'` - a host that is not a valid host name
**Root cause:** the resolver encodes a host name as IDNA and raises a
`UnicodeError` for a name with an empty label. `UnicodeError` is a
`ValueError` and not an `OSError`, so the narrow `except` clauses of the
library did not catch it.

**Fix:** `ValueError` is caught where the host is resolved or connected:
`ethscan/{cert,geo,mac,ping}.py` (`_resolve_host`),
`ethscan/dnssec.py` (`_resolve_nameservers`), `ethscan/{scanner,service}.py`
(the connection), `ethscan/{osdetect,ssh}.py` (the connection error) and
`ethscan/{smtp,ftp}.py` (the connection failure).

**Deliberate contract choice:** such a host is reported the way **every
host that cannot be resolved** is reported - as a failed probe inside the
output (**exit 0**), exactly like `no-such-host.invalid` - and not as a
usage error. The 13 commands that were affected (`cert`, `dnssec`, `ftp`,
`geo`, `mac`, `osdetect`, `ping`, `report`, `scan`, `service`, `smtp`,
`ssh`, `vuln`) all report an unresolvable host that way today, so the
malformed host now behaves the same as a missing one.

## Verification (with the evidence)
- Full suite: `python -m pytest -q` -> **4319 passed, 1 skipped**.
- Ruff: `python -m ruff check ethscan/ tests/` -> the same **48**
  pre-existing errors, **no new ones** (the diff of the finding list
  against the baseline is empty).
- `git diff --check` -> clean.
- Sweep of all 42 target-consuming commands with 11 hostile targets
  (`....`, `%00`, `http://user:pass@example.com`, `host name`,
  `host\tname`, `https://example.com/a b`, `redis://host:notaport`,
  `host:99999`, `http://example.com/ho\x00st`, `https://host\tname`, `""`)
  -> **462 invocations, 0 leaked tracebacks**. The script is in
  `NEXT_TASK.md`. The commands `brute`, `snmp`, `ssh` and `trace` need more
  than 15 s in this sandbox for a target that resolves (the network is
  unreachable here), with or without a change.
- **Mutation checks** (the fix was reverted, the new tests were run again,
  the fix was restored):
  - three port options back to `type=int` -> **6 of the 8** new port tests
    fail and reproduce the original
    `OverflowError('connect(): port must be 0-65535.')`;
  - the decoded-host check and the userinfo strip removed -> **15** of the
    new tests fail (4 of them at the CLI level);
  - the `ValueError` removed from the `except` clauses -> every new test
    of the malformed-host class fails.
  Every new test was checked against a reverted fix at least once.

## Approaches that failed or were rejected
- **Refusing a target with a userinfo** (usage error) was considered and
  **rejected**: the repo already has the opposite convention - `whois`,
  `mongodb` and `ssh` strip the userinfo and use the host
  (`tests/test_whois.py`, `tests/test_mongodb.py`, `tests/test_ssh.py`).
  Stripping keeps the tool usable and the reported host consistent with the
  host the request is sent to.
- **A CLI-level host validator** (refuse a host that is not a valid DNS
  name as a usage error) was considered for the `....` class and **rejected**:
  it would have to reproduce the rules of the IDNA encoder (a label may be
  empty only as the trailing dot, a label is shorter than 64 characters,
  an underscore is fine, an IPv6 literal is fine) in ethscan, and a
  mistake there would refuse a host that works today. Catching the
  `ValueError` instead cannot refuse a working target.
- **Using `urlsplit`/`urlunsplit` to strip the userinfo** was rejected: it
  lower-cases the host and drops the brackets of an IPv6 literal.
  `strip_userinfo` works on the raw text and keeps everything else.

## The next task: the `--timeout` option is not range-checked

43 CLI options are declared as `@click.option("--timeout", ..., type=float)`
without a range. A negative timeout reaches the socket layer, where
`socket.settimeout()` refuses it:

```
$ python -m ethscan redis --target 127.0.0.1 --timeout -1
  File ".../ethscan/redis.py", line 191, in _send_recv
    sock.settimeout(timeout)
ValueError: Timeout value out of range
EXIT=1
```

**9 commands leak a traceback** with `--timeout -1`: `ldap`, `memcached`,
`netbios`, `ntp`, `redis`, `smb`, `snmp`, `trace` and `whois`. The sites are
`sock.settimeout(timeout)` in `ethscan/redis.py:191`, `ethscan/ldap.py:467`,
`ethscan/memcached.py:89`, `ethscan/netbios.py:460`, `ethscan/ntp.py:247`,
`ethscan/smb.py:220`, `ethscan/snmp.py:405`, `ethscan/trace.py:62` and
`ethscan/whois.py:43`.

**`whois` leaks a second one** with `--timeout 0`:
`BlockingIOError: [Errno 115] Operation now in progress` at
`ethscan/whois.py:45` (`sock.connect()`), because a timeout of 0 is legal
for `socket.settimeout()` and puts the socket in non-blocking mode.

Reproduce with:

```python
from click.testing import CliRunner
from ethscan import cli

runner = CliRunner()
cmds = ("brute cert cve dns dnsbrute dnssec ftp fuzz geo headers ldap mac "
        "memcached mongodb mssql mysql netbios ntp oracle osdetect ping "
        "postgresql recon redis report resolve s3 scan service smb smtp snmp "
        "ssh ssl subdomains subtake tls trace urlcheck vuln web whois").split()

for c in cmds:
    for value in ("-1", "0"):
        res = runner.invoke(cli.cli, [c, "--target", "127.0.0.1", "--timeout", value])
        exc = res.exception
        if exc is not None and not isinstance(exc, SystemExit):
            print(c, value, type(exc).__name__, exc)
```

**Suggested fix shape:** the same shape as the `--port` fix - give the
`--timeout` option a range (`click.FloatRange(min=...)`) so click refuses
the value before the command runs, with exit 2 and a one-line error. Two
points to decide:

- the lower bound: `min=0` fixes the negative value but leaves the
  `--timeout 0` case of `whois` open (0 is a legal socket timeout), so the
  bound has to exclude 0 (e.g. `min=0.001`) or `whois` has to read from a
  socket that is not in non-blocking mode;
- 8 of the 9 commands (`redis`, `ldap`, `memcached`, `netbios`, `ntp`,
  `smb`, `snmp`, `trace`) are decorated with `@_target_usage_errors` and
  have a usage-error contract; `whois` is **not** decorated and reports a
  failed probe in its output instead. A range check on the **option** works
  for both, because click validates the option before the command function
  runs - the result is exit 2 in every case. A check inside the modules
  instead would have to follow the contract of each command.

Verify with `python -m ethscan <cmd> --target 127.0.0.1 --timeout -1` ->
exit 2 and a one-line error for the commands above, that the valid timeouts
(`0.5`, `5.0`) keep working, and add one CLI test that loops over the
commands with a timeout option - the shape of
`test_an_out_of_range_port_option_is_a_usage_error` in `tests/test_cli.py`.

## Unchanged / deliberate non-changes
- The valid target forms are untouched: `host`, `host:1234`, `host:65535`,
  `[::1]:443`, `redis://host:6379`, `https://host:8443`,
  `https://example.com/a%20b` (a percent-encoded space in the **path** is
  still accepted - only the **host** is decoded now).
- The scheme-qualified form of an out-of-range port is still refused by
  `url_port()` with the same message.
- `s3` is unaffected: it never reads the port of its target.
- The 14 `_normalize_target` copies remain duplicated (separate refactor;
  they differ on `host:` / bracketed-IPv6 edge cases).
- The 48 pre-existing ruff errors are unrelated and left alone.
- The `--ports` option (the plural form) was swept in this session for
  `99999`, `0-99999`, `80,99999` and `-1`: every command that has it
  refuses the value, so nothing had to be changed there.
