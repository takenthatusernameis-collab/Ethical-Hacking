# HANDOFF_NEXT.md

## Session summary (2026-10-20T08:20:00Z)

This session finished the task of the previous session (the explicit
`--port` option), added the regression tests that the fix was missing, and
closed the three classes of the wider sweep backlog.

| task | state |
|---|---|
| explicit `--port` option range check | **complete** (the range check was already in the code; the tests were missing and were added) |
| `--target '%00'` (percent-encoded control character in the host) | **complete** |
| `--target 'http://user:pass@example.com'` (userinfo in the authority) | **complete** |
| `--target '....'` (host that is not a valid host name) | **complete** |
| `--timeout` option range check | **complete** |

Verified: **4323 passed / 1 skipped** (4319 before + 4 new tests), ruff
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

**DONE in this session.**

All 43 `--timeout` CLI options were changed from `type=float` to
`click.FloatRange(min=0.001)` (`ethscan/cli.py`), so click refuses a negative
or zero timeout before the command runs, with exit 2 and a single line
`Error: Invalid value for '--timeout': <value> is not in the range x>=0.001.`.

- The lower bound is `0.001`: `min=0` would still allow `--timeout 0`,
  which puts the whois socket into non-blocking mode and leaks
  `BlockingIOError: [Errno 115] Operation now in progress`.
- Every default timeout (2.0, 3.0, 5.0, 10.0, DEFAULT_TIMEOUT) is >= 0.001,
  so no valid default is rejected.
- `--http-timeout` (subtake) and `--service-timeout` were deliberately left
  as `type=float`: neither leaks a traceback (`--http-timeout -1` exits 0;
  `--service-timeout` is not a `service` option -- `service` uses `--timeout`).

Verification:
- `python -m pytest -q` -> **4323 passed, 1 skipped** (4319 before + 4 new
  timeout tests).
- `python -m ruff check ethscan/ tests/` -> same **48** pre-existing errors,
  no new ones; touched files (`ethscan/cli.py`, `tests/test_cli.py`) are
  clean.
- `git diff --check` -> clean.
- `--timeout -1` and `--timeout 0` now return exit 2 with a one-line error
  for all 43 commands; valid timeouts (`0.001`, `0.5`, `5.0`, `10.0`) still
  work (redis returns exit 0, no traceback).
- 4 new tests in `tests/test_cli.py`:
  `test_every_timeout_option_of_the_cli_is_range_checked`,
  `test_an_out_of_range_timeout_option_is_a_usage_error`,
  `test_an_out_of_range_timeout_option_is_a_single_line_error`,
  `test_a_valid_timeout_option_is_still_used`.

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
